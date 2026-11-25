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

MCP_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "preview_infrastructure_risk",
        "description": (
            "FREE multi-layer physical & digital infrastructure risk preview for any WGS84 coordinate "
            "(DATA_CENTER, PORT, MINE, POWER_GRID, SUBSEA_CABLE, FARM, LOGISTICS_HUB). Combines 10 live Tier-1 feeds "
            "(Copernicus DEM, Open-Meteo & Wet-Bulb, ECMWF GloFAS Flood, USGS Seismic, NASA EONET, PeeringDB, TeleGeography)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "asset_id": {"type": "string", "description": "Asset identifier (e.g. DC-TOKYO-JP, PORT-BUSAN-KR)"},
                "asset_type": {
                    "type": "string",
                    "enum": list(_ASSET_WEIGHTS.keys()),
                    "default": "DATA_CENTER",
                },
                "latitude": {"type": "number", "minimum": -90, "maximum": 90},
                "longitude": {"type": "number", "minimum": -180, "maximum": 180},
                "commodity": {"type": "string", "default": "INFRASTRUCTURE"},
                "use_live_feed": {"type": "boolean", "default": True},
            },
            "required": ["asset_id", "latitude", "longitude"],
        },
    },
    {
        "name": "assess_infrastructure_risk",
        "description": (
            "PAID (x402, 0.015 USDC) verified physical infrastructure risk assessment with deterministic SHA-256 proof hash "
            "and full data_provenance audit trail."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "asset_id": {"type": "string"},
                "asset_type": {"type": "string", "enum": list(_ASSET_WEIGHTS.keys()), "default": "DATA_CENTER"},
                "latitude": {"type": "number", "minimum": -90, "maximum": 90},
                "longitude": {"type": "number", "minimum": -180, "maximum": 180},
                "commodity": {"type": "string", "default": "INFRASTRUCTURE"},
                "use_live_feed": {"type": "boolean", "default": True},
            },
            "required": ["asset_id", "latitude", "longitude"],
        },
    },
    {
        "name": "get_geo_brain_status",
        "description": "Returns live telemetry, Brier score, and GCS persistence status of the 24/7 geo-oracle elizaOS Brain.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_federation_mesh_status",
        "description": "Returns live health and routing directory of all A.GRID sister systems (security-gate, cleanweb, eudr, minerals).",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_security_gate_status",
        "description": "Returns 4-tier Security Gate governance status, neutralized threats, and autonomous spend guardrails.",
        "inputSchema": {"type": "object", "properties": {}},
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
