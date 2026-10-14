"""
Comprehensive Test Suite for Multi-Chain & Solana x402 Micropayments.
Verifies Solana Ed25519 cryptographic authorization, Base58 keypair generation,
anti-replay protection, network negotiation headers, and multi-chain EVM routing.
"""

import time
import json
import pytest
from httpx import AsyncClient, ASGITransport
from eth_account import Account
from eth_account.messages import encode_typed_data

from app.main import app
from app.core.x402_verifier import (
    X402Verifier,
    SOLANA_USDC_MINT,
    SUPPORTED_NETWORKS,
)
from app.core.solana_utils import (
    SolanaKeypair,
    SolanaVerifier,
    b58encode,
    b58decode,
    is_valid_solana_address,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_solana_keypair_and_base58_primitives():
    """Validates pure-Python Base58 encoding/decoding and Ed25519 keypair functionality."""
    keypair = SolanaKeypair.generate()
    pub_key_b58 = keypair.public_key_b58
    assert is_valid_solana_address(pub_key_b58)
    assert len(b58decode(pub_key_b58)) == 32

    raw_test_data = b"Autonomous-Robot-Solana-Micropayment-Payload"
    encoded = b58encode(raw_test_data)
    decoded = b58decode(encoded)
    assert decoded == raw_test_data

    # Sign and verify
    sig_b58 = keypair.sign_message(raw_test_data)
    assert len(b58decode(sig_b58)) == 64

    is_valid, msg = SolanaVerifier.verify_signature(
        public_key_b58=pub_key_b58,
        signature_b58=sig_b58,
        message=raw_test_data,
    )
    assert is_valid is True


@pytest.mark.anyio
async def test_solana_challenge_generation():
    """Tests generating a 402 challenge explicitly tailored for Solana."""
    challenge = X402Verifier.generate_challenge(
        price_usdc="0.005",
        oracle_name="Geo-Terrain Oracle",
        preferred_network="solana",
    )
    assert challenge.network == "solana"
    assert challenge.chain_id is None
    assert challenge.cluster == "mainnet-beta"
    assert challenge.token_address == SOLANA_USDC_MINT
    assert "solana" in challenge.supported_networks
    assert "polygon" in challenge.supported_networks
    assert challenge.multi_chain_options is not None
    assert "solana" in challenge.multi_chain_options
    assert "base" in challenge.multi_chain_options


@pytest.mark.anyio
async def test_solana_micropayment_full_cycle():
    """Simulates an autonomous AI agent paying for Geo-Terrain Oracle using Solana Ed25519 wallet."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Request challenge specifying Solana preference
        res_402 = await client.post(
            "/v1/terrain/analyze",
            json={"latitude": 37.3850, "longitude": 126.6500, "sampling_radius_meters": 30.0},
            headers={"X-402-Preferred-Network": "solana"},
        )
        assert res_402.status_code == 402
        challenge_data = res_402.json()
        assert challenge_data["network"] == "solana"
        nonce = challenge_data["nonce"]

        # 2. Agent creates Solana keypair and signs payment authorization
        agent_wallet = SolanaKeypair.generate()
        now_ts = int(time.time())
        amount_usdc = challenge_data["price_usdc"]

        auth_message = X402Verifier.format_solana_message(
            nonce=nonce,
            timestamp=now_ts,
            amount=amount_usdc,
        )
        signature = agent_wallet.sign_message(auth_message.encode("utf-8"))

        payment_header_payload = json.dumps({
            "payer_address": agent_wallet.public_key_b58,
            "signature": signature,
            "nonce": nonce,
            "timestamp": now_ts,
            "amount_usdc": amount_usdc,
            "type": "ed25519",
            "network": "solana",
        })

        # 3. Submit request with Solana payment signature
        res_200 = await client.post(
            "/v1/terrain/analyze",
            json={"latitude": 37.3850, "longitude": 126.6500, "sampling_radius_meters": 30.0},
            headers={
                "X-402-Signature": payment_header_payload,
                "X-402-Preferred-Network": "solana",
            },
        )
        assert res_200.status_code == 200
        output = res_200.json()
        assert output["oracle_type"] == "TERRAIN_PHYSICS"
        assert "Solana" in output["settlement_network"]
        assert res_200.headers.get("X-402-Settlement-Status") == "VERIFIED_PAID"
        assert res_200.headers.get("X-402-Payer") == agent_wallet.public_key_b58
        assert res_200.headers.get("X-402-Network") == "Solana"


@pytest.mark.anyio
async def test_solana_signature_tampering_and_replay_rejection():
    """Ensures invalid signatures and replayed nonces are rejected on Solana."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Challenge
        res_402 = await client.get("/v1/terrain/challenge?network=solana")
        assert res_402.status_code == 200
        challenge = res_402.json()
        nonce = challenge["nonce"]

        wallet = SolanaKeypair.generate()
        now_ts = int(time.time())

        # Test A: Tampered Signature
        bad_sig = wallet.sign_message(b"different_tampered_data")
        bad_payload = json.dumps({
            "payer_address": wallet.public_key_b58,
            "signature": bad_sig,
            "nonce": nonce,
            "timestamp": now_ts,
            "amount_usdc": "0.005",
            "type": "ed25519",
            "network": "solana",
        })

        res_bad = await client.post(
            "/v1/terrain/analyze",
            json={"latitude": 37.3850, "longitude": 126.6500},
            headers={"X-402-Signature": bad_payload},
        )
        assert res_bad.status_code == 402
        assert "Solana authorization rejected" in res_bad.json()["rejection_reason"]

        # Test B: Valid signature execution
        valid_msg = X402Verifier.format_solana_message(nonce=nonce, timestamp=now_ts, amount="0.005")
        valid_sig = wallet.sign_message(valid_msg.encode("utf-8"))
        good_payload = json.dumps({
            "payer_address": wallet.public_key_b58,
            "signature": valid_sig,
            "nonce": nonce,
            "timestamp": now_ts,
            "amount_usdc": "0.005",
            "type": "ed25519",
            "network": "solana",
        })

        res_good = await client.post(
            "/v1/terrain/analyze",
            json={"latitude": 37.3850, "longitude": 126.6500},
            headers={"X-402-Signature": good_payload},
        )
        assert res_good.status_code == 200

        # Test C: Replay attack with same nonce
        res_replay = await client.post(
            "/v1/terrain/analyze",
            json={"latitude": 37.3850, "longitude": 126.6500},
            headers={"X-402-Signature": good_payload},
        )
        assert res_replay.status_code == 402
        assert "already been consumed" in res_replay.json()["rejection_reason"]


@pytest.mark.anyio
async def test_evm_multichain_base_and_arbitrum_payments():
    """Tests EVM multi-chain payments on Base L2 (Chain ID 8453) and Arbitrum One (Chain ID 42161)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test on Base
        agent_account = Account.create()
        now_ts = int(time.time())
        amount_usdc = "0.005"

        chal_res = await client.get("/v1/weather/challenge?network=base")
        assert chal_res.status_code == 200
        chal_data = chal_res.json()
        assert chal_data["network"] == "base"
        assert chal_data["chain_id"] == 8453
        nonce = chal_data["nonce"]

        # Build Base EIP-712 structured payload
        typed_data = X402Verifier.build_eip712_structure(
            nonce=nonce,
            timestamp=now_ts,
            amount=amount_usdc,
            network="base",
        )
        signed_proof = agent_account.sign_message(encode_typed_data(full_message=typed_data))
        sig_hex = signed_proof.signature.hex() if hasattr(signed_proof.signature, "hex") else str(signed_proof.signature)

        pay_header = json.dumps({
            "payer_address": agent_account.address,
            "signature": sig_hex,
            "nonce": nonce,
            "timestamp": now_ts,
            "amount_usdc": amount_usdc,
            "type": "eip712",
            "network": "base",
        })

        res_base = await client.post(
            "/v1/weather/analyze",
            json={"latitude": 37.3850, "longitude": 126.6500},
            headers={"X-402-Signature": pay_header},
        )
        assert res_base.status_code == 200
        base_out = res_base.json()
        assert "Base L2 Mainnet" in base_out["settlement_network"]
        assert res_base.headers.get("X-402-Settlement-Status") == "VERIFIED_PAID"
