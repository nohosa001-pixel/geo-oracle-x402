"""
Security & Protocol Edge Case Test Suite for x402 on Polygon.
Tests replay protection, expired signatures, tampered payloads, and live feed trigger.
"""

import json
import time
import pytest
from httpx import AsyncClient, ASGITransport
from eth_account import Account
from eth_account.messages import encode_typed_data, encode_defunct

from app.main import app
from app.core.x402_verifier import (
    POLYGON_CHAIN_ID,
    USDC_POLYGON_ADDRESS,
    ORACLE_RECIPIENT_WALLET,
    X402Verifier,
)


@pytest.fixture
def test_agent():
    return Account.from_key("0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d")


@pytest.fixture
def attacker_wallet():
    return Account.create()


@pytest.mark.asyncio
async def test_replay_attack_prevention(test_agent):
    """Verifies that an already consumed nonce cannot be replayed for another request."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1: Probe to get challenge
        payload = {"latitude": 37.5665, "longitude": 126.9780}
        res_unpaid = await client.post("/v1/terrain/analyze", json=payload)
        assert res_unpaid.status_code == 402
        challenge = res_unpaid.json()
        nonce = challenge["nonce"]

        # Step 2: Sign valid EIP-712 payment
        now_ts = int(time.time())
        eip712_data = X402Verifier.build_eip712_structure(
            nonce=nonce,
            timestamp=now_ts,
            amount="0.005"
        )
        encoded_data = encode_typed_data(full_message=eip712_data)
        signed_message = Account.sign_message(encoded_data, private_key=test_agent.key)
        signature_hex = signed_message.signature.hex()
        if not signature_hex.startswith("0x"):
            signature_hex = "0x" + signature_hex

        auth_header = {
            "payer_address": test_agent.address,
            "signature": signature_hex,
            "nonce": nonce,
            "timestamp": now_ts,
            "amount_usdc": "0.005",
            "type": "eip712"
        }

        # First request succeeds
        res_paid = await client.post(
            "/v1/terrain/analyze",
            json=payload,
            headers={"X-402-Signature": json.dumps(auth_header)},
        )
        assert res_paid.status_code == 200

        # Replay attempt with same nonce MUST be rejected with HTTP 402
        res_replay = await client.post(
            "/v1/terrain/analyze",
            json=payload,
            headers={"X-402-Signature": json.dumps(auth_header)},
        )
        assert res_replay.status_code == 402
        assert res_replay.json()["nonce"] != nonce


@pytest.mark.asyncio
async def test_expired_deadline_rejected(test_agent):
    """Verifies that a payment signature with an expired timestamp is strictly rejected."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {"latitude": 37.5665, "longitude": 126.9780}
        res_unpaid = await client.post("/v1/weather/analyze", json=payload)
        challenge = res_unpaid.json()
        nonce = challenge["nonce"]

        # Sign with expired timestamp in the past (over 300 seconds ago)
        past_ts = int(time.time()) - 400
        eip712_data = X402Verifier.build_eip712_structure(
            nonce=nonce,
            timestamp=past_ts,
            amount="0.005"
        )
        encoded_data = encode_typed_data(full_message=eip712_data)
        signed_message = Account.sign_message(encoded_data, private_key=test_agent.key)
        signature_hex = signed_message.signature.hex()
        if not signature_hex.startswith("0x"):
            signature_hex = "0x" + signature_hex

        auth_header = {
            "payer_address": test_agent.address,
            "signature": signature_hex,
            "nonce": nonce,
            "timestamp": past_ts,
            "amount_usdc": "0.005",
            "type": "eip712"
        }

        res_expired = await client.post(
            "/v1/weather/analyze",
            json=payload,
            headers={"X-402-Signature": json.dumps(auth_header)},
        )
        assert res_expired.status_code == 402


@pytest.mark.asyncio
async def test_tampered_signature_rejected(test_agent, attacker_wallet):
    """Verifies that a signature forged by an attacker or tampered payload is rejected."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {"latitude": 37.5665, "longitude": 126.9780}
        res_unpaid = await client.post("/v1/geofence/check", json=payload)
        challenge = res_unpaid.json()
        nonce = challenge["nonce"]

        now_ts = int(time.time())
        # Signed by attacker wallet instead of claimed payer
        eip712_data = X402Verifier.build_eip712_structure(
            nonce=nonce,
            timestamp=now_ts,
            amount="0.005"
        )
        encoded_data = encode_typed_data(full_message=eip712_data)
        signed_message = Account.sign_message(encoded_data, private_key=attacker_wallet.key)
        signature_hex = signed_message.signature.hex()
        if not signature_hex.startswith("0x"):
            signature_hex = "0x" + signature_hex

        auth_header = {
            "payer_address": test_agent.address,  # Claims to be test_agent, but signed with attacker_wallet
            "signature": signature_hex,
            "nonce": nonce,
            "timestamp": now_ts,
            "amount_usdc": "0.005",
            "type": "eip712"
        }

        res = await client.post(
            "/v1/geofence/check",
            json=payload,
            headers={"X-402-Signature": json.dumps(auth_header)},
        )
        assert res.status_code == 402


@pytest.mark.asyncio
async def test_live_data_sync_trigger():
    """Verifies that the on-demand background sync endpoint updates registries accurately."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/v1/system/trigger-sync")
        assert res.status_code == 200
        data = res.json()
        assert "status" in data
        assert data["status"]["daemon_status"] == "ONLINE_ACTIVE"
        assert data["status"]["total_sync_cycles_completed"] >= 1
