"""
Interactive Real-Time Autonomous Mission Simulation across 5 Physical AI Oracles.
Demonstrates a commercial delivery drone paying for all 5 oracles via x402 on Polygon:
1. Geo-Terrain (0.005 USDC)
2. Micro-Weather & Turbulence (0.005 USDC)
3. Airspace & Regulatory Geofence (0.005 USDC)
4. RF Line-of-Sight & SatCom Mesh (0.005 USDC)
5. Kinematic & Energy-Optimal 3D Routing (0.010 USDC)
"""

import sys
import time
import json
import httpx
from eth_account import Account
from eth_account.messages import encode_typed_data
from fastapi.testclient import TestClient
from app.main import app
from app.core.x402_verifier import X402Verifier

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def banner(title: str):
    print("\n" + "=" * 75)
    print(f" 🛰️  {title}")
    print("=" * 75)

def call_paid_oracle(client, endpoint: str, payload: dict, agent_wallet: Account, oracle_name: str):
    print(f"\n▶ [{oracle_name}] POST {endpoint}")
    
    # 1. Unpaid probe -> get 402 challenge
    r_unpaid = client.post(endpoint, json=payload)
    if r_unpaid.status_code != 402:
        print(f"   Unexpected status: {r_unpaid.status_code}")
        return r_unpaid.json()
    
    challenge = r_unpaid.json()
    nonce = challenge["nonce"]
    price = challenge["price_usdc"]
    now_ts = int(time.time())

    print(f"   [HTTP 402 Challenge] Required: {price} USDC | Nonce: {nonce[:14]}... | Vault: {challenge['recipient_address'][:10]}...")

    # 2. Sign EIP-712 payment authorization
    eip712_structure = X402Verifier.build_eip712_structure(
        nonce=nonce,
        timestamp=now_ts,
        amount=price
    )

    signed = Account.sign_message(encode_typed_data(full_message=eip712_structure), private_key=agent_wallet.key)
    sig_hex = signed.signature.hex()
    if not sig_hex.startswith("0x"):
        sig_hex = "0x" + sig_hex

    auth_header = json.dumps({
        "payer_address": agent_wallet.address,
        "signature": sig_hex,
        "nonce": nonce,
        "timestamp": now_ts,
        "amount_usdc": price,
        "type": "eip712",
    })

    # 3. Paid Query
    t0 = time.perf_counter()
    r_paid = client.post(endpoint, json=payload, headers={"X-402-Signature": auth_header})
    elapsed_ms = (time.perf_counter() - t0) * 1000

    print(f"   [HTTP {r_paid.status_code} OK] {r_paid.headers.get('X-402-Settlement-Status')} ({elapsed_ms:.1f}ms) | Paid: {price} USDC")
    return r_paid.json()


