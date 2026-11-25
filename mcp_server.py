#!/usr/bin/env python3
"""
geo-oracle-x402 — Thin MCP Stdio Client (v3.0.0, Glama.ai / Claude / Cursor Compatible).
Proxies JSON-RPC 2.0 MCP calls directly to the hosted A.GRID Earth Physical Infrastructure
Risk Hub on Google Cloud Run.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, Optional

import httpx

DEFAULT_ORACLE_URL = "https://geo-oracle-x402-212942243360.asia-northeast3.run.app"


def get_base_url() -> str:
    return os.getenv("GEO_ORACLE_URL", DEFAULT_ORACLE_URL).rstrip("/")


def _headers() -> Dict[str, str]:
    headers: Dict[str, str] = {
        "Content-Type": "application/json",
        "User-Agent": "geo-oracle-x402-mcp-stdio/3.0.0",
    }
    x402_sig = os.getenv("X402_SIGNATURE") or os.getenv("X402_AUTHORIZATION")
    if x402_sig:
        headers["X-402-Signature"] = x402_sig
    return headers


def handle_jsonrpc(req: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    method = req.get("method", "")
    req_id = req.get("id")
    if method == "notifications/initialized":
        return None
    try:
        resp = httpx.post(f"{get_base_url()}/mcp", json=req, headers=_headers(), timeout=30.0)
        return resp.json()
    except Exception as exc:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32000, "message": str(exc)}}


def main() -> None:
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = handle_jsonrpc(req)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
