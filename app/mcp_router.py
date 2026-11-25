"""
Model Context Protocol (MCP) HTTP & Tool Discovery Router for geo-oracle-x402 (Glama.ai Ready).
Exposes:
  - GET  /mcp/tools   : Machine-readable MCP tool catalog
  - POST /mcp/invoke  : Direct tool invocation proxy
  - POST /mcp         : Standard MCP JSON-RPC 2.0 Streamable HTTP endpoint
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.brain.geo_brain_engine import brain_engine
from app.brain.security_gate_bridge import security_gate_bridge
from app.core.sister_federation import get_federation_mesh_status
from app.core.x402_verifier import X402Verifier
from app.oracles.infrastructure.router import (
    ORACLE_NAME,
    ORACLE_PRICE_USDC,
    InfrastructureAssessRequest,
    _ASSET_WEIGHTS,
    _run_infrastructure_assessment,
)

router = APIRouter(tags=["MCP (Glama.ai & AI Agents)"])

_INFRASTRUCTURE_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "asset_id": {
            "type": "string",
            "minLength": 1,
            "maxLength": 128,
            "description": (
                "Unique identifier for the physical infrastructure asset being evaluated. "
                "May be a registered A.GRID asset ID (e.g., 'DC-TOKYO-JP', 'PORT-BUSAN-KR', 'MINE-ATACAMA-CL') "
                "or any custom alphanumeric label for an arbitrary site."
            ),
        },
        "asset_type": {
            "type": "string",
            "enum": list(_ASSET_WEIGHTS.keys()),
            "default": "DATA_CENTER",
            "description": (
                "Physical infrastructure class used to weight seismic, climate, flood, and connectivity risk factors. "
                "Defaults to 'DATA_CENTER'. Choosing 'MINE' or 'FARM' also enriches the assessment with sister "
                "critical-minerals or EUDR deforestation compliance signals."
            ),
        },
        "latitude": {
            "type": "number",
            "minimum": -90,
            "maximum": 90,
            "description": (
                "WGS84 geographic latitude in decimal degrees from -90 (South Pole) to +90 (North Pole), "
                "for example 35.6762 for Tokyo or 37.5665 for Seoul."
            ),
        },
        "longitude": {
            "type": "number",
            "minimum": -180,
            "maximum": 180,
            "description": (
                "WGS84 geographic longitude in decimal degrees from -180 (West) to +180 (East), "
                "for example 139.6503 for Tokyo or 126.9780 for Seoul."
            ),
        },
        "commodity": {
            "type": "string",
            "default": "INFRASTRUCTURE",
            "description": (
                "Optional workload or commodity tag for domain context (e.g., 'AI_COMPUTE', 'LITHIUM', "
                "'SOYBEAN', 'LNG', or 'INFRASTRUCTURE'). Defaults to 'INFRASTRUCTURE'."
            ),
        },
        "use_live_feed": {
            "type": "boolean",
            "default": True,
            "description": (
                "When true (default, recommended), queries all 10 live Tier-1 Earth & digital infrastructure APIs "
                "(USGS, NASA EONET, Copernicus DEM, Open-Meteo, GloFAS Flood, PeeringDB, TeleGeography). "
                "Set false only for deterministic offline/synthetic fallback testing."
            ),
        },
    },
    "required": ["asset_id", "latitude", "longitude"],
}

MCP_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "preview_infrastructure_risk",
        "description": (
            "Compute a FREE, read-only multi-layer physical and digital infrastructure risk preview for any "
            "WGS84 coordinate worldwide. Use this tool first for site screening, hazard exploration, or "
            "cost-free risk checks before committing to a paid cryptographic audit (use assess_infrastructure_risk "
            "instead when a verifiable SHA-256 proof_hash and x402 payment receipt are required). "
            "Synthesizes 10 live Tier-1 feeds: Copernicus 5-point DEM slope/elevation, Open-Meteo weather & Stull "
            "wet-bulb cooling risk, ECMWF GloFAS river flood discharge, USGS ComCat seismic activity, NASA EONET "
            "wildfires/storms/volcanoes, PeeringDB data centers/IXPs, TeleGeography subsea cables, and Starlink "
            "orbital line-of-sight. Returns composite_risk_score (0-100), risk_grade, layer-by-layer sub-scores, "
            "confidence level, and full data_provenance metadata."
        ),
        "inputSchema": _INFRASTRUCTURE_INPUT_SCHEMA,
        "annotations": {
            "title": "Preview Physical Infrastructure Risk (Free)",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    },
    {
        "name": "assess_infrastructure_risk",
        "description": (
            "Execute a PAID (0.015 USDC via x402 multi-chain or Solana) verified physical infrastructure risk "
            "assessment with a deterministic SHA-256 proof_hash, BCBS operational resilience flags, and an auditable "
            "data_provenance trail. Use this tool when downstream smart contracts, insurers, or compliance workflows "
            "require a cryptographically verifiable risk attestation; use preview_infrastructure_risk for free "
            "exploratory queries. Requires a valid X-402-Signature header (or X402_SIGNATURE environment variable "
            "in stdio mode); if omitted or invalid, returns a structured payment_required (HTTP 402) challenge "
            "describing the exact USDC amount, recipient, and supported settlement networks."
        ),
        "inputSchema": _INFRASTRUCTURE_INPUT_SCHEMA,
        "annotations": {
            "title": "Assess Physical Infrastructure Risk (Paid x402 Attestation)",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    },
    {
        "name": "get_geo_brain_status",
        "description": (
            "Retrieve live operational telemetry from the 24/7 geo-oracle-elizaos-brain autonomous learning engine. "
            "Use this tool to inspect model calibration and reliability before trusting risk forecasts. "
            "Takes no arguments and returns current learning cycle count, sequential live Brier score, "
            "verified prediction pairs, high-confidence ratio, episodic memory size, and Google Cloud Storage "
            "checkpoint persistence status."
        ),
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {},
        },
        "annotations": {
            "title": "Get Geo-Oracle Brain Calibration Status",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    },
    {
        "name": "get_federation_mesh_status",
        "description": (
            "Check live health, latency, and endpoint routing across all A.GRID federated sister oracle services "
            "(agent-security-gate-x402, x402-cleanweb-agent, eudr-compliance-agent, and minerals-oracle-x402). "
            "Use this tool to verify cross-oracle connectivity or discover specialized domain endpoints for "
            "mining (MINE), deforestation/agriculture (FARM), or security workflows. Takes no arguments and "
            "returns per-service health status, URLs, and federation mesh summary."
        ),
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {},
        },
        "annotations": {
            "title": "Get A.GRID Federation Mesh Health",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    },
    {
        "name": "get_security_gate_status",
        "description": (
            "Inspect the 4-tier Security Gate governance and safety posture protecting geo-oracle-x402. "
            "Use this tool to audit prompt-injection defense metrics, autonomous x402 spend-cap guardrails, "
            "and EU AI Act Article 50 watermarking compliance before integrating this server into automated "
            "agent pipelines. Takes no arguments and returns active tier status, neutralized threat counters, "
            "and spend-cap policy thresholds."
        ),
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {},
        },
        "annotations": {
            "title": "Get 4-Tier Security Gate Governance Status",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    },
]


class MCPInvokeRequest(BaseModel):
    name: str = Field(..., description="MCP tool name")
    arguments: Dict[str, Any] = Field(default_factory=dict)


async def _dispatch_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    auth_header: Optional[str] = None,
) -> Dict[str, Any]:
    if tool_name == "preview_infrastructure_risk":
        req = InfrastructureAssessRequest(**arguments)
        return await _run_infrastructure_assessment(req=req, fee_paid=0.0, settlement_network="FREE_PREVIEW", preview=True)

    if tool_name == "assess_infrastructure_risk":
        if not auth_header:
            chal = X402Verifier.generate_challenge(price_usdc=ORACLE_PRICE_USDC, oracle_name=ORACLE_NAME)
            return {"payment_required": True, "http_status": 402, "challenge": chal.model_dump()}
        ok, msg, settlement = X402Verifier.verify_payment_header(auth_header, expected_price_usdc=ORACLE_PRICE_USDC)
        if not ok:
            chal = X402Verifier.generate_challenge(price_usdc=ORACLE_PRICE_USDC, oracle_name=ORACLE_NAME)
            return {"payment_required": True, "http_status": 402, "rejection_reason": msg, "challenge": chal.model_dump()}
        req = InfrastructureAssessRequest(**arguments)
        return await _run_infrastructure_assessment(
            req=req,
            fee_paid=float(ORACLE_PRICE_USDC),
            settlement_network=settlement.get("network", "Polygon") if settlement else "Polygon",
            preview=False,
        )

    if tool_name == "get_geo_brain_status":
        await brain_engine.initialize()
        return brain_engine.get_status()

    if tool_name == "get_federation_mesh_status":
        return await get_federation_mesh_status()

    if tool_name == "get_security_gate_status":
        return await security_gate_bridge.get_governance_status()

    raise HTTPException(status_code=404, detail=f"Unknown MCP tool: {tool_name}")


@router.get("/mcp/tools")
async def list_mcp_tools():
    """Returns MCP tool definitions for Glama.ai, Claude, Cursor, and autonomous agents."""
    return {
        "server": "geo-oracle-x402",
        "version": "3.0.0",
        "protocolVersion": "2024-11-05",
        "tools": MCP_TOOLS,
    }


@router.post("/mcp/invoke")
async def invoke_mcp_tool(
    body: MCPInvokeRequest,
    x_402_signature: Optional[str] = Header(default=None, alias="X-402-Signature"),
    authorization: Optional[str] = Header(default=None),
):
    """Direct REST invocation wrapper for MCP thin stdio clients."""
    return await _dispatch_tool(body.name, body.arguments, auth_header=x_402_signature or authorization)


@router.post("/mcp")
async def handle_mcp_jsonrpc(
    payload: Dict[str, Any],
    x_402_signature: Optional[str] = Header(default=None, alias="X-402-Signature"),
    authorization: Optional[str] = Header(default=None),
):
    """Standard MCP JSON-RPC 2.0 Streamable HTTP endpoint."""
    method = payload.get("method", "")
    req_id = payload.get("id")
    params = payload.get("params") or {}

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "geo-oracle-x402", "version": "3.0.0"},
            },
        }
    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}
    if method == "notifications/initialized":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"acknowledged": True}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": MCP_TOOLS}}
    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments") or {}
        try:
            result = await _dispatch_tool(tool_name, arguments, auth_header=x_402_signature or authorization)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
                    "isError": False,
                },
            }
        except HTTPException as exc:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32602, "message": str(exc.detail)},
            }
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32000, "message": str(exc)},
            }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }
