"""
Pluggable Nonce Store for x402 Anti-Replay Protection.
Uses Redis automatically when REDIS_URL is configured and `redis` package is installed;
falls back cleanly to a thread-safe in-memory store for local dev and single-instance runs.
"""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Any, Dict, Optional, Protocol


class NonceStore(Protocol):
    def issue(self, nonce: str, metadata: Dict[str, Any], ttl_seconds: int) -> None: ...
    def get_active(self, nonce: str) -> Optional[Dict[str, Any]]: ...
    def is_consumed(self, nonce: str) -> bool: ...
    def consume(self, nonce: str, consumed_ttl_seconds: int = 86400) -> None: ...


class InMemoryNonceStore:
    """Thread-safe in-memory nonce store with lazy TTL expiration."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active: Dict[str, Dict[str, Any]] = {}
        self._consumed: Dict[str, int] = {}

    def _prune(self, now: int) -> None:
        expired_active = [k for k, v in self._active.items() if v.get("expiry", 0) < now]
        for k in expired_active:
            self._active.pop(k, None)
        expired_consumed = [k for k, exp in self._consumed.items() if exp < now]
        for k in expired_consumed:
            self._consumed.pop(k, None)

    def issue(self, nonce: str, metadata: Dict[str, Any], ttl_seconds: int) -> None:
        now = int(time.time())
        record = dict(metadata)
        record.setdefault("expiry", now + ttl_seconds)
        with self._lock:
            self._prune(now)
            self._active[nonce] = record

    def get_active(self, nonce: str) -> Optional[Dict[str, Any]]:
        now = int(time.time())
        with self._lock:
            self._prune(now)
            return self._active.get(nonce)

    def is_consumed(self, nonce: str) -> bool:
        now = int(time.time())
        with self._lock:
            exp = self._consumed.get(nonce)
            if exp is None:
                return False
            if exp < now:
                self._consumed.pop(nonce, None)
                return False
            return True

    def consume(self, nonce: str, consumed_ttl_seconds: int = 86400) -> None:
        now = int(time.time())
        with self._lock:
            self._active.pop(nonce, None)
            self._consumed[nonce] = now + consumed_ttl_seconds


class RedisNonceStore:
    """Redis-backed nonce store for multi-instance Cloud Run deployments."""

    ACTIVE_PREFIX = "x402:active:"
    CONSUMED_PREFIX = "x402:consumed:"

    def __init__(self, redis_url: str) -> None:
        import redis  # type: ignore

        self._client = redis.Redis.from_url(redis_url, decode_responses=True)

    def issue(self, nonce: str, metadata: Dict[str, Any], ttl_seconds: int) -> None:
        self._client.setex(f"{self.ACTIVE_PREFIX}{nonce}", max(1, ttl_seconds), json.dumps(metadata))

    def get_active(self, nonce: str) -> Optional[Dict[str, Any]]:
        raw = self._client.get(f"{self.ACTIVE_PREFIX}{nonce}")
        return json.loads(raw) if raw else None

    def is_consumed(self, nonce: str) -> bool:
        return bool(self._client.exists(f"{self.CONSUMED_PREFIX}{nonce}"))

    def consume(self, nonce: str, consumed_ttl_seconds: int = 86400) -> None:
        pipe = self._client.pipeline()
        pipe.delete(f"{self.ACTIVE_PREFIX}{nonce}")
        pipe.setex(f"{self.CONSUMED_PREFIX}{nonce}", max(60, consumed_ttl_seconds), "1")
        pipe.execute()


_STORE_INSTANCE: Optional[NonceStore] = None


def get_nonce_store() -> NonceStore:
    """Returns singleton NonceStore (Redis if REDIS_URL is set and available, else InMemory)."""
    global _STORE_INSTANCE
    if _STORE_INSTANCE is not None:
        return _STORE_INSTANCE

    redis_url = os.getenv("REDIS_URL", "").strip()
    if redis_url:
        try:
            _STORE_INSTANCE = RedisNonceStore(redis_url)
            return _STORE_INSTANCE
        except Exception:
            pass

    _STORE_INSTANCE = InMemoryNonceStore()
    return _STORE_INSTANCE
