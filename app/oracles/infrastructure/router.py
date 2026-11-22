"""
A.GRID Earth Physical Infrastructure Risk Hub Router (x402).
Synthesizes live Open-Meteo Copernicus DEM Elevation, live Open-Meteo Site Weather,
5G/Starlink RF Connectivity, Global Critical Asset Registry, and live Cloud Run
Seismic (global-earthquake-agent) & Climate (climate-insurance-agent) sub-oracles.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from typing import Any, Dict, List, Literal, Optional

import httpx
from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.base_schemas import X402PaymentRequirement
from app.core.live_earth_feeds import fetch_live_elevation, fetch_live_weather
from app.core.observability import log_event
from app.core.x402_verifier import X402Verifier
from app.oracles.infrastructure.registry import get_asset_by_id, list_assets
from app.oracles.rf_coverage.engine import RFEngine
from app.oracles.rf_coverage.schemas import RFQueryInput
from app.oracles.terrain.engine import TerrainEngine
from app.oracles.terrain.schemas import GeoCoordinateInput

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
    asset_id: str = Field(..., description="Asset ID (e.g. DC-TOKYO-JP from /v1/infrastructure/assets, or custom ID)")
    asset_type: Optional[AssetType] = Field(default=None, description="Physical infrastructure asset class")
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0, description="WGS84 Latitude (optional if asset_id is registered)")
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0, description="WGS84 Longitude (optional if asset_id is registered)")
    commodity: Optional[str] = Field(default=None, description="Optional commodity or workload tag (e.g. AI_COMPUTE, LITHIUM, SOYBEAN)")
    use_live_feed: bool = Field(default=True, description="Query live Open-Meteo, seismic & climate sub-oracles")


def _resolve_asset_coordinates(req: InfrastructureAssessRequest) -> tuple[float, float, str, str, Optional[str]]:
    registered = get_asset_by_id(req.asset_id)
    lat = req.latitude if req.latitude is not None else (registered["latitude"] if registered else None)
    lon = req.longitude if req.longitude is not None else (registered["longitude"] if registered else None)
    if lat is None or lon is None:
        raise HTTPException(
            status_code=422,
            detail=f"latitude and longitude are required for unregistered asset_id '{req.asset_id}'.",
        )
    asset_type = req.asset_type or (registered["asset_type"] if registered else "DATA_CENTER")
    commodity = req.commodity or (registered["commodity"] if registered else "INFRASTRUCTURE")
    asset_name = registered["name"] if registered else None
    return float(lat), float(lon), asset_type, commodity, asset_name


async def _query_seismic_suboracle(
    asset_id: str, lat: float, lon: float, asset_type: str, commodity: str, use_live_feed: bool
) -> Dict[str, Any]:
    payload = {
        "waypoints": [
            {
                "asset_id": asset_id,
                "lat": lat,
                "lng": lon,
                "asset_type": asset_type,
                "commodity": commodity,
            }
        ],
        "use_live_feed": use_live_feed,
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
    except Exception as exc:
        log_event(
            "suboracle_degraded_fallback",
            severity="WARNING",
            suboracle="seismic",
            asset_id=asset_id,
            url=SEISMIC_ORACLE_URL,
            error=str(exc),
        )
        return {
            "status": "DEGRADED_FALLBACK",
            "action": "CLEAR",
            "severity": 0.0,
            "force_majeure": False,
            "alternate_hubs": [],
            "url": SEISMIC_ORACLE_URL,
        }


async def _query_climate_suboracle(
    asset_id: str, lat: float, lon: float, asset_type: str, commodity: str, use_live_feed: bool
) -> Dict[str, Any]:
    payload = {
        "waypoints": [
            {
                "asset_id": asset_id,
                "lat": lat,
                "lng": lon,
                "asset_type": asset_type,
                "commodity": commodity,
            }
        ],
        "use_live_feed": use_live_feed,
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
    except Exception as exc:
        log_event(
            "suboracle_degraded_fallback",
            severity="WARNING",
            suboracle="climate",
            asset_id=asset_id,
            url=CLIMATE_ORACLE_URL,
            error=str(exc),
        )
        return {
            "status": "DEGRADED_FALLBACK",
            "action": "CLEAR",
            "severity": 0.0,
            "force_majeure": False,
            "url": CLIMATE_ORACLE_URL,
        }


def _classify_site_indicators(
    elevation_m: float, temp_c: float, wind_mps: float, asset_type: str
) -> tuple[str, str, str, float]:
    """Computes infrastructure-specific operational stress indicators and bonus risk penalty."""
    if elevation_m < 5.0 and asset_type != "SUBSEA_CABLE":
        flood_risk = "HIGH"
        flood_penalty = 12.0
    elif elevation_m < 15.0 and asset_type != "SUBSEA_CABLE":
        flood_risk = "MODERATE"
        flood_penalty = 5.0
    else:
        flood_risk = "LOW"
        flood_penalty = 0.0

    if temp_c >= 35.0:
        cooling_stress = "HIGH"
        cooling_penalty = 12.0 if asset_type in ("DATA_CENTER", "POWER_GRID") else 5.0
    elif temp_c >= 28.0:
        cooling_stress = "MODERATE"
        cooling_penalty = 4.0 if asset_type in ("DATA_CENTER", "POWER_GRID") else 1.5
    else:
        cooling_stress = "LOW"
        cooling_penalty = 0.0

    if wind_mps >= 20.0:
        wind_hazard = "HIGH"
        wind_penalty = 10.0 if asset_type in ("PORT", "POWER_GRID", "LOGISTICS_HUB") else 3.0
    elif wind_mps >= 12.0:
        wind_hazard = "MODERATE"
        wind_penalty = 4.0 if asset_type in ("PORT", "POWER_GRID") else 1.0
    else:
        wind_hazard = "LOW"
        wind_penalty = 0.0

    return flood_risk, cooling_stress, wind_hazard, (flood_penalty + cooling_penalty + wind_penalty)


async def _run_infrastructure_assessment(
    req: InfrastructureAssessRequest,
    fee_paid: float,
    settlement_network: str,
    preview: bool = False,
) -> Dict[str, Any]:
    t0 = time.perf_counter()
    lat, lon, asset_type, commodity, asset_name = _resolve_asset_coordinates(req)

    # 1. Local deterministic slope/RF layers
    terrain = TerrainEngine.analyze(
        input_data=GeoCoordinateInput(latitude=lat, longitude=lon, agent_id=req.asset_id),
        fee_paid=0.0,
        settlement_network=settlement_network,
    )
    rf = RFEngine.analyze(
        RFQueryInput(latitude=lat, longitude=lon, altitude_agl_meters=15.0),
        fee_paid=0.0,
        settlement_network=settlement_network,
    )

    # 2. Concurrent live Earth telemetry (Open-Meteo DEM + Weather + Cloud Run Seismic + Climate)
    if req.use_live_feed:
        elev_data, weather_data, seismic, climate = await asyncio.gather(
            fetch_live_elevation(lat, lon),
            fetch_live_weather(lat, lon),
            _query_seismic_suboracle(req.asset_id, lat, lon, asset_type, commodity, True),
            _query_climate_suboracle(req.asset_id, lat, lon, asset_type, commodity, True),
        )
    else:
        elev_data = {"elevation_meters": round(terrain.elevation_meters, 1), "source": "DETERMINISTIC_FALLBACK"}
        weather_data = {
            "temperature_celsius": 18.0,
            "humidity_pct": 55.0,
            "surface_pressure_hpa": 1013.25,
            "wind_speed_mps": 4.0,
            "wind_direction_deg": 180.0,
            "precipitation_mm": 0.0,
            "source": "DETERMINISTIC_FALLBACK",
        }
        seismic = {"status": "DEGRADED_FALLBACK", "action": "CLEAR", "severity": 0.0, "force_majeure": False, "alternate_hubs": [], "url": SEISMIC_ORACLE_URL}
        climate = {"status": "DEGRADED_FALLBACK", "action": "CLEAR", "severity": 0.0, "force_majeure": False, "url": CLIMATE_ORACLE_URL}

    elevation_m = float(elev_data["elevation_meters"])
    temp_c = float(weather_data["temperature_celsius"])
    wind_mps = float(weather_data["wind_speed_mps"])

    flood_risk, cooling_stress, wind_hazard, site_penalty = _classify_site_indicators(
        elevation_m, temp_c, wind_mps, asset_type
    )

    # 3. Synthesize Earth Infrastructure Risk Score (0-100)
    # Re-normalize weights across active (non-degraded) layers so a sub-oracle outage
    # does not artificially deflate the composite risk score toward 0.
    weights = _ASSET_WEIGHTS.get(asset_type, _ASSET_WEIGHTS["DATA_CENTER"])
    starlink_los = float(rf.satellite.leo_starlink_los_pct)
    connectivity_risk = max(0.0, min(100.0, 100.0 - starlink_los))

    degraded_layers: List[str] = []
    active_components: List[tuple[float, float]] = [(connectivity_risk, weights["connectivity"])]
    if seismic["status"] == "OK":
        active_components.append((seismic["severity"], weights["seismic"]))
    else:
        degraded_layers.append("seismic")

    if climate["status"] == "OK":
        active_components.append((climate["severity"], weights["climate"]))
    else:
        degraded_layers.append("climate")

    total_active_weight = sum(w for _, w in active_components) or 1.0
    weighted_hazard = sum(val * (w / total_active_weight) for val, w in active_components)
    combined_score = round(min(100.0, weighted_hazard + site_penalty), 2)

    if len(degraded_layers) == 0:
        assessment_confidence = "HIGH"
    elif len(degraded_layers) == 1:
        assessment_confidence = "PARTIAL"
    else:
        assessment_confidence = "DEGRADED"

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
    if flood_risk == "HIGH":
        bcbs_flags.append("LOW_ELEVATION_FLOOD_EXPOSURE")
    if cooling_stress == "HIGH":
        bcbs_flags.append("THERMAL_COOLING_STRESS")
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
            "asset_type": asset_type,
            "lat": lat,
            "lng": lon,
            "combined_score": combined_score,
            "risk_grade": risk_grade,
        },
        sort_keys=True,
    )
    proof_hash = "0x" + hashlib.sha256(proof_payload.encode("utf-8")).hexdigest()

    return {
        "schema_version": "earth-infra-risk/1.1",
        "mode": "FREE_PREVIEW" if preview else "VERIFIED_PAID",
        "asset": {
            "asset_id": req.asset_id,
            "name": asset_name,
            "asset_type": asset_type,
            "latitude": lat,
            "longitude": lon,
            "commodity": commodity,
        },
        "summary": {
            "combined_risk_score": combined_score,
            "risk_grade": risk_grade,
            "recommended_action": recommended_action,
            "settlement_cleared": settlement_cleared,
            "assessment_confidence": assessment_confidence,
            "degraded_layers": degraded_layers,
            "flood_elevation_risk": flood_risk,
            "cooling_heat_stress": cooling_stress,
            "wind_hazard_level": wind_hazard,
            "bcbs_resilience_flags": bcbs_flags,
            "latency_ms": latency_ms,
        },
        "layers": {
            "terrain": {
                "elevation_meters": elevation_m,
                "slope_degrees": terrain.slope_gradient_degrees,
                "terrain_classification": terrain.terrain_classification,
                "data_source": elev_data["source"],
            },
            "weather": {
                "temperature_celsius": temp_c,
                "humidity_pct": weather_data["humidity_pct"],
                "surface_pressure_hpa": weather_data["surface_pressure_hpa"],
                "wind_speed_mps": wind_mps,
                "wind_direction_deg": weather_data["wind_direction_deg"],
                "precipitation_mm": weather_data["precipitation_mm"],
                "data_source": weather_data["source"],
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
        "schema_version": "earth-infra-risk/1.1",
        "supported_asset_types": list(_ASSET_WEIGHTS.keys()),
        "registered_assets_count": len(list_assets()),
        "sub_oracles": {
            "seismic": SEISMIC_ORACLE_URL,
            "climate": CLIMATE_ORACLE_URL,
        },
        "endpoints": {
            "asset_registry": "GET /v1/infrastructure/assets",
            "free_preview": "POST /v1/infrastructure/preview",
            "paid_x402_assess": "POST /v1/infrastructure/assess",
            "x402_challenge": "GET /v1/infrastructure/challenge",
        },
    }


@router.get("/assets")
async def get_registered_infrastructure_assets(asset_type: Optional[str] = None):
    """Free Global Critical Infrastructure Asset Registry (Data Centers, Ports, Mines, Subsea Cables, Farms)."""
    assets = list_assets(asset_type=asset_type)
    return {
        "count": len(assets),
        "filter_asset_type": asset_type.upper() if asset_type else None,
        "assets": assets,
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
