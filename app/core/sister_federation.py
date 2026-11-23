"""
A.GRID Sister Systems Federation Connector (Cross-Domain A2A Mesh).
Connects geo-oracle-x402 conditionally and safely with:
  - minerals-oracle-x402 (triggered for MINE assets)
  - eudr-compliance-agent (triggered for FARM assets)
  - agent-security-gate-x402 (integrity & escrow hub)
  - x402-cleanweb-agent (unstructured web/notice scrubbing)

Enforces strict MAX_FEDERATION_HOPS=2 loop protection via X-Agrid-Hop-Count
and X-Agrid-Trace-Id headers, with 5-minute TTL caching and graceful fallbacks.
"""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from typing import Any, Dict, Optional

import httpx

from app.core.observability import log_event

MAX_FEDERATION_HOPS = int(os.getenv("MAX_FEDERATION_HOPS", "2"))
SISTER_TIMEOUT_SEC = float(os.getenv("SISTER_TIMEOUT_SEC", "4.0"))
SISTER_CACHE_TTL_SEC = float(os.getenv("SISTER_CACHE_TTL_SEC", "300.0"))

SISTER_URLS: Dict[str, str] = {
    "security_gate": os.getenv(
        "SECURITY_GATE_URL",
        "https://agent-security-gate-x402-212942243360.asia-northeast3.run.app",
    ).rstrip("/"),
    "cleanweb": os.getenv(
        "CLEANWEB_AGENT_URL",
        "https://x402-cleanweb-agent-212942243360.asia-northeast3.run.app",
    ).rstrip("/"),
    "eudr": os.getenv(
        "EUDR_AGENT_URL",
        "https://eudr-compliance-agent-212942243360.asia-northeast3.run.app",
    ).rstrip("/"),
    "minerals": os.getenv(
        "MINERALS_ORACLE_URL",
        "https://minerals-oracle-x402-212942243360.asia-northeast3.run.app",
    ).rstrip("/"),
}

_COMMODITY_MINERALS_PATHS: Dict[str, str] = {
    "LITHIUM": "/api/v1/lithium/verify-origin",
    "TUNGSTEN": "/api/v1/tungsten/verify-origin",
    "NICKEL": "/api/v1/nickel/verify-origin",
    "COBALT": "/api/v1/cobalt/verify-origin",
    "COPPER": "/api/v1/copper/verify-origin",
    "SILVER": "/api/v1/silver/verify-origin",
    "RARE_EARTHS": "/api/v1/rare-earths/verify-origin",
}

_SISTER_CACHE: Dict[str, tuple[float, Dict[str, Any]]] = {}


def _federation_headers(hop_count: int, trace_id: Optional[str] = None) -> Dict[str, str]:
    return {
        "X-Agrid-Source": "geo-oracle-x402",
        "X-Agrid-Hop-Count": str(hop_count + 1),
        "X-Agrid-Trace-Id": trace_id or f"agrid_{uuid.uuid4().hex[:12]}",
    }


