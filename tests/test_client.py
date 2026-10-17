"""
Comprehensive Agent Test Client and Unit/Integration Tests.
Tests x402 payment challenge-response flow, EIP-712 / EIP-191 signatures,
Google AP2 manifest, MCP tools, and deterministic terrain physics output.
"""

import time
import json
import pytest
from httpx import AsyncClient, ASGITransport
from eth_account import Account
from eth_account.messages import encode_defunct, encode_typed_data

from app.main import app
from app.core.x402_verifier import (
    X402Verifier,
    POLYGON_CHAIN_ID,
    USDC_POLYGON_ADDRESS,
    ORACLE_RECIPIENT_WALLET,
    DEFAULT_MICRO_PRICE_USDC as MICRO_PRICE_USDC,
)


@pytest.fixture
def agent_wallet():
    """Generates an ephemeral autonomous agent test wallet."""
    # Deterministic test private key
    acct = Account.from_key("0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d")
    return acct


@pytest.mark.asyncio
async def test_health_and_root_endpoints():
    """Verifies service health, root metadata, and AP2 manifest endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test Root Info
        root_res = await client.get("/")
        assert root_res.status_code == 200
        root_data = root_res.json()
        assert root_data["service"] == "autonomous-physical-ai-oracle-suite"
        assert root_data["version"] == "2.2.0"
        assert len(root_data["oracles_catalog"]) >= 7

        # Test Health
        health_res = await client.get("/health")
        assert health_res.status_code == 200
        assert health_res.json()["status"] == "healthy"
        assert health_res.json()["active_oracles"] >= 6

        # Test Google AP2 Manifest
        ap2_res = await client.get("/.well-known/ap2")
        assert ap2_res.status_code == 200
        ap2_data = ap2_res.json()
        assert ap2_data["name"] == "autonomous-physical-ai-oracle-suite"
        assert ap2_data["monetization"]["network"] == "polygon"
        assert len(ap2_data["capabilities"]) == 7

        # Test FastMCP Spec
        mcp_res = await client.get("/mcp/tools")
        assert mcp_res.status_code == 200
        mcp_data = mcp_res.json()
        assert "tools" in mcp_data
        assert len(mcp_data["tools"]) >= 7  # 10 tools supported in v2.2.0 suite


@pytest.mark.asyncio
async def test_402_payment_challenge_on_unauthenticated_request():
    """Verifies that an unauthenticated agent receives HTTP 402 with challenge details."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "latitude": 37.7749,
            "longitude": -122.4194,
            "sampling_radius_meters": 30.0,
            "agent_id": "rover-alpha-01"
        }
        res = await client.post("/v1/terrain/analyze", json=payload)
        
        # Must return HTTP 402 Payment Required
        assert res.status_code == 402
        assert "X-402-Payment-Required" in res.headers
        
        challenge_data = res.json()
        assert challenge_data["protocol"] == "x402"
        assert challenge_data["network"] == "polygon"
        assert challenge_data["chain_id"] == 137
        assert challenge_data["token_symbol"] == "USDC"
        assert challenge_data["price_usdc"] == "0.005"
        assert challenge_data["recipient_address"] == ORACLE_RECIPIENT_WALLET
        assert challenge_data["nonce"].startswith("x402_")


