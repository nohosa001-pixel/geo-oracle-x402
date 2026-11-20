"""
Comprehensive End-to-End Test Suite for A.GRID Earth Physical Infrastructure Risk Hub (v3.0.0).
Covers Hub Discovery, Live Sync Telemetry, Core Physical Oracles (Terrain, Weather, RF),
and the Unified Earth Infrastructure Risk Hub (/v1/infrastructure/*).
"""

import json
import time
from unittest.mock import AsyncMock, patch

import pytest
from eth_account import Account
from eth_account.messages import encode_typed_data
from httpx import ASGITransport, AsyncClient

from app.core.x402_verifier import X402Verifier
from app.main import app


@pytest.fixture
def agent_signer():
    return Account.create()


def _sign_eip712(signer: Account, nonce: str, price: str) -> str:
    now_ts = int(time.time())
    eip712_data = X402Verifier.build_eip712_structure(nonce=nonce, timestamp=now_ts, amount=price)
    signed = Account.sign_message(encode_typed_data(full_message=eip712_data), private_key=signer.key)
    return json.dumps({
        "payer_address": signer.address,
        "signature": "0x" + signed.signature.hex(),
        "nonce": nonce,
        "timestamp": now_ts,
        "amount_usdc": price,
        "type": "eip712",
    })


@pytest.mark.asyncio
async def test_hub_discovery_and_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r_root = await client.get("/")
        assert r_root.status_code == 200
        data = r_root.json()
        assert data["service"] == "geo-oracle-x402"
        assert data["version"] == "3.0.0"
        assert len(data["oracles_catalog"]) == 4

        r_health = await client.get("/health")
        assert r_health.status_code == 200
        health = r_health.json()
        assert health["status"] == "healthy"
        assert health["active_oracles"] == 4
        assert health["live_sync_daemon"] == "RUNNING"

        r_card = await client.get("/.well-known/agent-card.json")
        assert r_card.status_code == 200
        assert r_card.json()["name"] == "geo-oracle-x402"

        r_llms = await client.get("/llms.txt")
        assert r_llms.status_code == 200
        assert "POST /v1/infrastructure/assess" in r_llms.text

        r_ap2 = await client.get("/.well-known/ap2")
        assert r_ap2.status_code == 200
        assert r_ap2.json()["version"] == "3.0.0"


@pytest.mark.asyncio
async def test_system_sync_daemon_telemetry():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r_status = await client.get("/v1/system/sync-status")
        assert r_status.status_code == 200
        status_data = r_status.json()
        assert status_data["daemon_status"] == "ONLINE_ACTIVE"
        assert "weather_noaa_gfs" in status_data["feeds"]
        assert "airspace_notams" in status_data["feeds"]
        assert "satcom_rf_mesh" in status_data["feeds"]

        r_trigger = await client.post("/v1/system/trigger-sync")
        assert r_trigger.status_code == 200
        assert "successfully" in r_trigger.json()["message"]


@pytest.mark.asyncio
async def test_oracle_terrain_e2e(agent_signer):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {"latitude": 45.8326, "longitude": 6.8652, "sampling_radius_meters": 30.0}
        r_unpaid = await client.post("/v1/terrain/analyze", json=payload)
        assert r_unpaid.status_code == 402
        nonce, price = r_unpaid.json()["nonce"], r_unpaid.json()["price_usdc"]

        auth = _sign_eip712(agent_signer, nonce, price)
        r_paid = await client.post("/v1/terrain/analyze", json=payload, headers={"X-402-Signature": auth})
        assert r_paid.status_code == 200
        assert r_paid.json()["oracle_type"] == "TERRAIN_PHYSICS"


@pytest.mark.asyncio
async def test_oracle_weather_e2e(agent_signer):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {"latitude": 37.5665, "longitude": 126.9780, "altitude_agl_meters": 80.0}
        r_chal = await client.get("/v1/weather/challenge")
        nonce, price = r_chal.json()["nonce"], r_chal.json()["price_usdc"]

        auth = _sign_eip712(agent_signer, nonce, price)
        r_paid = await client.post("/v1/weather/analyze", json=payload, headers={"X-402-Signature": auth})
        assert r_paid.status_code == 200
        assert r_paid.json()["oracle_type"] == "MICRO_WEATHER_TURBULENCE"