async def query_minerals_sister(
    commodity: str = "LITHIUM",
    hop_count: int = 0,
    trace_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Queries minerals-oracle-x402 status & origin-verification handoff for MINE assets."""
    base = SISTER_URLS["minerals"]
    verify_path = _COMMODITY_MINERALS_PATHS.get(commodity.upper(), "/api/v1/oracle/compliance/verify")

    if hop_count >= MAX_FEDERATION_HOPS:
        return {
            "sister": "minerals-oracle-x402",
            "status": "HOP_LIMIT_REACHED",
            "handoff_endpoint": f"{base}{verify_path}",
        }

    cache_key = f"minerals:{commodity.upper()}"
    now = time.time()
    cached = _SISTER_CACHE.get(cache_key)
    if cached and (now - cached[0]) < SISTER_CACHE_TTL_SEC:
        return cached[1]

    try:
        async with httpx.AsyncClient(timeout=SISTER_TIMEOUT_SEC) as client:
            resp = await client.get(f"{base}/status", headers=_federation_headers(hop_count, trace_id))
            resp.raise_for_status()
            data = resp.json()
            brain = data.get("elizaos_brain") or {}
            result = {
                "sister": "minerals-oracle-x402",
                "status": "CONNECTED_OK",
                "feed_status": data.get("feed_status", "operational"),
                "compliance_engine": data.get("compliance_engine", "operational"),
                "sister_brain_status": brain.get("status", "UNKNOWN"),
                "commodity": commodity.upper(),
                "handoff_endpoint": f"{base}{verify_path}",
                "url": base,
            }
            _SISTER_CACHE[cache_key] = (now, result)
            return result
    except Exception as exc:
        log_event("sister_federation_fallback", severity="WARNING", sister="minerals", error=str(exc))
        return {
            "sister": "minerals-oracle-x402",
            "status": "DEGRADED_FALLBACK",
            "commodity": commodity.upper(),
            "handoff_endpoint": f"{base}{verify_path}",
            "url": base,
        }


async def query_eudr_sister(
    hop_count: int = 0,
    trace_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Queries eudr-compliance-agent live brain & satellite parcel status for FARM assets."""
    base = SISTER_URLS["eudr"]
    handoff = f"{base}/api/v1/customs/fast-audit"

    if hop_count >= MAX_FEDERATION_HOPS:
        return {
            "sister": "eudr-compliance-agent",
            "status": "HOP_LIMIT_REACHED",
            "handoff_endpoint": handoff,
        }

    cache_key = "eudr:status"
    now = time.time()
    cached = _SISTER_CACHE.get(cache_key)
    if cached and (now - cached[0]) < SISTER_CACHE_TTL_SEC:
        return cached[1]

    try:
        async with httpx.AsyncClient(timeout=SISTER_TIMEOUT_SEC) as client:
            resp = await client.get(f"{base}/api/v1/brain/status", headers=_federation_headers(hop_count, trace_id))
            resp.raise_for_status()
            data = resp.json()
            result = {
                "sister": "eudr-compliance-agent",
                "status": "CONNECTED_OK",
                "agent_identity": data.get("agent_identity"),
                "readiness_score_pct": data.get("readiness_score_pct"),
                "satellite_verified_parcels": data.get("satellite_verified_parcels"),
                "ingested_reports_count": data.get("ingested_reports_count"),
                "handoff_endpoint": handoff,
                "url": base,
            }
            _SISTER_CACHE[cache_key] = (now, result)
            return result
    except Exception as exc:
        log_event("sister_federation_fallback", severity="WARNING", sister="eudr", error=str(exc))
        return {
            "sister": "eudr-compliance-agent",
            "status": "DEGRADED_FALLBACK",
            "handoff_endpoint": handoff,
            "url": base,
        }


async def _probe_sister_health(name: str, url: str, path: str) -> Dict[str, Any]:
    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=SISTER_TIMEOUT_SEC) as client:
            resp = await client.get(f"{url}{path}", headers=_federation_headers(0))
            return {
                "service": name,
                "url": url,
                "status": "ONLINE" if resp.status_code == 200 else f"HTTP_{resp.status_code}",
                "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
            }
    except Exception as exc:
        return {
            "service": name,
            "url": url,
            "status": "UNREACHABLE",
            "error": str(exc)[:120],
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
        }


async def get_federation_mesh_status() -> Dict[str, Any]:
    """Returns live health and routing directory across all A.GRID sister systems."""
    probes = await asyncio.gather(
        _probe_sister_health("agent-security-gate-x402", SISTER_URLS["security_gate"], "/health"),
        _probe_sister_health("x402-cleanweb-agent", SISTER_URLS["cleanweb"], "/health"),
        _probe_sister_health("eudr-compliance-agent", SISTER_URLS["eudr"], "/health"),
        _probe_sister_health("minerals-oracle-x402", SISTER_URLS["minerals"], "/health"),
    )
    online_count = sum(1 for p in probes if p["status"] == "ONLINE")
    return {
        "hub": "geo-oracle-x402",
        "federation_protocol": "A.GRID-A2A-MESH/1.0",
        "max_federation_hops": MAX_FEDERATION_HOPS,
        "sisters_online": online_count,
        "sisters_total": len(probes),
        "peers": {
            "security_gate": {
                **probes[0],
                "role": "Deterministic Security & Hallucination Gate (<10ms) + Universal Escrow Hub",
                "inspect_endpoint": f"{SISTER_URLS['security_gate']}/api/v1/gate/inspect",
            },
            "cleanweb": {
                **probes[1],
                "role": "Unstructured Web/PDF/Port-Notice Noise Removal (87% Token Compression)",
                "clean_endpoint": f"{SISTER_URLS['cleanweb']}/api/v1/clean-web",
            },
            "eudr": {
                **probes[2],
                "role": "EU Deforestation Regulation (EUDR) Satellite Compliance (FARM assets)",
                "audit_endpoint": f"{SISTER_URLS['eudr']}/api/v1/customs/fast-audit",
            },
            "minerals": {
                **probes[3],
                "role": "Critical Minerals Origin & Battery Passport Compliance (MINE assets)",
                "status_endpoint": f"{SISTER_URLS['minerals']}/status",
            },
        },
    }
