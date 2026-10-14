"""
Interactive Real-Time Autonomous Agent Demo.
Simulates a physical AI agent paying 0.005 USDC via x402 on Polygon to unlock terrain physics.
"""

import sys
import time
import json
import httpx
from eth_account import Account
from eth_account.messages import encode_typed_data
from fastapi.testclient import TestClient
from app.main import app
from app.core.x402_verifier import X402Verifier, ORACLE_RECIPIENT_WALLET

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def print_banner(title: str):
    print("\n" + "=" * 70)
    print(f" 🤖 [AI Agent Demo] {title}")
    print("=" * 70)

def run_simulation():
    # 1. Spawn simulated Autonomous Field Agent with its own cryptographic keypair
    agent_wallet = Account.create()
    print_banner("1. 자율 AI 에이전트 가동 및 지갑 생성")
    print(f"• 에이전트 ID         : Rover-VTOL-Autonomous-Unit-01")
    print(f"• 에이전트 지갑 주소  : {agent_wallet.address}")
    print(f"• 목표 탐사 좌표      : 위도 45.8326°, 경도 6.8652° (알프스 몽블랑 고지대)")
    print(f"• 수신자 오라클 지갑  : {ORACLE_RECIPIENT_WALLET}")

    target_endpoint = "/v1/terrain/analyze"
    payload = {
        "latitude": 45.8326,
        "longitude": 6.8652,
        "sampling_radius_meters": 30.0,
        "agent_id": "Rover-VTOL-Autonomous-Unit-01"
    }

    # 2. Step 1: Unpaid Probe (최초 무료 요청 시도)
    print_banner("2. [1단계] 오라클에 지형 물리 데이터 요청 (미결제 상태)")
    print(f"📡 POST {target_endpoint}")
    print(f"   Payload: {json.dumps(payload)}")
    
    client = TestClient(app)
    try:
        res = client.post(target_endpoint, json=payload)
        print(f"\n📥 [오라클 응답 상태코드]: HTTP {res.status_code} Payment Required (결제 요구됨)")
        
        challenge = res.json()
        print("\n📜 [오라클이 발급한 402 결제 챌린지]:")
        print(json.dumps(challenge, indent=2, ensure_ascii=False))

        nonce = challenge["nonce"]
        price_usdc = challenge["price_usdc"]
        recipient = challenge["recipient_address"]
        now_ts = int(time.time())

        # 3. Step 2: Agent Cryptographic Signing (EIP-712 서명 생성)
        print_banner("3. [2단계] 에이전트가 개인키로 EIP-712 마이크로 결제 서명 생성")
        print(f"✍️  {price_usdc} USDC 결제 서명 중...")
        print(f"• Nonce Challenge   : {nonce}")
        print(f"• 수취인 (사용자님) : {recipient}")
        print(f"• 네트워크          : Polygon Mainnet (Chain ID 137)")

        eip712_structure = X402Verifier.build_eip712_structure(
            nonce=nonce,
            timestamp=now_ts,
            amount=price_usdc
        )
        # Sign typed data with private key
        encoded_data = encode_typed_data(full_message=eip712_structure)
        signed_message = Account.sign_message(encoded_data, private_key=agent_wallet.key)
        signature_hex = "0x" + signed_message.signature.hex()

        print(f"✅ 서명 생성 완료: {signature_hex[:20]}...{signature_hex[-20:]}")

        auth_header_payload = json.dumps({
            "payer_address": agent_wallet.address,
            "signature": signature_hex,
            "nonce": nonce,
            "timestamp": now_ts,
            "amount_usdc": price_usdc,
            "type": "eip712"
        })

        # 4. Step 3: Re-issue Request with Payment Authorization
        print_banner("4. [3단계] 결제 서명 헤더(X-402-Signature) 동봉 후 재요청")
        headers = {"X-402-Signature": auth_header_payload}
        
        start_time = time.perf_counter()
        paid_res = client.post(target_endpoint, json=payload, headers=headers)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        print(f"📥 [오라클 응답 상태코드]: HTTP {paid_res.status_code} OK (결제 검증 승인 완료, {elapsed_ms:.1f}ms)")
        print(f"• Settlement Header : {paid_res.headers.get('X-402-Settlement-Status')}")
        print(f"• Payer Header      : {paid_res.headers.get('X-402-Payer')}")
        print(f"• Proof Hash        : {paid_res.headers.get('X-402-Proof-Hash')}")

        # 5. Final Result Display
        print_banner("5. [최종 결과] 에이전트가 수신한 실시간 지형 물리 및 기동성 평가 데이터")
        result_data = paid_res.json()
        print(json.dumps(result_data, indent=2, ensure_ascii=False))
    finally:
        if hasattr(client, "close"):
            client.close()

if __name__ == "__main__":
    run_simulation()
