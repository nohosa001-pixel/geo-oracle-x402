"""
Comprehensive End-to-End Test Suite for Autonomous Physical AI & Insurance Oracle Hub.
Includes Tests for Real-Time Background Synchronization Telemetry and Ingestion.
"""

import time
import json
import pytest
from httpx import AsyncClient, ASGITransport
from eth_account import Account
from eth_account.messages import encode_typed_data

from app.main import app
from app.core.x402_verifier import X402Verifier


@pytest.fixture
def agent_signer():
    return Account.create()


@pytest.mark.asyncio
async def test_hub_discovery_and_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Root discovery
        r_root = await client.get("/")
        assert r_root.status_code == 200
        data = r_root.json()
        assert data["version"] == "2.2.0"
        assert len(data["oracles_catalog"]) >= 7

        # 2. Health check
        r_health = await client.get("/health")
        assert r_health.status_code == 200
        assert r_health.json()["active_oracles"] >= 6
        assert r_health.json()["live_sync_daemon"] == "RUNNING"

        # 3. AP2 Manifest
        r_ap2 = await client.get("/.well-known/ap2")
        assert r_ap2.status_code == 200
        assert len(r_ap2.json()["capabilities"]) == 7

        # 4. FastMCP spec
        r_mcp = await client.get("/mcp/tools")
        assert r_mcp.status_code == 200
        assert len(r_mcp.json()["tools"]) >= 7  # 10 tools supported in v2.2.0 suite


@pytest.mark.asyncio
async def test_system_sync_daemon_telemetry():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Check live sync status
        r_status = await client.get("/v1/system/sync-status")
        assert r_status.status_code == 200
        status_data = r_status.json()
        assert status_data["daemon_status"] == "ONLINE_ACTIVE"
        assert "weather_noaa_gfs" in status_data["feeds"]
        assert "airspace_notams" in status_data["feeds"]
        assert "satcom_rf_mesh" in status_data["feeds"]

        # 2. Trigger on-demand sync cycle
        r_trigger = await client.post("/v1/system/trigger-sync")
        assert r_trigger.status_code == 200
        assert "successfully" in r_trigger.json()["message"]


@pytest.mark.asyncio
async def test_oracle_1_terrain_e2e(agent_signer):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {"latitude": 45.8326, "longitude": 6.8652, "sampling_radius_meters": 30.0}
        r_unpaid = await client.post("/v1/terrain/analyze", json=payload)
        assert r_unpaid.status_code == 402
        nonce, price = r_unpaid.json()["nonce"], r_unpaid.json()["price_usdc"]

        now_ts = int(time.time())
        eip712_data = X402Verifier.build_eip712_structure(nonce=nonce, timestamp=now_ts, amount=price)
        signed = Account.sign_message(encode_typed_data(full_message=eip712_data), private_key=agent_signer.key)
        auth = json.dumps({
            "payer_address": agent_signer.address,
            "signature": "0x" + signed.signature.hex(),
            "nonce": nonce,
            "timestamp": now_ts,
            "amount_usdc": price,
            "type": "eip712",
        })

        r_paid = await client.post("/v1/terrain/analyze", json=payload, headers={"X-402-Signature": auth})
        assert r_paid.status_code == 200
        assert r_paid.json()["oracle_type"] == "TERRAIN_PHYSICS"


@pytest.mark.asyncio
async def test_oracle_2_weather_e2e(agent_signer):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {"latitude": 37.5665, "longitude": 126.9780, "altitude_agl_meters": 80.0}
        r_chal = await client.get("/v1/weather/challenge")
        nonce, price = r_chal.json()["nonce"], r_chal.json()["price_usdc"]

        now_ts = int(time.time())
        eip712_data = X402Verifier.build_eip712_structure(nonce=nonce, timestamp=now_ts, amount=price)
        signed = Account.sign_message(encode_typed_data(full_message=eip712_data), private_key=agent_signer.key)
        auth = json.dumps({
            "payer_address": agent_signer.address,
            "signature": "0x" + signed.signature.hex(),
            "nonce": nonce,
            "timestamp": now_ts,
            "amount_usdc": price,
            "type": "eip712",
        })

        r_paid = await client.post("/v1/weather/analyze", json=payload, headers={"X-402-Signature": auth})
        assert r_paid.status_code == 200
        assert r_paid.json()["oracle_type"] == "MICRO_WEATHER_TURBULENCE"


@pytest.mark.asyncio
async def test_oracle_3_geofence_e2e(agent_signer):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {"latitude": 37.5665, "longitude": 126.9780, "altitude_agl_meters": 100.0}
        r_chal = await client.get("/v1/geofence/challenge")
        nonce, price = r_chal.json()["nonce"], r_chal.json()["price_usdc"]

        now_ts = int(time.time())
        eip712_data = X402Verifier.build_eip712_structure(nonce=nonce, timestamp=now_ts, amount=price)
        signed = Account.sign_message(encode_typed_data(full_message=eip712_data), private_key=agent_signer.key)
        auth = json.dumps({
            "payer_address": agent_signer.address,
            "signature": "0x" + signed.signature.hex(),
            "nonce": nonce,
            "timestamp": now_ts,
            "amount_usdc": price,
            "type": "eip712",
        })

        r_paid = await client.post("/v1/geofence/check", json=payload, headers={"X-402-Signature": auth})
        assert r_paid.status_code == 200
        assert r_paid.json()["oracle_type"] == "AIRSPACE_GEOFENCE_REGULATORY"


