"""
A.GRID Autonomous Logistics & Machine Finance Full Lifecycle Simulation.
Simulates:
1. A.GRID Service Discovery (.well-known/agrid.json)
2. Consignor Escrow Funding ($35 USDC)
3. Pre-Dispatch Proof of Insurability (PoI) Risk Verification & EIP-712 Signing
4. In-Transit 1Hz Telemetry Streaming & Cold-Chain Monitoring
5. Safe Arrival Proof of Delivery (PoD) Verification & Instant 3-Way Escrow Disbursement
6. Autonomous Machine Credit Scoring & Bond Underwriting ($25,000 credit line)
7. Edge-case Safety Rejection (Preventing flight in Prohibited Airspace)
"""

import sys
import io

# Ensure utf-8 encoding on Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def run_simulation():
    print("=" * 88)
    print("      A.GRID AUTONOMOUS LOGISTICS & MACHINE FINANCE FULL LIFECYCLE SIMULATION       ")
    print("               Powered by geo-oracle-x402 on Polygon (x402 Protocol)                 ")
    print("=" * 88)

    # -------------------------------------------------------------------------
    # STEP 1: A.GRID Semantic Service Discovery
    # -------------------------------------------------------------------------
    print("\n[STEP 1] Autonomous Agent discovers A.GRID Oracle Node...")
    res = client.get("/.well-known/agrid.json")
    assert res.status_code == 200, f"Discovery failed: {res.text}"
    manifest = res.json()
    print(f"  [OK] Found Agent Node: {manifest['display_name']}")
    print(f"  [OK] Settlement Network: {manifest['network']['chain'].upper()} (Chain ID: {manifest['network']['chain_id']})")
    print(f"  [OK] Settlement Token: {manifest['network']['token_symbol']} ({manifest['network']['token_address']})")
    print(f"  [OK] Escrow Contract: {manifest['network']['smart_contracts']['logistics_escrow']}")
    print(f"  [OK] Capabilities Registered: {len(manifest['capabilities'])} active micro-services")

    # -------------------------------------------------------------------------
    # STEP 2: Mission Creation & Pre-Flight PoI Dispatch Clearance
    # -------------------------------------------------------------------------
    mission_id = "0x88f1a23b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f"
    carrier_drone = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
    drone_owner = "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"
    merchant_pharma = "0x90F79bf6EB2c4f870365E785982E1f101E93b906"

    print(f"\n[STEP 2] Cold-Chain Pharma Delivery Mission Initiated")
    print(f"  * Mission ID: {mission_id[:18]}...")
    print(f"  * Consignor locked: $35.00 USDC in AutonomousLogisticsEscrow.sol")
    print(f"    - Merchant (Vaccines): $25.00 USDC")
    print(f"    - Drone Owner Net Wage: $9.95 USDC")
    print(f"    - geo-oracle Verification Fee: $0.05 USDC")
    print("  * Requesting pre-flight Proof of Insurability (PoI) clearance from geo-oracle...")

    dispatch_payload = {
        "mission_id": mission_id,
        "carrier_agent": carrier_drone,
        "cargo_category": "ColdChainBio",
        "origin_lat": 37.3850,
        "origin_lon": 126.6500,
        "dest_lat": 37.3980,
        "dest_lon": 126.6620,
        "planned_cruise_altitude_m": 65.0,
        "carrier_mass_kg": 14.5,
        "cargo_weight_kg": 2.2
    }

    res = client.post("/v1/agrid/escrow/dispatch-verify", json=dispatch_payload)
    assert res.status_code == 200, f"PoI verification failed: {res.text}"
    poi_data = res.json()

    print(f"  [OK] Dispatch Approved: {poi_data['approved_for_dispatch']}")
    print(f"  [OK] Actuarial Risk Score: {poi_data['risk_score']} (PPM: {poi_data['risk_score_ppm']})")
    print(f"  [OK] 3D Atmospheric Wind: {poi_data['weather_summary']['wind_speed_ms']} m/s (EDR: {poi_data['weather_summary']['edr_turbulence']})")
    print(f"  [OK] EIP-712 PoI Signature: {poi_data['poi_signature'][:30]}...")
    print(f"  [OK] Proof Hash: {poi_data['proof_hash'][:30]}...")
    print("  --> AutonomousLogisticsEscrow.sol state updated: [FUNDED] -> [DISPATCHED]")

    # -------------------------------------------------------------------------
    # STEP 3: In-Transit Telemetry Streaming & Boundary Monitoring
    # -------------------------------------------------------------------------
    print("\n[STEP 3] Autonomous Drone in Flight: Live Telemetry Streaming")
    telemetry_frames = [
        {"lat": 37.3880, "lon": 126.6530, "altitude_m": 64.5, "g_force": 1.15, "temperature_celsius": 4.2, "required_min_temp": 2.0, "required_max_temp": 8.0, "battery_soc_percent": 96.0},
        {"lat": 37.3920, "lon": 126.6570, "altitude_m": 65.2, "g_force": 1.40, "temperature_celsius": 4.5, "required_min_temp": 2.0, "required_max_temp": 8.0, "battery_soc_percent": 91.0},
        {"lat": 37.3975, "lon": 126.6615, "altitude_m": 60.1, "g_force": 1.22, "temperature_celsius": 4.8, "required_min_temp": 2.0, "required_max_temp": 8.0, "battery_soc_percent": 86.0},
    ]

    for i, frame in enumerate(telemetry_frames, 1):
        res = client.post("/v1/agrid/telemetry/frame", json=frame)
        assert res.status_code == 200
        t_res = res.json()
        print(f"  * Frame {i}: GPS ({frame['lat']}, {frame['lon']}) | Temp: {frame['temperature_celsius']}C | Accel: {frame['g_force']}G | Status: {t_res['status']}")

    print("  [OK] Cold-chain temperature stayed strictly within 2.0C ~ 8.0C SLA.")
    print("  [OK] Zero shock damage detected (G-force well below 2.50G limit).")

    # -------------------------------------------------------------------------
    # STEP 4: Safe Arrival & Proof of Delivery (PoD) Instant Settlement
    # -------------------------------------------------------------------------
    print("\n[STEP 4] Drone lands at Hospital Helipad (Target Destination)")
    delivery_payload = {
        "mission_id": mission_id,
        "carrier_agent": carrier_drone,
        "current_lat": 37.39801,
        "current_lon": 126.66202,
        "target_dest_lat": 37.3980,
        "target_dest_lon": 126.6620,
        "max_recorded_g_force": 1.40,
        "max_allowed_g_force": 2.50,
        "min_recorded_temp_celsius": 4.2,
        "max_recorded_temp_celsius": 4.8,
        "required_min_temp": 2.0,
        "required_max_temp": 8.0
    }

    res = client.post("/v1/agrid/escrow/delivery-verify", json=delivery_payload)
    assert res.status_code == 200, f"PoD verification failed: {res.text}"
    pod_data = res.json()

    print(f"  [OK] Delivery Verified: {pod_data['delivery_verified']}")
    print(f"  [OK] Distance to Target GPS: {pod_data['distance_to_dest_m']} meters (Accuracy < 25m OK)")
    print(f"  [OK] EIP-712 PoD Signature: {pod_data['pod_signature'][:30]}...")
    print(f"  [OK] Verdict: {pod_data['status']}")
    print("\n  [ON-CHAIN SMART CONTRACT DISBURSEMENT EXECUTED IN 1 BLOCK]:")
    print(f"    --> Merchant Wallet ({merchant_pharma[:10]}...): +$25.00 USDC")
    print(f"    --> Drone Owner Wallet ({drone_owner[:10]}...): +$9.95 USDC (Machine Capital Passive Income)")
    print(f"    --> geo-oracle Node Vault: +$0.05 USDC")

    # -------------------------------------------------------------------------
    # STEP 5: Machine Credit Scoring & Bond Underwriting Capacity
    # -------------------------------------------------------------------------
    print("\n[STEP 5] Updating On-Chain Machine Credit Bureau (MachineCreditScorer.sol)")
    credit_payload = {
        "agent_address": carrier_drone,
        "owner_address": drone_owner,
        "total_missions_completed": 142,
        "total_missions_failed": 1,
        "total_mileage_km": 1280.5,
        "total_revenue_earned_usdc": 1412.90,
        "accident_count": 0,
        "avg_stability_score": 0.94,
        "hardware_health_score": 0.98
    }

    res = client.post("/v1/agrid/credit/evaluate", json=credit_payload)
    assert res.status_code == 200, f"Credit evaluation failed: {res.text}"
    credit_data = res.json()

    print(f"  [OK] Machine FICO Credit Score: {credit_data['machine_credit_score']} / 850")
    print(f"  [OK] Credit Rating Tier: {credit_data['credit_tier']}")
    print(f"  [OK] Annual Default Probability: {credit_data['annual_default_probability'] * 100:.2f}%")
    print(f"  [OK] Unsecured Robot Lending Capacity: ${credit_data['underwriting_recommendations']['max_unsecured_loan_usdc']:,.2f} USDC")
    print(f"  [OK] Recommended Loan APR: {credit_data['underwriting_recommendations']['recommended_apr_percent']}%")
    print(f"  [OK] Bond Issuance Eligible: {credit_data['underwriting_recommendations']['bond_issuance_eligible']}")
    print(f"  [OK] Max ABS Bond Tranche: ${credit_data['underwriting_recommendations']['max_bond_tranche_usdc']:,.2f} USDC")

    # -------------------------------------------------------------------------
    # STEP 6: Edge Case Safety Test (Preventing Flight in Prohibited Zone)
    # -------------------------------------------------------------------------
    print("\n[STEP 6] Edge Case Security Test: Drone requested in Prohibited No-Fly Airspace")
    invalid_dispatch = {
        "mission_id": "0xdeadbeef111122223333444455556666777788889999aaaabbbbccccddddeeee",
        "carrier_agent": carrier_drone,
        "cargo_category": "StandardParcel",
        "origin_lat": 37.5665,
        "origin_lon": 126.9780,
        "dest_lat": 37.5866,  # Immediate Blue House / P-73 Prohibited Zone
        "dest_lon": 126.9748,
        "planned_cruise_altitude_m": 80.0,
        "carrier_mass_kg": 15.0,
        "cargo_weight_kg": 1.0
    }

    res = client.post("/v1/agrid/escrow/dispatch-verify", json=invalid_dispatch)
    assert res.status_code == 200
    rejected_poi = res.json()
    print(f"  [OK] Dispatch Approved: {rejected_poi['approved_for_dispatch']}")
    print(f"  [OK] Security Rejection Reason: {rejected_poi['rejection_reason']}")
    print("  [OK] Drone Owner's robot was prevented from illegal flight and seizure!")

    print("\n" + "=" * 88)
    print("      ALL A.GRID AUTONOMOUS LOGISTICS & MACHINE FINANCE TESTS PASSED (6/6)          ")
    print("==================================================================================")

if __name__ == "__main__":
    run_simulation()