@pytest.mark.asyncio
async def test_oracle_rf_coverage_e2e(agent_signer):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {"latitude": 35.6762, "longitude": 139.6503, "altitude_agl_meters": 60.0}
        r_chal = await client.get("/v1/rf/challenge")
        nonce, price = r_chal.json()["nonce"], r_chal.json()["price_usdc"]

        auth = _sign_eip712(agent_signer, nonce, price)
        r_paid = await client.post("/v1/rf/coverage", json=payload, headers={"X-402-Signature": auth})
        assert r_paid.status_code == 200
        assert r_paid.json()["oracle_type"] == "RF_COVERAGE_SATCOM_MESH"


@pytest.mark.asyncio
async def test_infrastructure_catalog_and_free_preview():
    mock_seismic = {
        "status": "OK",
        "action": "CLEAR",
        "severity": 12.0,
        "force_majeure": False,
        "alternate_hubs": [],
        "url": "https://mock-seismic",
    }
    mock_climate = {
        "status": "OK",
        "action": "CLEAR",
        "severity": 18.0,
        "force_majeure": False,
        "parametric_payout_rate": 0.0,
        "url": "https://mock-climate",
    }

    with (
        patch("app.oracles.infrastructure.router._query_seismic_suboracle", new=AsyncMock(return_value=mock_seismic)),
        patch("app.oracles.infrastructure.router._query_climate_suboracle", new=AsyncMock(return_value=mock_climate)),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r_cat = await client.get("/v1/infrastructure/catalog")
            assert r_cat.status_code == 200
            cat = r_cat.json()
            assert "DATA_CENTER" in cat["supported_asset_types"]
            assert "SUBSEA_CABLE" in cat["supported_asset_types"]

            r_prev = await client.post(
                "/v1/infrastructure/preview",
                json={
                    "asset_id": "DC-SEOUL-01",
                    "asset_type": "DATA_CENTER",
                    "latitude": 37.5665,
                    "longitude": 126.9780,
                    "commodity": "AI_COMPUTE",
                },
            )
            assert r_prev.status_code == 200
            prev = r_prev.json()
            assert prev["schema_version"] == "earth-infra-risk/1.0"
            assert prev["mode"] == "FREE_PREVIEW"
            assert prev["settlement"]["fee_paid_usdc"] == 0.0
            assert "terrain" in prev["layers"]
            assert "weather" in prev["layers"]
            assert "connectivity" in prev["layers"]
            assert prev["layers"]["seismic"]["status"] == "OK"
            assert prev["layers"]["climate"]["status"] == "OK"


@pytest.mark.asyncio
async def test_infrastructure_assess_x402_e2e(agent_signer):
    mock_seismic = {
        "status": "OK",
        "action": "CAUTION",
        "severity": 65.0,
        "force_majeure": False,
        "alternate_hubs": ["BUSAN-DC"],
        "url": "https://mock-seismic",
    }
    mock_climate = {
        "status": "OK",
        "action": "CLEAR",
        "severity": 30.0,
        "force_majeure": False,
        "parametric_payout_rate": 0.0,
        "url": "https://mock-climate",
    }

    with (
        patch("app.oracles.infrastructure.router._query_seismic_suboracle", new=AsyncMock(return_value=mock_seismic)),
        patch("app.oracles.infrastructure.router._query_climate_suboracle", new=AsyncMock(return_value=mock_climate)),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            payload = {
                "asset_id": "PORT-TOKYO-01",
                "asset_type": "PORT",
                "latitude": 35.6528,
                "longitude": 139.7760,
                "commodity": "SEMICONDUCTOR",
            }
            r_unpaid = await client.post("/v1/infrastructure/assess", json=payload)
            assert r_unpaid.status_code == 402
            chal = r_unpaid.json()
            nonce, price = chal["nonce"], chal["price_usdc"]
            assert price == "0.015"

            auth = _sign_eip712(agent_signer, nonce, price)
            r_paid = await client.post(
                "/v1/infrastructure/assess",
                json=payload,
                headers={"X-402-Signature": auth},
            )
            assert r_paid.status_code == 200
            assert r_paid.headers["X-402-Settlement-Status"] == "VERIFIED_PAID"
            assert r_paid.headers["X-402-Proof-Hash"].startswith("0x")

            body = r_paid.json()
            assert body["mode"] == "VERIFIED_PAID"
            assert body["summary"]["risk_grade"] in ("ELEVATED", "CRITICAL")
            assert "ELEVATED_SEISMIC_CORRELATED_RISK" in body["summary"]["bcbs_resilience_flags"]
            assert body["settlement"]["fee_paid_usdc"] == 0.015
