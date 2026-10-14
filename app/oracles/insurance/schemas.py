"""
Pydantic Schemas for Physical AI Risk Underwriting & Parametric Insurance Oracle.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class InsuranceUnderwriteInput(BaseModel):
    origin_latitude: float = Field(..., ge=-90.0, le=90.0, description="Mission Origin WGS84 Latitude")
    origin_longitude: float = Field(..., ge=-180.0, le=180.0, description="Mission Origin WGS84 Longitude")
    destination_latitude: float = Field(..., ge=-90.0, le=90.0, description="Mission Destination WGS84 Latitude")
    destination_longitude: float = Field(..., ge=-180.0, le=180.0, description="Mission Destination WGS84 Longitude")
    cruise_altitude_agl_meters: Optional[float] = Field(default=60.0, ge=5.0, le=2000.0, description="Cruising altitude AGL in meters")
    vehicle_type: Optional[str] = Field(default="QUADCOPTER_VTOL", description="Vehicle type: QUADCOPTER_VTOL, FIXED_WING_DRONE, WHEELED_ROVER, or QUADRUPED_ROBOT")
    vehicle_mass_kg: Optional[float] = Field(default=8.5, ge=0.5, le=1000.0, description="Vehicle mass in kg")
    vehicle_hull_value_usdc: Optional[float] = Field(default=3500.0, ge=50.0, description="Airframe / robot market replacement value in USDC")
    cargo_value_usdc: Optional[float] = Field(default=1500.0, ge=0.0, description="Payload / cargo value insured in USDC")
    operator_id: Optional[str] = Field(default="AeroLogistics-Autonomous-Fleet", description="Operator / fleet corporate ID")


class RiskComponentBreakdown(BaseModel):
    terrain_tipping_hazard_score: float = Field(..., ge=0.0, le=1.0, description="Terrain gradient and roughness hazard (0.0=safe, 1.0=impassable)")
    weather_turbulence_risk_score: float = Field(..., ge=0.0, le=1.0, description="Wind gust, wind shear, and icing hazard (0.0=calm, 1.0=severe)")
    airspace_regulatory_penalty_score: float = Field(..., ge=0.0, le=1.0, description="Proximity to NFZ, controlled airspace, and altitude violation risk")
    comms_loss_link_risk_score: float = Field(..., ge=0.0, le=1.0, description="5G shadow fading and satellite blackout probability")
    energy_depletion_risk_score: float = Field(..., ge=0.0, le=1.0, description="Battery depletion probability before reaching destination")
    composite_mission_risk_score: float = Field(..., ge=0.0, le=1.0, description="Actuarial weighted composite risk index (0.0 to 1.0)")


class ParametricTriggerRule(BaseModel):
    trigger_condition: str = Field(..., description="Automated payout trigger clause")
    threshold_value: str = Field(..., description="Quantitative trigger boundary")
    payout_percentage: float = Field(..., description="Percentage of policy limit disbursed on trigger")


class InsurancePolicyCertificate(BaseModel):
    policy_id: str = Field(..., description="Unique cryptographic policy serial number (POL_x402_...)")
    operator_id: str
    underwriting_status: str = Field(..., description="APPROVED_INSURED, CONDITIONAL_CAUTION, or REJECTED_HIGH_RISK")
    total_coverage_limit_usdc: float = Field(..., description="Maximum payout liability in USDC (Hull + Cargo)")
    actuarial_dynamic_premium_usdc: float = Field(..., description="Real-time dynamic insurance premium in USDC")
    proof_of_insurability_hash: str = Field(..., description="Tamper-proof SHA-256 flight clearance & insurance hash")
    valid_until_timestamp: int = Field(..., description="Expiry timestamp of insurance coverage")
    parametric_triggers: List[ParametricTriggerRule] = Field(..., description="Pre-agreed smart contract automated payout triggers")


class InsuranceUnderwriteOutput(BaseModel):
    oracle_type: str = Field(default="INSURANCE_UNDERWRITING_AND_CLEARANCE", description="Oracle capability type")
    policy: InsurancePolicyCertificate
    risk_breakdown: RiskComponentBreakdown
    flight_clearance: str = Field(..., description="CLEARED_FOR_TAKEOFF, MANUAL_PILOT_OVERRIDE_REQUIRED, or FLIGHT_GROUNDED")
    clearance_advisory: str = Field(..., description="Legal and operational flight advisory notice")
    deterministic_proof_hash: str
    settlement_network: str
    fee_paid_usdc: float


class ClaimVerificationInput(BaseModel):
    policy_id: str = Field(..., description="Policy ID issued during underwriting")
    proof_of_insurability_hash: str = Field(..., description="Original Proof of Insurability Hash")
    incident_timestamp: int = Field(..., description="Epoch timestamp of incident / crash")
    incident_latitude: float = Field(..., ge=-90.0, le=90.0, description="Crash location Latitude")
    incident_longitude: float = Field(..., ge=-180.0, le=180.0, description="Crash location Longitude")
    blackbox_wind_gust_recorded_mps: float = Field(..., description="Onboard anemometer peak gust speed at crash (m/s)")
    blackbox_c2_link_loss_seconds: float = Field(..., description="Duration of total control link blackout prior to incident (seconds)")
    blackbox_path_deviation_meters: float = Field(..., description="Distance deviation from approved oracle waypoint trajectory in meters")
    actual_damage_loss_usdc: float = Field(..., ge=0.0, description="Claimed total monetary loss in USDC")


class ClaimAdjudicationOutput(BaseModel):
    oracle_type: str = Field(default="PARAMETRIC_CLAIM_ADJUDICATION", description="Oracle capability type")
    claim_id: str = Field(..., description="Unique claim adjudication serial")
    policy_id: str
    adjudication_verdict: str = Field(..., description="APPROVED_PAYOUT, PARTIAL_PAYOUT, REJECTED_PILOT_BREACH, or INVESTIGATION_REQUIRED")
    adjudicated_payout_amount_usdc: float = Field(..., description="Final approved payout sum in USDC")
    primary_fault_attribution: str = Field(..., description="Cause: FORCE_MAJEURE_SEVERE_WEATHER, C2_TELEMETRY_BLACKOUT, UNPREDICTED_OBSTACLE, or OPERATOR_WAYPOINT_BREACH")
    payout_smart_contract_authorization: str = Field(..., description="EIP-712 payload authorizing onchain vault disbursement")
    deterministic_proof_hash: str
    settlement_network: str
    fee_paid_usdc: float