def run_mission():
    agent_wallet = Account.create()
    banner(f"자율 AI 배달 드론(AeroDelivery-Bot-99) 임무 시작 및 지갑 생성")
    print(f"• 에이전트 지갑 주소: {agent_wallet.address}")
    print(f"• 임무 구간         : 출발지 [37.5665, 126.9780] -> 목적지 [37.5850, 127.0120]")
    print(f"• 비행체 제원       : 8.0kg 쿼드콥터 VTOL, 280Wh 배터리")

    total_spent_usdc = 0.0
    client = TestClient(app)

    try:
        # Oracle 1: Terrain
        banner("오라클 1. 지형 & 표면 착륙 물리 분석 (0.005 USDC)")
        terrain_res = call_paid_oracle(
            client,
            "/v1/terrain/analyze",
            {"latitude": 37.5665, "longitude": 126.9780, "sampling_radius_meters": 30.0},
            agent_wallet,
            "Terrain Oracle",
        )
        total_spent_usdc += 0.005
        print(f"  [지형 정보] 해발고도: {terrain_res['elevation_meters']}m | 경사도: {terrain_res['slope_gradient_degrees']}° | 착륙적합성: {terrain_res['trafficability']['drone_landing_score']} | 상태: {terrain_res['trafficability']['overall_status']}")

        # Oracle 2: Weather
        banner("오라클 2. 국지성 미기상 & 3D 바람/난기류 분석 (0.005 USDC)")
        weather_res = call_paid_oracle(
            client,
            "/v1/weather/analyze",
            {"latitude": 37.5665, "longitude": 126.9780, "altitude_agl_meters": 60.0, "heading_degrees": 45.0, "vehicle_mass_kg": 8.0},
            agent_wallet,
            "Weather Oracle",
        )
        total_spent_usdc += 0.005
        print(f"  [기상 정보] 수평풍속: {weather_res['wind_vector']['horizontal_speed_mps']}m/s | EDR 난기류: {weather_res['flight_stability']['eddy_dissipation_rate_edr']} | VTOL안정도: {weather_res['flight_stability']['vtol_stability_score']} ({weather_res['flight_stability']['flight_safety_category']})")

        # Oracle 3: Geofence
        banner("오라클 3. 공역 등급 및 비행금지구역(NFZ) 규제 검증 (0.005 USDC)")
        geofence_res = call_paid_oracle(
            client,
            "/v1/geofence/check",
            {"latitude": 37.5665, "longitude": 126.9780, "altitude_agl_meters": 60.0, "vehicle_category": "DRONE_COMMERCIAL"},
            agent_wallet,
            "Geofence Oracle",
        )
        total_spent_usdc += 0.005
        print(f"  [공역 규제] 공역등급: {geofence_res['airspace']['class_code']} | 비행제한구역: {geofence_res['no_fly_zone']['in_prohibited_zone']} ({geofence_res['no_fly_zone']['zone_type']}) | 규제준수: {geofence_res['regulation']['compliance_status']}")

        # Oracle 4: RF Coverage
        banner("오라클 4. RF 가시선 & 위성 통신(SatCom) 커버리지 (0.005 USDC)")
        rf_res = call_paid_oracle(
            client,
            "/v1/rf/coverage",
            {"latitude": 37.5665, "longitude": 126.9780, "altitude_agl_meters": 60.0},
            agent_wallet,
            "RF Coverage Oracle",
        )
        total_spent_usdc += 0.005
        print(f"  [통신 신뢰성] 5G RSRP: {rf_res['cellular']['rsrp_dbm']}dBm | 위성 가시각: {rf_res['satellite']['sky_view_clearance_angle_deg']}° | 권장 링크: {rf_res['link_margin']['failover_recommendation']}")

        # Oracle 5: 3D Energy Routing
        banner("오라클 5. 3D 에너지 최적 경로 & 배터리 수명 계획 (0.010 USDC)")
        routing_res = call_paid_oracle(
            client,
            "/v1/routing/energy-optimal",
            {
                "origin_latitude": 37.5665,
                "origin_longitude": 126.9780,
                "destination_latitude": 37.5850,
                "destination_longitude": 127.0120,
                "cruise_altitude_agl_meters": 60.0,
                "vehicle_mass_kg": 8.0,
                "battery_capacity_wh": 280.0,
                "initial_soc_pct": 100.0,
                "cruise_speed_mps": 12.0
            },
            agent_wallet,
            "Energy Routing Oracle",
        )
        total_spent_usdc += 0.010
        print(f"  [최적 3D 경로] 총 거리: {routing_res['performance']['total_distance_km']:.2f}km | 예상소비전력: {routing_res['energy_budget']['total_energy_consumed_wh']:.2f}Wh | 잔여배터리: {routing_res['energy_budget']['final_soc_pct']:.1f}%")

        banner("임무 완료 및 결제 수수료 요약")
        print(f"✔ 5개 오라클 모두 성공적으로 EIP-712 서명 승인 및 검증 완료!")
        print(f"✔ 총 에이전트 지출 수수료: {total_spent_usdc:.3f} USDC (Polygon 메인넷)")
        print(f"✔ 오라클 수취 금고 지갑 : 0xA185B43fDD19619f99952AAed6eabf1029bF36a1")

    finally:
        if hasattr(client, "close"):
            client.close()

if __name__ == "__main__":
    run_mission()
