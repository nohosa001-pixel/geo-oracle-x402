"""
Zero-Dependency Checkpoint Persistence for geo-oracle elizaOS Brain.
Stores state locally in data/brain/ and automatically syncs to Google Cloud Storage
when GCS_BRAIN_BUCKET is set (using Cloud Run's native GCE metadata OAuth2 token).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import quote

import httpx

from app.core.observability import log_event

LOCAL_BRAIN_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "brain"
GCS_BRAIN_BUCKET = os.getenv("GCS_BRAIN_BUCKET", "").strip()
GCS_BRAIN_PREFIX = os.getenv("GCS_BRAIN_PREFIX", "geo-oracle").strip().strip("/")
_METADATA_TOKEN_URL = (
    "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
)


class BrainCheckpointStore:
    """Persists Brain JSON checkpoints to local disk and optionally Google Cloud Storage."""

    def __init__(
        self,
        local_dir: Optional[Path] = None,
        gcs_bucket: Optional[str] = None,
        gcs_prefix: Optional[str] = None,
    ) -> None:
        self.local_dir = local_dir or LOCAL_BRAIN_DIR
        self.gcs_bucket = (gcs_bucket if gcs_bucket is not None else GCS_BRAIN_BUCKET).strip()
        self.gcs_prefix = (gcs_prefix if gcs_prefix is not None else GCS_BRAIN_PREFIX).strip().strip("/")
        self.local_dir.mkdir(parents=True, exist_ok=True)

    @property
    def persistence_mode(self) -> str:
        return f"GCS_SYNCED (gs://{self.gcs_bucket}/{self.gcs_prefix})" if self.gcs_bucket else "LOCAL_DISK_ONLY"

    async def _get_gcs_token(self) -> Optional[str]:
        """Fetches an OAuth2 access token from the Cloud Run metadata server."""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(_METADATA_TOKEN_URL, headers={"Metadata-Flavor": "Google"})
                if resp.status_code == 200:
                    return resp.json().get("access_token")
        except Exception:
            pass
        return None

    async def save_json(self, filename: str, data: Dict[str, Any]) -> bool:
        """Writes JSON locally and mirrors to GCS if GCS_BRAIN_BUCKET is configured."""
        self.local_dir.mkdir(parents=True, exist_ok=True)
        local_path = self.local_dir / filename
        payload_bytes = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
        local_path.write_bytes(payload_bytes)

        if not self.gcs_bucket:
            return True

        token = await self._get_gcs_token()
        if not token:
            return False

        obj_name = f"{self.gcs_prefix}/{filename}" if self.gcs_prefix else filename
        upload_url = (
            f"https://storage.googleapis.com/upload/storage/v1/b/{self.gcs_bucket}/o"
            f"?uploadType=media&name={quote(obj_name, safe='')}"
        )
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    upload_url,
                    content=payload_bytes,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                )
                if resp.status_code in (200, 201):
                    return True
                log_event(
                    "brain_gcs_save_failed",
                    severity="WARNING",
                    filename=filename,
                    status_code=resp.status_code,
                )
        except Exception as exc:
            log_event("brain_gcs_save_error", severity="WARNING", filename=filename, error=str(exc))
        return False

    async def load_json(self, filename: str) -> Optional[Dict[str, Any]]:
        """Loads JSON from GCS first (if configured) to survive Cloud Run restarts, falling back to local disk."""
        if self.gcs_bucket:
            token = await self._get_gcs_token()
            if token:
                obj_name = f"{self.gcs_prefix}/{filename}" if self.gcs_prefix else filename
                download_url = (
                    f"https://storage.googleapis.com/storage/v1/b/{self.gcs_bucket}/o/"
                    f"{quote(obj_name, safe='')}?alt=media"
                )
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        resp = await client.get(download_url, headers={"Authorization": f"Bearer {token}"})
                        if resp.status_code == 200:
                            data = resp.json()
                            # Cache locally
                            (self.local_dir / filename).write_text(
                                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
                            )
                            return data
                except Exception as exc:
                    log_event("brain_gcs_load_error", severity="WARNING", filename=filename, error=str(exc))

        local_path = self.local_dir / filename
        if local_path.exists():
            try:
                return json.loads(local_path.read_text(encoding="utf-8"))
            except Exception:
                return None
        return None
