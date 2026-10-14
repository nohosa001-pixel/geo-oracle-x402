import pytest
import json
from app.agrid.logistics_oracle_mcp import LogisticsVerificationEngine, LOGISTICS_ORACLE_SIGNER

def test_dcsa_ebl_verification_valid():
    engine = LogisticsVerificationEngine()
    result = engine.verify_dcsa_ebl(
        bl_number="MEDU12345678",
        carrier_scac="MSCU",
        vessel_imo=9839438,
        container_id="MSKU1234567",
        origin_port="CNSHA",
        dest_port="KRPUS"
    )
    assert result["verified"] is True
    assert result["standard"] == "DCSA-eBL-v3.0"
    assert result["blDocumentHash"].startswith("0x")
    assert result["containerIdHash"].startswith("0x")
    assert result["vesselImo"] == 9839438
    assert result["route"]["pol"] == "CNSHA"
    assert result["route"]["pod"] == "KRPUS"

def test_dcsa_ebl_verification_invalid_container():
    engine = LogisticsVerificationEngine()
    # Invalid container (wrong format)
    result = engine.verify_dcsa_ebl(
        bl_number="MEDU12345678",
        carrier_scac="MSCU",
        vessel_imo=9839438,
        container_id="INVALID_ID",
        origin_port="CNSHA",
        dest_port="KRPUS"
    )
    assert result["verified"] is False

def test_issue_pod_attestation_success():
    engine = LogisticsVerificationEngine()
    deal_id = "0x" + "11" * 32
    bl_hash = "0x" + "22" * 32
    container_id = "MSKU9876543"
    logs = [
        {"temp_c": 15.0, "vibration_g": 0.2, "humidity": 50},
        {"temp_c": 17.5, "vibration_g": 0.3, "humidity": 52}
    ]
    attestation = engine.issue_pod_attestation(
        deal_id_hex=deal_id,
        bl_doc_hash=bl_hash,
        container_id=container_id,
        vessel_imo=9839438,
        dest_unlocode="KRPUS",
        sensor_logs=logs,
        max_allowed_temp_c=25.0
    )
    assert attestation["oracleSigner"] == LOGISTICS_ORACLE_SIGNER
    assert attestation["podStruct"]["conditionPassed"] is True
    assert attestation["escrowAction"] == "READY_FOR_INSTANT_RELEASE"
    assert attestation["eip712Signature"].startswith("0x")
    assert len(attestation["eip712Signature"]) == 132 # 65 bytes in hex + 0x

def test_issue_pod_attestation_sla_breach():
    engine = LogisticsVerificationEngine()
    deal_id = "0x" + "33" * 32
    bl_hash = "0x" + "44" * 32
    container_id = "MSKU9876543"
    # One temperature reading breaches threshold (32.0 > 25.0)
    logs = [
        {"temp_c": 22.0, "vibration_g": 0.2, "humidity": 50},
        {"temp_c": 32.0, "vibration_g": 0.8, "humidity": 70}
    ]
    attestation = engine.issue_pod_attestation(
        deal_id_hex=deal_id,
        bl_doc_hash=bl_hash,
        container_id=container_id,
        vessel_imo=9839438,
        dest_unlocode="KRPUS",
        sensor_logs=logs,
        max_allowed_temp_c=25.0
    )
    assert attestation["podStruct"]["conditionPassed"] is False
    assert attestation["escrowAction"] == "DISPUTE_TRIGGERED_BY_SLA_BREACH"

def test_merkle_root_determinism():
    logs = [
        {"ts": 100, "val": "A"},
        {"ts": 200, "val": "B"},
        {"ts": 300, "val": "C"}
    ]
    root1 = LogisticsVerificationEngine.compute_merkle_root(logs)
    root2 = LogisticsVerificationEngine.compute_merkle_root(logs)
    assert root1 == root2
    assert root1.startswith("0x")
    assert len(root1) == 66
