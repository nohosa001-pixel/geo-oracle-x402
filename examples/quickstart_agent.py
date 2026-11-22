"""
Quickstart AI Agent Client for A.GRID Earth Physical Infrastructure Risk Hub (geo-oracle-x402 v3.0.0).

Demonstrates the full 3-step onboarding flow:
  1. Free discovery: GET /v1/infrastructure/catalog
  2. Free risk preview: POST /v1/infrastructure/preview
  3. Paid x402 assessment: POST /v1/infrastructure/assess (HTTP 402 -> EIP-712 sign -> HTTP 200)

Usage:
  python examples/quickstart_agent.py --url http://localhost:8080
  python examples/quickstart_agent.py --url https://your-cloud-run-url.run.app
"""

from __future__ import annotations

import argparse
import json
import time
import httpx
from eth_account import Account
from eth_account.messages import encode_typed_data


def build_eip712_payment_header(signer: Account, challenge: dict) -> str:
    """Signs an x402 payment challenge using EIP-712 structured data."""
    now_ts = int(time.time())
    typed_data = {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "MicroOraclePayment": [
                {"name": "recipient", "type": "address"},
                {"name": "token", "type": "address"},
                {"name": "amount", "type": "string"},
                {"name": "nonce", "type": "string"},
                {"name": "timestamp", "type": "uint256"},
            ],
        },
        "primaryType": "MicroOraclePayment",
        "domain": {
            "name": "Global Autonomous Physical AI Oracle Suite",
            "version": "1",
            "chainId": int(challenge.get("chain_id") or 137),
            "verifyingContract": challenge["token_address"],
        },
        "message": {
            "recipient": challenge["recipient_address"],
            "token": challenge["token_address"],
            "amount": challenge["price_usdc"],
            "nonce": challenge["nonce"],
            "timestamp": now_ts,
        },
    }
    signed = Account.sign_message(encode_typed_data(full_message=typed_data), private_key=signer.key)
    return json.dumps({
        "payer_address": signer.address,
        "signature": "0x" + signed.signature.hex(),
        "nonce": challenge["nonce"],
        "timestamp": now_ts,
        "amount_usdc": challenge["price_usdc"],
        "network": challenge.get("network", "polygon"),
        "type": "eip712",
    })


def main() -> None:
    parser = argparse.ArgumentParser(description="geo-oracle-x402 Quickstart Agent")
    parser.add_argument("--url", default="http://localhost:8080", help="Base URL of geo-oracle-x402")
    args = parser.parse_args()
    base_url = args.url.rstrip("/")

    payload = {
        "asset_id": "DC-SEOUL-01",
        "asset_type": "DATA_CENTER",
        "latitude": 37.5665,
        "longitude": 126.9780,
        "commodity": "AI_COMPUTE",
        "use_live_feed": True,
    }

    with httpx.Client(timeout=15.0) as client:
        # 1. Free Catalog
        cat = client.get(f"{base_url}/v1/infrastructure/catalog").json()
        print(f"[1/3] Catalog OK — asset types: {cat['supported_asset_types']}")

        # 2. Free Preview
        prev = client.post(f"{base_url}/v1/infrastructure/preview", json=payload).json()
        s = prev["summary"]
        print(
            f"[2/3] Free Preview OK — score={s['combined_risk_score']}, "
            f"grade={s['risk_grade']}, confidence={s['assessment_confidence']}"
        )

        # 3. Paid x402 Assessment (HTTP 402 -> Sign -> HTTP 200)
        r_402 = client.post(f"{base_url}/v1/infrastructure/assess", json=payload)
        assert r_402.status_code == 402, f"Expected 402, got {r_402.status_code}"
        challenge = r_402.json()

        ephemeral_agent = Account.create()
        sig_header = build_eip712_payment_header(ephemeral_agent, challenge)
        r_200 = client.post(
            f"{base_url}/v1/infrastructure/assess",
            json=payload,
            headers={"X-402-Signature": sig_header},
        )
        r_200.raise_for_status()
        paid = r_200.json()
        print(
            f"[3/3] Verified x402 Assess OK — mode={paid['mode']}, "
            f"proof_hash={r_200.headers.get('X-402-Proof-Hash')}"
        )


if __name__ == "__main__":
    main()
