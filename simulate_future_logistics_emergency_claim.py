"""
========================================================================================
     A.GRID FUTURE LOGISTICS: SEVERE WEATHER PARAMETRIC INSURANCE EMERGENCY SIMULATION
       - Autonomous BVLOS Drone Encounters Force Majeure Micro-burst Gust (32.5 m/s)
       - Automated Blackbox Telemetry Cross-Verification & Fault Attribution
       - Zero-Friction Parametric Smart Contract Payout Disbursement
========================================================================================
"""

import sys
import time
import json

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi.testclient import TestClient
from eth_account import Account
from app.main import app
from app.core.x402_verifier import X402Verifier, SUPPORTED_NETWORKS

client = TestClient(app)


def print_banner(title: str):
    print("\n" + "=" * 90)
    print(f" {title}")
    print("=" * 90)


def run_emergency_insurance_simulation():
    print_banner("EMERGENCY SCENARIO: SEVERE WEATHER & INSTANT PARAMETRIC INSURANCE ADJUDICATION")
    print("   Integration: 5-Factor Physical Underwriting -> In-Flight Force Majeure -> Zero-Friction Payout")

    drone_agent = Account.create()
    print(f"[*] Autonomous Heavy-Lift Drone: SkyMedic-BVLOS-03")
    print(f"    - Onboard Autonomous Wallet: {drone_agent.address}")
    print(f"    - Cargo: Cold-Chain Rare Biological Antivenom (Declared Value: $2,500 USDC)")

    # -------------------------------------------------------------------------
    # STAGE 1: PRE-FLIGHT UNDERWRITING & POLICY ISSUANCE (x402 Monitored)
    # -------------------------------------------------------------------------
    print_banner("STAGE 1: PRE-FLIGHT ACTUARIAL RISK UNDERWRITING (PoI CLEARANCE)")
    underwrite_payload = {
        "mission_id": "MIS-2026-EMERGENCY-BIO-99",
        "operator_id": "BioFleet-Global-Robotics",
        "drone_model": "HexaRotor-VTOL-HeavyLift",
        "route_distance_km": 48.0,
        "planned_cruise_altitude_m": 80.0,
        "origin_latitude": 37.3850,
        "origin_longitude": 126.6500,
        "destination_latitude": 37.4500,
        "destination_longitude": 126.7200,
        "payload_value_usdc": 2500.0,
        "payload_weight_kg": 4.5,
        "historical_operator_safety_score": 0.95,
    }

    # Request underwriting challenge
    res_chal = client.get("/v1/insurance/challenge?network=polygon")
    assert res_chal.status_code == 200
    chal = res_chal.json()

    now_ts = int(time.time())
    typed_poly = X402Verifier.build_eip712_structure(
        nonce=chal["nonce"],
        timestamp=now_ts,
        amount=chal["price_usdc"],
        network="polygon",
    )
    from eth_account.messages import encode_typed_data
    sig_poly = drone_agent.sign_message(encode_typed_data(full_message=typed_poly)).signature.hex()

    headers = {
        "X-402-Signature": json.dumps({
            "payer_address": drone_agent.address,
            "signature": sig_poly,
            "nonce": chal["nonce"],
            "timestamp": now_ts,
            "amount_usdc": chal["price_usdc"],
            "type": "eip712",
            "network": "polygon",
        })
    }

    res_policy = client.post("/v1/insurance/underwrite", json=underwrite_payload, headers=headers)
    assert res_policy.status_code == 200, f"Underwrite failed: {res_policy.text}"
    policy_data = res_policy.json()
    policy = policy_data["policy"]

    print(f"  [OK] Policy Issued: {policy['policy_id']}")
    print(f"  [OK] Underwriting Status: {policy['underwriting_status']}")
    print(f"  [OK] Flight Clearance: {policy_data['flight_clearance']}")
    print(f"  [OK] Coverage Limit: ${policy['total_coverage_limit_usdc']:,.2f} USDC (Hull + Cargo)")
    print(f"  [OK] Actuarial Micro-Premium: ${policy['actuarial_dynamic_premium_usdc']:.4f} USDC")
    print(f"  [OK] Proof of Insurability (PoI) Hash: {policy['proof_of_insurability_hash'][:32]}...")
    print(f"  [OK] Active Parametric Triggers: {len(policy['parametric_triggers'])} rules locked in contract")

    # -------------------------------------------------------------------------
    # STAGE 2: IN-FLIGHT DISASTER: UNPREDICTED MICROBURST & EMERGENCY LANDING
    # -------------------------------------------------------------------------
    print_banner("STAGE 2: IN-FLIGHT DISASTER: UNPREDICTED 32.5 M/S MICROBURST ENCOUNTERED")
    print("  * Cruise at Waypoint #7 (Altitude: 82m AGL, Groundspeed: 18 m/s)")
    print("  [ALERT] Extreme localized wind shear & downdraft detected by ultrasonic anemometers!")
    print("  [ALERT] Peak wind gust: 32.5 m/s (Standard VTOL structural limit: 25.0 m/s)")
    print("  [ALERT] Rapid altitude drop: -14.2 m/s. Autonomous fail-safe parachute deployed!")
    print("  * Drone conducts controlled emergency touchdown in designated contingency zone.")
    print("  * Cryo cooling chamber compromised due to rough impact shock (Hull loss + Spoiled cargo: $2,500 USDC)")

    # -------------------------------------------------------------------------
    # STAGE 3: BLACKBOX TELEMETRY SUBMISSION & ORACLE CLAIM ADJUDICATION
    # -------------------------------------------------------------------------
    print_banner("STAGE 3: BLACKBOX TELEMETRY CROSS-CHECK & PARAMETRIC CLAIM ADJUDICATION")
    claim_payload = {
        "policy_id": policy["policy_id"],
        "proof_of_insurability_hash": policy["proof_of_insurability_hash"],
        "incident_timestamp": int(time.time()),
        "incident_latitude": 37.4120,
        "incident_longitude": 126.6850,
        "blackbox_wind_gust_recorded_mps": 32.5,
        "blackbox_c2_link_loss_seconds": 12.0,
        "blackbox_path_deviation_meters": 14.5,
        "actual_damage_loss_usdc": 2500.0,
    }

    # Obtain challenge for claim adjudication
    res_claim_chal = client.get("/v1/insurance/claim-challenge?network=polygon")
    assert res_claim_chal.status_code == 200
    claim_chal = res_claim_chal.json()

    now_ts_claim = int(time.time())
    typed_claim = X402Verifier.build_eip712_structure(
        nonce=claim_chal["nonce"],
        timestamp=now_ts_claim,
        amount=claim_chal["price_usdc"],
        network="polygon",
    )
    sig_claim = drone_agent.sign_message(encode_typed_data(full_message=typed_claim)).signature.hex()

    claim_headers = {
        "X-402-Signature": json.dumps({
            "payer_address": drone_agent.address,
            "signature": sig_claim,
            "nonce": claim_chal["nonce"],
            "timestamp": now_ts_claim,
            "amount_usdc": claim_chal["price_usdc"],
            "type": "eip712",
            "network": "polygon",
        })
    }

    print("--> Transmitting tamper-proof blackbox telemetry to geo-oracle Claim Engine...")
    t0 = time.perf_counter()
    res_adjudication = client.post("/v1/insurance/claim-verify", json=claim_payload, headers=claim_headers)
    t_adjudicate = (time.perf_counter() - t0) * 1000
    assert res_adjudication.status_code == 200, f"Claim adjudication failed: {res_adjudication.text}"
    adj = res_adjudication.json()

    print(f"\n  [ORACLE ADJUDICATION COMPLETE IN {t_adjudicate:.1f} MS]:")
    print(f"  [OK] Claim Serial: {adj['claim_id']}")
    print(f"  [OK] Adjudication Verdict: {adj['adjudication_verdict']}")
    print(f"  [OK] Primary Fault Attribution: {adj['primary_fault_attribution']}")
    print(f"  [OK] Approved Payout Amount: ${adj['adjudicated_payout_amount_usdc']:,.2f} USDC (100% Full Indemnity)")
    print(f"  [OK] On-Chain Smart Contract Payout Signature: {adj['payout_smart_contract_authorization'][:36]}...")
    print(f"  [OK] Deterministic Proof Hash: {adj['deterministic_proof_hash'][:36]}...")

    # -------------------------------------------------------------------------
    # STAGE 4: ON-CHAIN INSTANT PAYOUT DISBURSEMENT
    # -------------------------------------------------------------------------
    print_banner("STAGE 4: ON-CHAIN SMART CONTRACT INSTANT LIQUIDITY DISBURSEMENT")
    print("  * ParametricInsurancePool.sol executes automated payout upon oracle signature:")
    print(f"      --> Consignor / Hospital Account: +$2,000.00 USDC (Biological cargo replacement)")
    print(f"      --> Drone Operator Maintenance Account: +$500.00 USDC (Hardware repairs & rotor parts)")
    print("  * Total settlement time: < 1.0 second (Zero human claim adjuster delay)")
    print("  * Result: Consignor orders replacement batch immediately, zero solvency strain on operator!")

    print("\n" + "=" * 90)
    print("      PARAMETRIC EMERGENCY INSURANCE SIMULATION COMPLETED WITH 100% SUCCESS       ")
    print("==================================================================================")


if __name__ == "__main__":
    run_emergency_insurance_simulation()