@pytest.mark.asyncio
async def test_oracle_4_rf_coverage_e2e(agent_signer):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {"latitude": 35.6762, "longitude": 139.6503, "altitude_agl_meters": 60.0}
        r_chal = await client.get("/v1/rf/challenge")
        nonce, price = r_chal.json()["nonce"], r_chal.json()["price_usdc"]

        now_ts = int(time.time())
        eip712_data = X402Verifier.build_eip712_structure(nonce=nonce, timestamp=now_ts, amount=price)
        signed = Account.sign_message(encode_typed_data(full_message=eip712_data), private_key=agent_signer.key)
        auth = json.dumps({
            "payer_address": agent_signer.address,
            "signature": "0x" + signed.signature.hex(),
            "nonce": nonce,
            "timestamp": now_ts,
            "amount_usdc": price,
            "type": "eip712",
        })

        r_paid = await client.post("/v1/rf/coverage", json=payload, headers={"X-402-Signature": auth})
        assert r_paid.status_code == 200
        assert r_paid.json()["oracle_type"] == "RF_COVERAGE_SATCOM_MESH"


@pytest.mark.asyncio
async def test_oracle_5_energy_routing_e2e(agent_signer):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "origin_latitude": 37.5665,
            "origin_longitude": 126.9780,
            "destination_latitude": 37.5750,
            "destination_longitude": 126.9950,
            "cruise_altitude_agl_meters": 60.0,
            "vehicle_mass_kg": 6.5,
            "battery_capacity_wh": 250.0,
        }
        r_chal = await client.get("/v1/routing/challenge")
        nonce, price = r_chal.json()["nonce"], r_chal.json()["price_usdc"]
        assert price == "0.010"

        now_ts = int(time.time())
        eip712_data = X402Verifier.build_eip712_structure(nonce=nonce, timestamp=now_ts, amount=price)
        signed = Account.sign_message(encode_typed_data(full_message=eip712_data), private_key=agent_signer.key)
        auth = json.dumps({
            "payer_address": agent_signer.address,
            "signature": "0x" + signed.signature.hex(),
            "nonce": nonce,
            "timestamp": now_ts,
            "amount_usdc": price,
            "type": "eip712",
        })

        r_paid = await client.post("/v1/routing/energy-optimal", json=payload, headers={"X-402-Signature": auth})
        assert r_paid.status_code == 200
        assert r_paid.json()["oracle_type"] == "ENERGY_OPTIMAL_ROUTING"


@pytest.mark.asyncio
async def test_oracle_6_insurance_underwriting_and_claim_e2e(agent_signer):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        underwrite_payload = {
            "origin_latitude": 37.4563,
            "origin_longitude": 126.6128,
            "destination_latitude": 37.3827,
            "destination_longitude": 126.6573,
            "cruise_altitude_agl_meters": 70.0,
            "vehicle_hull_value_usdc": 4000.0,
            "cargo_value_usdc": 2000.0,
            "operator_id": "Test-Delivery-Fleet",
        }
        
        # 1. Underwrite Challenge (0.025 USDC)
        r_chal = await client.get("/v1/insurance/challenge")
        assert r_chal.status_code == 200
        nonce = r_chal.json()["nonce"]
        price = r_chal.json()["price_usdc"]
        assert price == "0.025"

        # 2. Sign and Underwrite
        now_ts = int(time.time())
        eip712_data = X402Verifier.build_eip712_structure(nonce=nonce, timestamp=now_ts, amount=price)
        signed = Account.sign_message(encode_typed_data(full_message=eip712_data), private_key=agent_signer.key)
        auth = json.dumps({
            "payer_address": agent_signer.address,
            "signature": "0x" + signed.signature.hex(),
            "nonce": nonce,
            "timestamp": now_ts,
            "amount_usdc": price,
            "type": "eip712",
        })

        r_underwrite = await client.post("/v1/insurance/underwrite", json=underwrite_payload, headers={"X-402-Signature": auth})
        assert r_underwrite.status_code == 200
        uw_out = r_underwrite.json()
        assert uw_out["oracle_type"] == "INSURANCE_UNDERWRITING_AND_CLEARANCE"
        assert "policy" in uw_out
        policy_id = uw_out["policy"]["policy_id"]
        poi_hash = uw_out["policy"]["proof_of_insurability_hash"]

        # 3. Simulate Force Majeure Incident Claim Verification (0.050 USDC fee)
        claim_payload = {
            "policy_id": policy_id,
            "proof_of_insurability_hash": poi_hash,
            "incident_timestamp": int(time.time()) + 1800,
            "incident_latitude": 37.4100,
            "incident_longitude": 126.6300,
            "blackbox_wind_gust_recorded_mps": 18.5,
            "blackbox_c2_link_loss_seconds": 12.0,
            "blackbox_path_deviation_meters": 15.0,
            "actual_damage_loss_usdc": 4200.0,
        }

        r_claim_chal = await client.get("/v1/insurance/claim-challenge")
        c_nonce = r_claim_chal.json()["nonce"]
        c_price = r_claim_chal.json()["price_usdc"]

        c_now = int(time.time())
        c_eip712 = X402Verifier.build_eip712_structure(nonce=c_nonce, timestamp=c_now, amount=c_price)
        c_signed = Account.sign_message(encode_typed_data(full_message=c_eip712), private_key=agent_signer.key)
        c_auth = json.dumps({
            "payer_address": agent_signer.address,
            "signature": "0x" + c_signed.signature.hex(),
            "nonce": c_nonce,
            "timestamp": c_now,
            "amount_usdc": c_price,
            "type": "eip712",
        })

        r_claim = await client.post("/v1/insurance/claim-verify", json=claim_payload, headers={"X-402-Signature": c_auth})
        assert r_claim.status_code == 200
        claim_out = r_claim.json()
        assert claim_out["oracle_type"] == "PARAMETRIC_CLAIM_ADJUDICATION"
        assert claim_out["adjudication_verdict"] == "APPROVED_PAYOUT"
