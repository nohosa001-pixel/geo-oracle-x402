"""
Test Suite for Future Logistics:
1. FAA Part 108 BVLOS Compliance Audit
2. EASA U-space & SORA 2.5 Airspace Audit
3. WHO PQS & FDA 21 CFR Cold-Chain Bio SLA Audit
4. Solana Anchor Escrow Ed25519 PoI & PoD Verification and Signing
"""

import pytest
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric import ed25519

from app.main import app
from app.core.solana_utils import SolanaKeypair, b58decode

client = TestClient(app)


def test_faa_part108_bvlos_audit_compliant():
    payload = {
        "carrier_agent_id": "Drone-Hexa-BVLOS-01",
        "flight_corridor_length_km": 42.5,
        "planned_altitude_agl_m": 85.0,
        "airspace_class": "G",
        "has_active_ads_b_in": True,
        "has_optical_daa": True,
        "has_radar_daa": True,
        "ground_population_density_per_sq_km": 45.0,
        "satellite_c2_link_active": True,
        "contingency_landing_sites_count": 4,
    }
    res = client.post("/v1/agrid/compliance/bvlos-audit", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["faa_part_108"]["compliant"] is True
    assert "PERMIT" in data["faa_part_108"]["authorization_tier"] or "CERTIFICATE" in data["faa_part_108"]["authorization_tier"]
    assert data["faa_part_108"]["audit_verdict"] == "AUTHORIZED_BVLOS"
    assert data["easa_sora_2_5"]["sail_level"] in ["SAIL_I", "SAIL_II", "SAIL_III"]
    assert data["overall_status"] == "APPROVED"


def test_faa_part108_bvlos_audit_non_compliant():
    # Deficient DAA, excessive altitude, and high population density
    payload = {
        "carrier_agent_id": "Drone-Amateur-02",
        "flight_corridor_length_km": 15.0,
        "planned_altitude_agl_m": 220.0,  # Exceeds 122m standard
        "airspace_class": "B",
        "has_active_ads_b_in": False,
        "has_optical_daa": False,
        "has_radar_daa": False,
        "ground_population_density_per_sq_km": 1500.0,
        "satellite_c2_link_active": False,
        "contingency_landing_sites_count": 0,
    }
    res = client.post("/v1/agrid/compliance/bvlos-audit", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["faa_part_108"]["compliant"] is False
    assert data["faa_part_108"]["audit_verdict"] == "BVLOS_REJECTED"
    assert data["overall_status"] == "REQUIRES_MITIGATION"


def test_who_coldchain_bio_audit_success():
    # Pfizer/BioNTech or Moderna style mRNA or standard 2-8C vaccine
    payload = {
        "consignment_id": "CONS-PHARMA-2026-X99",
        "pharma_category": "Refrigerated_2_8C",
        "monitored_temperatures_celsius": [3.5, 4.0, 4.2, 4.8, 5.1, 4.7, 4.0, 3.8],
        "elapsed_minutes": 35.0,
        "container_vacuum_insulation_ok": True,
        "sensor_calibration_valid": True,
    }
    res = client.post("/v1/agrid/compliance/coldchain-audit", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["sla_breached"] is False
    assert data["pharma_release_status"] == "VERIFIED_GOOD_TO_DISBURSE"
    assert "mean_kinetic_temperature_mkt_celsius" in data
    assert 3.0 <= data["mean_kinetic_temperature_mkt_celsius"] <= 6.0


def test_who_coldchain_bio_audit_breach():
    # Excessive excursion beyond thermal limits
    payload = {
        "consignment_id": "CONS-PHARMA-SPOILED",
        "pharma_category": "Refrigerated_2_8C",
        "monitored_temperatures_celsius": [4.0, 5.5, 9.5, 12.0, 14.2, 11.0],  # Breached 8C
        "elapsed_minutes": 45.0,
        "container_vacuum_insulation_ok": False,
        "sensor_calibration_valid": True,
    }
    res = client.post("/v1/agrid/compliance/coldchain-audit", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["sla_breached"] is True
    assert data["pharma_release_status"] == "REJECTED_DISCARD"


def test_solana_escrow_dispatch_and_delivery_verification():
    # Generate mock carrier Solana address
    carrier_solana = SolanaKeypair.generate()
    mission_id = "0x99aa11bb22cc33dd44ee55ff66aa77bb88cc99dd00112233445566778899aabb"

    # 1. Solana PoI Dispatch Verification
    dispatch_req = {
        "mission_id": mission_id,
        "carrier_agent_solana": carrier_solana.public_key_b58,
        "cargo_category": "ColdChainBio",
        "origin_lat": 37.3850,
        "origin_lon": 126.6500,
        "dest_lat": 37.3980,
        "dest_lon": 126.6620,
        "planned_cruise_altitude_m": 60.0,
        "carrier_mass_kg": 15.0,
        "cargo_weight_kg": 2.5,
    }
    res_poi = client.post("/v1/agrid/escrow/solana/dispatch-verify", json=dispatch_req)
    assert res_poi.status_code == 200
    poi = res_poi.json()
    assert poi["approved_for_dispatch"] is True
    assert poi["oracle_signature_b58"] is not None
    assert len(poi["oracle_signature_bytes"]) == 64
    assert poi["oracle_authority_pubkey"] is not None

    # Cryptographically verify the Ed25519 signature
    oracle_pub_bytes = b58decode(poi["oracle_authority_pubkey"])
    oracle_verifier = ed25519.Ed25519PublicKey.from_public_bytes(oracle_pub_bytes)
    sig_bytes = b58decode(poi["oracle_signature_b58"])
    mission_bytes = bytes.fromhex(mission_id[2:])
    risk_ppm = poi["risk_score_ppm"]
    valid_until = poi["valid_until"]

    expected_signed_msg = (
        b"POI:" +
        mission_bytes +
        risk_ppm.to_bytes(4, byteorder="little", signed=False) +
        valid_until.to_bytes(8, byteorder="little", signed=True)
    )
    # This must not raise InvalidSignature
    oracle_verifier.verify(sig_bytes, expected_signed_msg)

    # 2. Solana PoD Delivery Verification
    delivery_req = {
        "mission_id": mission_id,
        "carrier_agent_solana": carrier_solana.public_key_b58,
        "current_lat": 37.39801,
        "current_lon": 126.66202,
        "target_dest_lat": 37.3980,
        "target_dest_lon": 126.6620,
        "max_recorded_g_force": 1.25,
        "max_allowed_g_force": 2.50,
        "min_recorded_temp_celsius": 4.1,
        "max_recorded_temp_celsius": 4.7,
        "required_min_temp": 2.0,
        "required_max_temp": 8.0,
    }
    res_pod = client.post("/v1/agrid/escrow/solana/delivery-verify", json=delivery_req)
    assert res_pod.status_code == 200
    pod = res_pod.json()
    assert pod["delivery_verified"] is True
    assert pod["status"] == "APPROVED_FOR_SOLANA_ESCROW_DISBURSEMENT"
    assert len(pod["pod_signature_bytes"]) == 64

    # Cryptographically verify the PoD Ed25519 signature
    sig_pod_bytes = b58decode(pod["pod_signature_b58"])
    max_g_ppm = int(delivery_req["max_recorded_g_force"] * 1_000_000)
    dist_ppm = pod["distance_to_dest_ppm"]
    expected_pod_msg = (
        b"POD:" +
        mission_bytes +
        max_g_ppm.to_bytes(4, byteorder="little", signed=False) +
        dist_ppm.to_bytes(4, byteorder="little", signed=False) +
        b"\x00"
    )
    oracle_verifier.verify(sig_pod_bytes, expected_pod_msg)
