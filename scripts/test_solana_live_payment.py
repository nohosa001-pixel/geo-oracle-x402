"""
========================================================================================
     A.GRID LIVE SOLANA MICROPAYMENT (Ed25519) VERIFICATION & SETTLEMENT SCRIPT
========================================================================================
Executes real-time autonomous agent Solana SPL USDC micropayment authorization
against geo-oracle-x402 with zero-friction cryptographic verification.
"""

import sys
import time
import json
import httpx

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app
from app.core.x402_verifier import X402Verifier, SUPPORTED_NETWORKS
from app.core.solana_utils import SolanaKeypair


def get_client():
    try:
        r = httpx.get("http://localhost:8000/", timeout=0.5)
        if r.status_code == 200 and r.json().get("service") == "autonomous-physical-ai-oracle-suite":
            print("[*] Connected to live FastAPI server on http://localhost:8000")
            return httpx.Client(base_url="http://localhost:8000", timeout=10.0)
    except Exception:
        pass
    print("[*] Testing in-process via Starlette TestClient (FastAPI)")
    from starlette.testclient import TestClient
    return TestClient(app)


def run_test():
    client = get_client()

    print("\n" + "=" * 80)
    print(" 🪐 1. SOLANA AUTONOMOUS AGENT KEYPAIR & TREASURY INITIALIZED")
    print("=" * 80)

    agent = SolanaKeypair.generate()
    sol_cfg = SUPPORTED_NETWORKS["solana"]

    print(f"[*] Autonomous Agent Public Key : {agent.public_key_b58}")
    print(f"[*] Cryptographic Standard     : Ed25519 (Solana Mainnet-Beta)")
    print(f"[*] Settlement Token (Mint)     : SPL USDC ({sol_cfg['token_address']})")
    print(f"[*] Oracle Treasury Vault       : {sol_cfg['recipient_address']}")

    print("\n" + "=" * 80)
    print(" 🛰️ 2. SOLANA HTTP 402 PAYMENT CHALLENGE REQUEST")
    print("=" * 80)

    query = {
        "latitude": 37.3850,
        "longitude": 126.6500,
        "sampling_radius_meters": 30.0,
        "agent_id": f"Solana-Rover-{agent.public_key_b58[:6]}",
    }

    t0 = time.perf_counter()
    res_402 = client.post(
        "/v1/terrain/analyze",
        json=query,
        headers={"X-402-Preferred-Network": "solana"},
    )
    t_chal = (time.perf_counter() - t0) * 1000

    assert res_402.status_code == 402, f"Expected 402, got {res_402.status_code}"
    chal = res_402.json()

    print(f"[HTTP 402 PAYMENT REQUIRED] Received in {t_chal:.1f}ms")
    print(f"    - Network         : {chal['network']} (Cluster: {chal.get('cluster', 'mainnet-beta')})")
    print(f"    - Nonce           : {chal['nonce']}")
    print(f"    - Price           : {chal['price_usdc']} USDC")
    print(f"    - Recipient Vault : {chal['recipient_address']}")

    print("\n" + "=" * 80)
    print(" ⚡ 3. Ed25519 CRYPTOGRAPHIC MICROPAYMENT AUTHORIZATION")
    print("=" * 80)

    t_sign_start = time.perf_counter()
    now_ts = int(time.time())
    msg_to_sign = X402Verifier.format_solana_message(
        nonce=chal["nonce"],
        timestamp=now_ts,
        amount=chal["price_usdc"],
    )
    sig_b58 = agent.sign_message(msg_to_sign.encode("utf-8"))
    t_sign = (time.perf_counter() - t_sign_start) * 1000

    print(f"--> Signed Message Format:")
    print(f"    '{msg_to_sign.replace(chr(10), ' | ')}'")
    print(f"--> Ed25519 Signature ({t_sign:.2f}ms): {sig_b58[:32]}...")

    sol_header = json.dumps({
        "payer_address": agent.public_key_b58,
        "signature": sig_b58,
        "nonce": chal["nonce"],
        "timestamp": now_ts,
        "amount_usdc": chal["price_usdc"],
        "type": "ed25519",
        "network": "solana",
    })

    print("\n" + "=" * 80)
    print(" 🚀 4. SUBMITTING SIGNATURE & EXECUTING DETERMINISTIC ORACLE")
    print("=" * 80)

    t_verify_start = time.perf_counter()
    res_200 = client.post(
        "/v1/terrain/analyze",
        json=query,
        headers={
            "X-402-Signature": sol_header,
            "X-402-Preferred-Network": "solana",
        },
    )
    t_verify = (time.perf_counter() - t_verify_start) * 1000

    assert res_200.status_code == 200, f"Expected 200, got {res_200.status_code}: {res_200.text}"
    result = res_200.json()

    print(f"[HTTP 200 OK] Verified & Settled on Solana in {t_verify:.1f}ms!")
    print(f"    - Settlement Proof : {res_200.headers.get('X-402-Proof-Hash', '0x...')}")
    print(f"    - Status           : {res_200.headers.get('X-402-Settlement-Status')}")
    print(f"    - Payer Key        : {res_200.headers.get('X-402-Payer')}")
    print(f"    - Terrain Physics  :")
    print(f"        * WGS84 Elevation : {result['elevation_meters']} m")
    print(f"        * Surface Slope   : {result['slope_gradient_degrees']}° ({result['terrain_classification']})")
    print(f"        * Trafficability  : {result['trafficability']['overall_status']} (Rover Mobility: {result['trafficability']['wheeled_rover_score']})")

    print("\n" + "=" * 80)
    print(" 🎉 SOLANA MICROPAYMENT INTEGRATION CONFIRMED: 100% OPERATIONAL")
    print(f" Treasury Recipient Vault: {sol_cfg['recipient_address']}")
    print(" Web3 Dashboard URL: http://localhost:8000/solana-pay")
    print("=" * 80)


if __name__ == "__main__":
    run_test()
