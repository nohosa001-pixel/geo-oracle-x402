"""
A.GRID Earth Physical Infrastructure Risk Hub Router (x402).
Synthesizes local WGS84 Terrain, Micro-Weather, and 5G/Starlink RF Connectivity
with live Cloud Run Seismic (global-earthquake-agent) and Climate (climate-insurance-agent)
sub-oracles for global physical infrastructure assets (DATA_CENTER, PORT, MINE, POWER_GRID,
SUBSEA_CABLE, FARM, LOGISTICS_HUB).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from typing import Any, Dict, List, Literal, Optional

import httpx
from fastapi import APIRouter, Header, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.base_schemas import X402PaymentRequirement
from app.core.x402_verifier import X402Verifier
from app.oracles.rf_coverage.engine import RFEngine
from app.oracles.rf_coverage.schemas import RFQueryInput
from app.oracles.terrain.engine import TerrainEngine
from app.oracles.terrain.schemas import GeoCoordinateInput
from app.oracles.weather.engine import WeatherEngine
from app.oracles.weather.schemas import WeatherQueryInput

router = APIRouter(prefix="/v1/infrastructure", tags=["0. Earth Physical Infrastructure Hub"])

ORACLE_PRICE_USDC = "0.015"
ORACLE_NAME = "Earth Physical Infrastructure Risk Hub"

SEISMIC_ORACLE_URL = os.getenv(
    "SEISMIC_ORACLE_URL",
    "https://global-earthquake-agent-212942243360.asia-northeast3.run.app",
).rstrip("/")
CLIMATE_ORACLE_URL = os.getenv(
    "CLIMATE_ORACLE_URL",
    "https://climate-insurance-agent-212942243360.asia-northeast3.run.app",
).rstrip("/")
SUBORACLE_TIMEOUT_SEC = float(os.getenv("SUBORACLE_TIMEOUT_SEC", "4.0"))

AssetType = Literal[
    "DATA_CENTER",
    "PORT",
    "MINE",
    "POWER_GRID",
    "SUBSEA_CABLE",
    "FARM",
    "LOGISTICS_HUB",
]

# Asset-type sensitivity weights for physical hazards (seismic, climate, connectivity)
_ASSET_WEIGHTS: Dict[str, Dict[str, float]] = {
    "DATA_CENTER": {"seismic": 0.45, "climate": 0.35, "connectivity": 0.20},
    "PORT": {"seismic": 0.40, "climate": 0.45, "connectivity": 0.15},
    "MINE": {"seismic": 0.50, "climate": 0.35, "connectivity": 0.15},
    "POWER_GRID": {"seismic": 0.40, "climate": 0.45, "connectivity": 0.15},
    "SUBSEA_CABLE": {"seismic": 0.65, "climate": 0.20, "connectivity": 0.15},
    "FARM": {"seismic": 0.20, "climate": 0.65, "connectivity": 0.15},
    "LOGISTICS_HUB": {"seismic": 0.40, "climate": 0.40, "connectivity": 0.20},
}


class InfrastructureAssessRequest(BaseModel):
    asset_id: str = Field(..., description="Unique asset identifier (e.g., DC-SEOUL-01, PORT-ROTTERDAM, MINE-CL-ATACAMA)")
    asset_type: AssetType = Field(default="DATA_CENTER", description="Physical infrastructure asset class")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="WGS84 Latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="WGS84 Longitude")
    commodity: Optional[str] = Field(default="INFRASTRUCTURE", description="Optional commodity or workload tag (e.g. AI_COMPUTE, LITHIUM, SOYBEAN)")
    use_live_feed: bool = Field(default=True, description="Query live Cloud Run seismic & climate sub-oracles")


async def _query_seismic_suboracle(req: InfrastructureAssessRequest) -> Dict[str, Any]:
    payload = {
        "waypoints": [
            {
                "asset_id": req.asset_id,
                "lat": req.latitude,
                "lng": req.longitude,
                "asset_type": req.asset_type,
                "commodity": req.commodity or "INFRASTRUCTURE",
            }
        ],
        "use_live_feed": req.use_live_feed,
    }
    try:
        async with httpx.AsyncClient(timeout=SUBORACLE_TIMEOUT_SEC) as client:
            resp = await client.post(f"{SEISMIC_ORACLE_URL}/api/trade-oracle/assess-route", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return {
                "status": "OK",
                "action": data.get("route_trade_action", "CLEAR"),
                "severity": float(data.get("max_severity_score", 0.0)),
                "force_majeure": bool(data.get("force_majeure_triggered", False)),
                "alternate_hubs": data.get("alternate_hubs_suggested", []),
                "url": SEISMIC_ORACLE_URL,
            }
    except Exception:
        return {
            "status": "DEGRADED_FALLBACK",
            "action": "CLEAR",
            "severity": 0.0,
            "force_majeure": False,
            "alternate_hubs": [],
            "url": SEISMIC_ORACLE_URL,
        }


async def _query_climate_suboracle(req: InfrastructureAssessRequest) -> Dict[str, Any]:
    payload = {
        "waypoints": [
            {
                "asset_id": req.asset_id,
                "lat": req.latitude,
                "lng": req.longitude,
                "asset_type": req.asset_type,
                "commodity": req.commodity or "INFRASTRUCTURE",
            }
        ],
        "use_live_feed": req.use_live_feed,
    }
    try:
        async with httpx.AsyncClient(timeout=SUBORACLE_TIMEOUT_SEC) as client:
            resp = await client.post(f"{CLIMATE_ORACLE_URL}/api/trade-oracle/assess-route", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return {
                "status": "OK",
                "action": data.get("route_trade_action", "CLEAR"),
                "severity": float(data.get("max_severity_score", 0.0)),
                "force_majeure": bool(data.get("force_majeure_triggered", False)),
                "url": CLIMATE_ORACLE_URL,
            }
    except Exception:
        return {
            "status": "DEGRADED_FALLBACK",
            "action": "CLEAR",
            "severity": 0.0,
            "force_majeure": False,
            "url": CLIMATE_ORACLE_URL,
        }


async def _run_infrastructure_assessment(
    req: InfrastructureAssessRequest,
    fee_paid: float,
    settlement_network: str,
    preview: bool = False,
) -> Dict[str, Any]:
    t0 = time.perf_counter()

    # 1. Local deterministic Earth physics layers (terrain, micro-weather, 5G/Starlink connectivity)
    terrain = TerrainEngine.analyze(
        input_data=GeoCoordinateInput(latitude=req.latitude, longitude=req.longitude, agent_id=req.asset_id),
        fee_paid=0.0,
        settlement_network=settlement_network,
    )
    weather = WeatherEngine.analyze(
        WeatherQueryInput(latitude=req.latitude, longitude=req.longitude, altitude_agl_meters=10.0),
        fee_paid=0.0,
        settlement_network=settlement_network,
    )
    rf = RFEngine.analyze(
        RFQueryInput(latitude=req.latitude, longitude=req.longitude, altitude_agl_meters=15.0),
        fee_paid=0.0,
        settlement_network=settlement_network,
    )

    # 2. Parallel live Cloud Run sub-oracle calls (seismic + climate) with graceful fallback
    seismic, climate = await asyncio.gather(
        _query_seismic_suboracle(req),
        _query_climate_suboracle(req),
    )

    # 3. Synthesize Earth Infrastructure Risk Score (0-100)
    weights = _ASSET_WEIGHTS.get(req.asset_type, _ASSET_WEIGHTS["DATA_CENTER"])
    starlink_los = float(rf.satellite.leo_starlink_los_pct)
    connectivity_risk = max(0.0, min(100.0, 100.0 - starlink_los))

    combined_score = round(
        min(
            100.0,
            seismic["severity"] * weights["seismic"]
            + climate["severity"] * weights["climate"]
            + connectivity_risk * weights["connectivity"],
        ),
        2,
    )

    if combined_score >= 70.0 or seismic["force_majeure"] or climate["force_majeure"]:
        risk_grade = "CRITICAL"
        recommended_action = "HALT_OR_FAILOVER"
        settlement_cleared = False
    elif combined_score >= 40.0 or seismic["action"] == "CAUTION" or climate["action"] == "CAUTION":
        risk_grade = "ELEVATED"
        recommended_action = "CAUTION_MONITOR"
        settlement_cleared = True
    elif combined_score >= 20.0:
        risk_grade = "MODERATE"
        recommended_action = "PROCEED_WITH_LOGGING"
        settlement_cleared = True
    else:
        risk_grade = "LOW"
        recommended_action = "CLEAR"
        settlement_cleared = True

    bcbs_flags: List[str] = []
    if seismic["severity"] >= 40.0:
        bcbs_flags.append("ELEVATED_SEISMIC_CORRELATED_RISK")
    if climate["severity"] >= 40.0:
        bcbs_flags.append("EXTREME_CLIMATE_OPERATIONAL_RISK")
    if starlink_los >= 70.0:
        bcbs_flags.append("SATCOM_REDUNDANCY_AVAILABLE")
    else:
        bcbs_flags.append("LIMITED_SATCOM_FAILOVER")
    if seismic["status"] != "OK" or climate["status"] != "OK":
        bcbs_flags.append("SUBORACLE_CONTINGENCY_FALLBACK_ACTIVE")

    latency_ms = round((time.perf_counter() - t0) * 1000, 2)

    proof_payload = json.dumps(
        {
            "asset_id": req.asset_id,
            "asset_type": req.asset_type,
            "lat": req.latitude,
            "lng": req.longitude,
            "combined_score": combined_score,
            "risk_grade": risk_grade,
        },
        sort_keys=True,
    )
    proof_hash = "0x" + hashlib.sha256(proof_payload.encode("utf-8")).hexdigest()

    return {
        "schema_version": "earth-infra-risk/1.0",
        "mode": "FREE_PREVIEW" if preview else "VERIFIED_PAID",
        "asset": {
            "asset_id": req.asset_id,
            "asset_type": req.asset_type,
            "latitude": req.latitude,
            "longitude": req.longitude,
            "commodity": req.commodity,
        },
        "summary": {
            "combined_risk_score": combined_score,
            "risk_grade": risk_grade,
            "recommended_action": recommended_action,
            "settlement_cleared": settlement_cleared,
            "bcbs_resilience_flags": bcbs_flags,
            "latency_ms": latency_ms,
        },
        "layers": {
            "terrain": {
                "elevation_meters": terrain.elevation_meters,
                "slope_degrees": terrain.slope_gradient_degrees,
                "terrain_classification": terrain.terrain_classification,
                "surface_status": terrain.trafficability.overall_status,
            },
            "weather": {
                "temperature_celsius": weather.atmosphere.temperature_celsius,
                "humidity_pct": weather.atmosphere.relative_humidity_pct,
                "wind_speed_mps": weather.wind_vector.horizontal_speed_mps,
                "icing_risk_index": weather.atmosphere.icing_risk_index,
            },
            "connectivity": {
                "cellular_tech": rf.cellular.carrier_technology,
                "rsrp_dbm": rf.cellular.rsrp_dbm,
                "starlink_leo_los_pct": starlink_los,
                "gnss_pdop": rf.satellite.gnss_pdop,
            },
            "seismic": seismic,
            "climate": climate,
        },
        "settlement": {
            "fee_paid_usdc": fee_paid,
            "network": settlement_network,
            "deterministic_proof_hash": proof_hash,
        },
    }


@router.get("/catalog")
async def get_infrastructure_catalog():
    """Free catalog of supported Earth Physical Infrastructure asset classes and live sub-oracles."""
    return {
        "hub": "A.GRID Earth Physical Infrastructure Risk Hub (geo-oracle-x402)",
        "schema_version": "earth-infra-risk/1.0",
        "supported_asset_types": list(_ASSET_WEIGHTS.keys()),
        "sub_oracles": {
            "seismic": SEISMIC_ORACLE_URL,
            "climate": CLIMATE_ORACLE_URL,
        },
        "endpoints": {
            "free_preview": "POST /v1/infrastructure/preview",
            "paid_x402_assess": "POST /v1/infrastructure/assess",
            "x402_challenge": "GET /v1/infrastructure/challenge",
        },
    }


@router.get("/challenge", response_model=X402PaymentRequirement)
async def get_infrastructure_challenge(
    network: Optional[str] = None,
    x_402_preferred_network: Optional[str] = Header(default=None, alias="X-402-Preferred-Network"),
):
    """Request an x402 payment challenge for Earth Physical Infrastructure Risk Assessment."""
    return X402Verifier.generate_challenge(
        price_usdc=ORACLE_PRICE_USDC,
        oracle_name=ORACLE_NAME,
        preferred_network=network or x_402_preferred_network,
    )


@router.post("/preview")
async def preview_infrastructure_risk(body: InfrastructureAssessRequest):
    """Free preview endpoint for EU buyers, financial risk analysts, and AI agents."""
    result = await _run_infrastructure_assessment(
        req=body,
        fee_paid=0.0,
        settlement_network="FREE_PREVIEW",
        preview=True,
    )
    return JSONResponse(status_code=status.HTTP_200_OK, content=result)


@router.post("/assess")
async def assess_infrastructure_risk(
    body: InfrastructureAssessRequest,
    x_402_signature: Optional[str] = Header(default=None, alias="X-402-Signature"),
    authorization: Optional[str] = Header(default=None),
    x_402_preferred_network: Optional[str] = Header(default=None, alias="X-402-Preferred-Network"),
    x_402_network: Optional[str] = Header(default=None, alias="X-402-Network"),
):
    """x402-protected Earth Physical Infrastructure Risk Assessment with deterministic proof hash."""
    auth_header = x_402_signature or authorization
    preferred_net = x_402_preferred_network or x_402_network

    if not auth_header:
        challenge = X402Verifier.generate_challenge(
            price_usdc=ORACLE_PRICE_USDC,
            oracle_name=ORACLE_NAME,
            preferred_network=preferred_net,
        )
        return JSONResponse(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            content=challenge.model_dump(),
            headers={"X-402-Payment-Required": challenge.model_dump_json()},
        )

    is_valid, msg, settlement = X402Verifier.verify_payment_header(auth_header, expected_price_usdc=ORACLE_PRICE_USDC)
    if not is_valid:
        challenge = X402Verifier.generate_challenge(
            price_usdc=ORACLE_PRICE_USDC,
            oracle_name=ORACLE_NAME,
            preferred_network=preferred_net,
        )
        challenge_dict = challenge.model_dump()
        challenge_dict["rejection_reason"] = msg
        return JSONResponse(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            content=challenge_dict,
            headers={
                "X-402-Payment-Required": challenge.model_dump_json(),
                "X-402-Rejection-Reason": msg,
            },
        )

    settlement_net = settlement.get("network", "Polygon") if settlement else "Polygon"
    result = await _run_infrastructure_assessment(
        req=body,
        fee_paid=float(ORACLE_PRICE_USDC),
        settlement_network=settlement_net,
        preview=False,
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=result,
        headers={
            "X-402-Settlement-Status": "VERIFIED_PAID",
            "X-402-Payer": settlement.get("payer", "unknown") if settlement else "unknown",
            "X-402-Network": settlement_net,
            "X-402-Proof-Hash": result["settlement"]["deterministic_proof_hash"],
        },
    )
