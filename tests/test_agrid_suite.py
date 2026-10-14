"""
Comprehensive Test Suite for A.GRID Autonomous Logistics Escrow,
Proof of Insurability (PoI), Proof of Delivery (PoD), Machine Credit Scoring, and Telemetry.
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_agrid_discovery():
    """Validates A.GRID Semantic Manifest & Agent Card."""
    res1 = client.get("/.well-known/agrid.json")
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["agent_id"] == "did:agrid:polygon:geo-oracle-x402"
    assert data1["network"]["token_symbol"] == "USDC"
    assert "logistics_escrow" in data1["network"]["smart_contracts"]

    res2 = client.get("/v1/agrid/agent-card")
    assert res2.status_code == 200
    assert res2.json()["version"] == "3.0.0"


def test_agrid_poi_dispatch_approval():
    """Validates successful PoI risk underwriting in permitted corridor."""
    payload = {
        "mission_id": "0x1111222233334444555566667777888899990000aaaabbbbccccddddeeeeffff",
        "carrier_agent": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        "cargo_category": "StandardParcel",
        "origin_lat": 37.3850,
        "origin_lon": 126.6500,
        "dest_lat": 37.3980,
        "dest_lon": 126.6620,
        "planned_cruise_altitude_m": 60.0,
        "carrier_mass_kg": 12.0,
        "cargo_weight_kg": 1.5
    }
    res = client.post("/v1/agrid/escrow/dispatch-verify", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["approved_for_dispatch"] is True
    assert data["poi_signature"] is not None
    assert data["risk_score"] < 0.70


def test_agrid_poi_dispatch_prohibited_airspace_rejection():
    """Ensures robot cannot dispatch into Prohibited Airspace (P-73)."""
    payload = {
        "mission_id": "0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
        "carrier_agent": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        "cargo_category": "StandardParcel",
        "origin_lat": 37.5665,
        "origin_lon": 126.9780,
        "dest_lat": 37.5866,
        "dest_lon": 126.9748,
        "planned_cruise_altitude_m": 70.0
    }
    res = client.post("/v1/agrid/escrow/dispatch-verify", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["approved_for_dispatch"] is False
    assert "Prohibited" in data["rejection_reason"]


def test_agrid_pod_delivery_success():
    """Validates delivery within GPS radius (<25m) and within SLA."""
    payload = {
        "mission_id": "0x1111222233334444555566667777888899990000aaaabbbbccccddddeeeeffff",
        "carrier_agent": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        "current_lat": 37.39801,
        "current_lon": 126.66202,
        "target_dest_lat": 37.3980,
        "target_dest_lon": 126.6620,
        "max_recorded_g_force": 1.25,
        "max_allowed_g_force": 2.50
    }
    res = client.post("/v1/agrid/escrow/delivery-verify", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["delivery_verified"] is True
    assert data["distance_to_dest_m"] < 10.0
    assert data["pod_signature"] is not None
    assert data["status"] == "APPROVED_FOR_INSTANT_ESCROW_DISBURSEMENT"


def test_agrid_pod_delivery_rejections():
    """Tests spatial distance, G-force shock, and temperature breach rejections."""
    # 1. Distance too far (500m)
    p1 = {
        "mission_id": "0x1234",
        "carrier_agent": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        "current_lat": 37.4050,
        "current_lon": 126.6620,
        "target_dest_lat": 37.3980,
        "target_dest_lon": 126.6620,
        "max_recorded_g_force": 1.0
    }
    r1 = client.post("/v1/agrid/escrow/delivery-verify", json=p1).json()
    assert r1["delivery_verified"] is False
    assert any("away from destination" in reason for reason in r1["rejection_reasons"])

    # 2. G-force shock breach (4.5G > 2.0G limit)
    p2 = {
        "mission_id": "0x1234",
        "carrier_agent": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        "current_lat": 37.3980,
        "current_lon": 126.6620,
        "target_dest_lat": 37.3980,
        "target_dest_lon": 126.6620,
        "max_recorded_g_force": 4.5,
        "max_allowed_g_force": 2.0
    }
    r2 = client.post("/v1/agrid/escrow/delivery-verify", json=p2).json()
    assert r2["delivery_verified"] is False
    assert any("excessive impact shock" in reason for reason in r2["rejection_reasons"])

    # 3. Cold chain temperature breach (12.0C > 8.0C max limit)
    p3 = {
        "mission_id": "0x1234",
        "carrier_agent": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        "current_lat": 37.3980,
        "current_lon": 126.6620,
        "target_dest_lat": 37.3980,
        "target_dest_lon": 126.6620,
        "max_recorded_g_force": 1.0,
        "max_recorded_temp_celsius": 12.0,
        "required_max_temp": 8.0
    }
    r3 = client.post("/v1/agrid/escrow/delivery-verify", json=p3).json()
    assert r3["delivery_verified"] is False
    assert any("Temperature exceeded" in reason for reason in r3["rejection_reasons"])


def test_agrid_machine_credit_scoring():
    """Validates deterministic machine credit score calculation."""
    # Pristine seasoned drone
    p_prime = {
        "agent_address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        "owner_address": "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC",
        "total_missions_completed": 250,
        "total_missions_failed": 0,
        "total_mileage_km": 2500.0,
        "total_revenue_earned_usdc": 3500.0,
        "accident_count": 0,
        "avg_stability_score": 0.98,
        "hardware_health_score": 0.99
    }
    r_prime = client.post("/v1/agrid/credit/evaluate", json=p_prime).json()
    assert r_prime["machine_credit_score"] >= 800
    assert "AAA" in r_prime["credit_tier"]
    assert r_prime["underwriting_recommendations"]["bond_issuance_eligible"] is True
    assert r_prime["underwriting_recommendations"]["max_unsecured_loan_usdc"] >= 25000.0

    # High risk drone with multiple accidents
    p_risk = {
        "agent_address": "0x9999",
        "owner_address": "0x8888",
        "total_missions_completed": 10,
        "total_missions_failed": 15,
        "accident_count": 4,
        "avg_stability_score": 0.35,
        "hardware_health_score": 0.40
    }
    r_risk = client.post("/v1/agrid/credit/evaluate", json=p_risk).json()
    assert r_risk["machine_credit_score"] < 550
    assert r_risk["underwriting_recommendations"]["bond_issuance_eligible"] is False