@pytest.mark.asyncio
async def test_full_eip712_payment_and_oracle_analysis_cycle(agent_wallet):
    """
    Simulates full autonomous agent lifecycle:
    1. Send terrain query
    2. Intercept HTTP 402 + Challenge Nonce
    3. Sign EIP-712 Micropayment authorization with agent's private key
    4. Re-issue request with X-402-Signature header
    5. Receive HTTP 200 + Deterministic Terrain Physics Data
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        query_payload = {
            "latitude": 45.8326,  # Mont Blanc region (steep mountainous terrain)
            "longitude": 6.8652,
            "sampling_radius_meters": 30.0,
            "agent_id": "quadruped-scout-9"
        }

        # Step 1: Initial query -> Get 402 Challenge
        init_res = await client.post("/v1/terrain/analyze", json=query_payload)
        assert init_res.status_code == 402
        challenge = init_res.json()
        nonce = challenge["nonce"]

        # Step 2: Agent signs EIP-712 structured data
        now_ts = int(time.time())
        eip712_data = X402Verifier.build_eip712_structure(
            nonce=nonce,
            timestamp=now_ts,
            amount="0.005"
        )
        encoded_data = encode_typed_data(full_message=eip712_data)
        signed_message = Account.sign_message(encoded_data, private_key=agent_wallet.key)
        signature_hex = signed_message.signature.hex()
        if not signature_hex.startswith("0x"):
            signature_hex = "0x" + signature_hex

        # Step 3: Package X-402-Signature Header
        x402_auth_payload = {
            "payer_address": agent_wallet.address,
            "signature": signature_hex,
            "nonce": nonce,
            "timestamp": now_ts,
            "amount_usdc": "0.005",
            "type": "eip712"
        }
        auth_header_val = json.dumps(x402_auth_payload)

        # Step 4: Submit request with payment authorization
        paid_res = await client.post(
            "/v1/terrain/analyze",
            json=query_payload,
            headers={"X-402-Signature": auth_header_val}
        )

        # Step 5: Verify Oracle Result
        assert paid_res.status_code == 200
        assert paid_res.headers.get("X-402-Settlement-Status") == "VERIFIED_PAID"

        data = paid_res.json()
        assert data["latitude"] == 45.8326
        assert data["longitude"] == 6.8652
        assert "elevation_meters" in data
        assert "slope_gradient_degrees" in data
        assert "slope_gradient_percentage" in data
        assert "aspect_degrees" in data
        assert "aspect_compass" in data
        assert "solar_exposure_index" in data
        assert "terrain_classification" in data
        assert "soil_roughness_score" in data
        assert "trafficability" in data
        assert "physics" in data
        assert data["deterministic_proof_hash"].startswith("0x")
        assert data["fee_paid_usdc"] == 0.005
        assert data["settlement_network"] == "Polygon (Chain ID 137)"

        # Check trafficability subfields
        traffic = data["trafficability"]
        assert 0.0 <= traffic["wheeled_rover_score"] <= 1.0
        assert 0.0 <= traffic["tracked_vehicle_score"] <= 1.0
        assert 0.0 <= traffic["quadruped_bot_score"] <= 1.0
        assert 0.0 <= traffic["drone_landing_score"] <= 1.0
        assert traffic["overall_status"] in ["GO", "CAUTION", "HAZARDOUS", "IMPASSABLE"]

        # Check physics subfields
        physics = data["physics"]
        assert physics["friction_coefficient_mu"] > 0
        assert physics["max_safe_speed_mps"] > 0
        assert 0.0 <= physics["tip_over_risk_index"] <= 1.0


@pytest.mark.asyncio
async def test_replay_attack_prevention(agent_wallet):
    """Verifies that a consumed nonce cannot be reused (replay protection)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1: Get challenge
        c_res = await client.get("/v1/terrain/challenge")
        challenge = c_res.json()
        nonce = challenge["nonce"]

        # Step 2: Sign and spend
        now_ts = int(time.time())
        eip712_data = X402Verifier.build_eip712_structure(nonce=nonce, timestamp=now_ts, amount="0.005")
        signed = Account.sign_message(encode_typed_data(full_message=eip712_data), private_key=agent_wallet.key)
        sig_hex = signed.signature.hex() if signed.signature.hex().startswith("0x") else "0x" + signed.signature.hex()

        auth_header = json.dumps({
            "payer_address": agent_wallet.address,
            "signature": sig_hex,
            "nonce": nonce,
            "timestamp": now_ts,
            "amount_usdc": "0.005",
            "type": "eip712"
        })

        # First call -> 200 OK
        res1 = await client.post(
            "/v1/terrain/analyze",
            json={"latitude": 0.0, "longitude": 0.0},
            headers={"X-402-Signature": auth_header}
        )
        assert res1.status_code == 200

        # Second call with identical consumed nonce -> Must be 402 rejected
        res2 = await client.post(
            "/v1/terrain/analyze",
            json={"latitude": 0.0, "longitude": 0.0},
            headers={"X-402-Signature": auth_header}
        )
        assert res2.status_code == 402
        assert "already been consumed" in res2.json().get("rejection_reason", "")


@pytest.mark.asyncio
async def test_personal_sign_fallback(agent_wallet):
    """Verifies EIP-191 personal_sign fallback authentication."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        c_res = await client.get("/v1/terrain/challenge")
        challenge = c_res.json()
        nonce = challenge["nonce"]

        now_ts = int(time.time())
        plain_msg = X402Verifier.format_plain_message(nonce=nonce, timestamp=now_ts, amount="0.005")
        signed = Account.sign_message(encode_defunct(text=plain_msg), private_key=agent_wallet.key)
        sig_hex = signed.signature.hex() if signed.signature.hex().startswith("0x") else "0x" + signed.signature.hex()

        auth_header = json.dumps({
            "payer_address": agent_wallet.address,
            "signature": sig_hex,
            "nonce": nonce,
            "timestamp": now_ts,
            "amount_usdc": "0.005",
            "type": "personal_sign"
        })

        res = await client.post(
            "/v1/terrain/analyze",
            json={"latitude": 28.5983, "longitude": 83.9310},
            headers={"X-402-Signature": auth_header}
        )
        assert res.status_code == 200
        assert res.json()["settlement_network"] == "Polygon (Chain ID 137)"


@pytest.mark.asyncio
async def test_invalid_signature_rejection(agent_wallet):
    """Verifies that forged or mismatched signatures are rejected with HTTP 402."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        c_res = await client.get("/v1/terrain/challenge")
        nonce = c_res.json()["nonce"]

        # Deliberately forged signature
        forged_auth_header = json.dumps({
            "payer_address": agent_wallet.address,
            "signature": "0x" + "00" * 65,
            "nonce": nonce,
            "timestamp": int(time.time()),
            "amount_usdc": "0.005",
            "type": "eip712"
        })

        res = await client.post(
            "/v1/terrain/analyze",
            json={"latitude": 10.0, "longitude": 20.0},
            headers={"X-402-Signature": forged_auth_header}
        )
        assert res.status_code == 402
        assert "X-402-Rejection-Reason" in res.headers


@pytest.mark.asyncio
async def test_geodetic_bounds_and_physics_extremes(agent_wallet):
    """Verifies physical computations across extreme global coordinates."""
    from app.oracles.terrain.engine import TerrainEngine
    from app.oracles.terrain.schemas import GeoCoordinateInput

    # 1. North Pole
    np_res = TerrainEngine.analyze(GeoCoordinateInput(latitude=89.9, longitude=0.0))
    assert np_res.elevation_meters is not None
    assert 0.0 <= np_res.slope_gradient_degrees <= 90.0
    assert 0.0 <= np_res.solar_exposure_index <= 1.0

    # 2. Equator
    eq_res = TerrainEngine.analyze(GeoCoordinateInput(latitude=0.0, longitude=0.0))
    assert eq_res.elevation_meters is not None
    assert eq_res.trafficability.overall_status in ["GO", "CAUTION", "HAZARDOUS", "IMPASSABLE"]

    # 3. Southern High Latitude
    sh_res = TerrainEngine.analyze(GeoCoordinateInput(latitude=-75.0, longitude=120.0))
    assert sh_res.deterministic_proof_hash.startswith("0x")

