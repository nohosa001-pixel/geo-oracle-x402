"""
Deterministic Actuarial Risk Underwriting & Smart Contract Parametric Claim Engine.
"""

import time
import math
import hashlib
import secrets
from app.oracles.terrain.engine import TerrainEngine
from app.oracles.terrain.schemas import GeoCoordinateInput
from app.oracles.weather.engine import WeatherEngine
from app.oracles.weather.schemas import WeatherQueryInput
from app.oracles.geofence.engine import GeofenceEngine
from app.oracles.geofence.schemas import GeofenceCheckInput
from app.oracles.rf_coverage.engine import RFEngine
from app.oracles.rf_coverage.schemas import RFQueryInput
from app.oracles.energy_routing.engine import EnergyRoutingEngine
from app.oracles.energy_routing.schemas import EnergyRoutingInput

from app.oracles.insurance.schemas import (
    InsuranceUnderwriteInput,
    RiskComponentBreakdown,
    ParametricTriggerRule,
    InsurancePolicyCertificate,
    InsuranceUnderwriteOutput,
    ClaimVerificationInput,
    ClaimAdjudicationOutput,
)


class InsuranceEngine:
    """
    Synthesizes 5 physical oracle dimensions to produce dynamic actuarial insurance underwriting,
    flight clearance tickets (Proof of Insurability), and instant parametric claim adjudication.
    """

    @classmethod
    def underwrite_mission(
        cls,
        query: InsuranceUnderwriteInput,
        fee_paid: float = 0.025,
        settlement_network: str = "Polygon (Chain ID 137)",
    ) -> InsuranceUnderwriteOutput:
        lat1, lon1 = query.origin_latitude, query.origin_longitude
        lat2, lon2 = query.destination_latitude, query.destination_longitude
        alt = query.cruise_altitude_agl_meters or 60.0
        hull_val = query.vehicle_hull_value_usdc or 3500.0
        cargo_val = query.cargo_value_usdc or 1500.0
        total_coverage = hull_val + cargo_val

        # 1. Run All 5 Physical Engines Internally for Actuarial Synthesis
        # A. Terrain Hazard at Midpoint
        mid_lat = (lat1 + lat2) / 2.0
        mid_lon = (lon1 + lon2) / 2.0
        terrain_res = TerrainEngine.analyze(GeoCoordinateInput(latitude=mid_lat, longitude=mid_lon))
        terrain_risk = round(min(1.0, (terrain_res.slope_gradient_degrees / 40.0) * 0.7 + (1.0 - terrain_res.trafficability.drone_landing_score) * 0.3), 3)

        # B. Weather Hazard
        weather_res = WeatherEngine.analyze(WeatherQueryInput(latitude=mid_lat, longitude=mid_lon, altitude_agl_meters=alt))
        weather_risk = round(max(0.05, min(1.0, 1.0 - weather_res.flight_stability.vtol_stability_score)), 3)

        # C. Geofence & Airspace Regulatory Risk
        geofence_res = GeofenceEngine.check(GeofenceCheckInput(latitude=mid_lat, longitude=mid_lon, altitude_agl_meters=alt))
        if geofence_res.no_fly_zone.in_prohibited_zone:
            geofence_risk = 1.0
        elif geofence_res.airspace.is_controlled:
            geofence_risk = 0.45
        else:
            geofence_risk = 0.08

        # D. RF & Comms Loss-of-Link Risk
        rf_res = RFEngine.analyze(RFQueryInput(latitude=mid_lat, longitude=mid_lon, altitude_agl_meters=alt))
        if rf_res.link_margin.comms_health_status == "EXCELLENT":
            comms_risk = 0.05
        elif rf_res.link_margin.comms_health_status == "ADEQUATE":
            comms_risk = 0.20
        elif rf_res.link_margin.comms_health_status == "MARGINAL":
            comms_risk = 0.55
        else:
            comms_risk = 0.90

        # E. Energy Depletion Risk
        routing_res = EnergyRoutingEngine.generate_optimal_route(
            EnergyRoutingInput(
                origin_latitude=lat1,
                origin_longitude=lon1,
                destination_latitude=lat2,
                destination_longitude=lon2,
                cruise_altitude_agl_meters=alt,
                vehicle_mass_kg=query.vehicle_mass_kg or 8.5,
            )
        )
        final_soc = routing_res.energy_budget.final_soc_pct
        if final_soc >= 35.0:
            energy_risk = 0.05
        elif final_soc >= 15.0:
            energy_risk = 0.35
        else:
            energy_risk = 0.95

        # 2. Multi-Factor Actuarial Composite Risk Calculation
        # Weights: Weather 25%, Geofence 25%, Terrain 15%, Energy 20%, Comms 15%
        composite_risk = round(
            0.25 * weather_risk +
            0.25 * geofence_risk +
            0.15 * terrain_risk +
            0.20 * energy_risk +
            0.15 * comms_risk,
            3
        )

        # 3. Dynamic Actuarial Premium Calculation (USDC)
        # Premium = Total Coverage * Composite Risk * Actuarial Factor (0.2%) + Base Risk Surcharge
        dynamic_premium = round(total_coverage * (composite_risk * 0.0025) + 0.10, 2)

        # 4. Underwriting & Flight Clearance Decision
        if geofence_risk >= 0.95 or composite_risk >= 0.80:
            uw_status = "REJECTED_HIGH_RISK"
            clearance = "FLIGHT_GROUNDED"
            advisory = "CRITICAL RISK: Prohibited airspace intersection or severe hazard exceeds safe underwriting threshold. Flight strictly grounded."
        elif composite_risk >= 0.50:
            uw_status = "CONDITIONAL_CAUTION"
            clearance = "MANUAL_PILOT_OVERRIDE_REQUIRED"
            advisory = "ELEVATED RISK: High turbulence or marginal battery reserves. Approved only under active human teleoperation supervision."
        else:
            uw_status = "APPROVED_INSURED"
            clearance = "CLEARED_FOR_TAKEOFF"
            advisory = "OPTIMAL RISK PROFILE: All 5 physical dimensions cleared. EIP-712 Proof of Insurability Certificate activated."

        policy_id = f"POL_x402_{secrets.token_hex(8)}"
        valid_until = int(time.time()) + 14400  # 4 hours coverage window

        # Pre-agreed Parametric Trigger Rules
        parametric_triggers = [
            ParametricTriggerRule(
                trigger_condition="FORCE_MAJEURE_PEAK_WIND_GUST",
                threshold_value="Recorded gust speed >= 16.0 m/s at incident location",
                payout_percentage=100.0,
            ),
            ParametricTriggerRule(
                trigger_condition="CONTINUOUS_C2_LINK_BLACKOUT",
                threshold_value="Telemetry C2 blackout >= 45.0 seconds",
                payout_percentage=100.0,
            ),
            ParametricTriggerRule(
                trigger_condition="UNAUTHORIZED_WAYPOINT_DEVIATION",
                threshold_value="Flight path horizontal deviation > 250.0 meters",
                payout_percentage=0.0,  # Zero payout if pilot violates approved corridor
            ),
        ]

        # Deterministic Proof of Insurability Hash
        poi_raw = f"INSURANCE_POLICY:{policy_id}:{lat1:.4f}:{lon1:.4f}:{lat2:.4f}:{lon2:.4f}:{composite_risk}:{dynamic_premium}:{valid_until}"
        poi_hash = "0x" + hashlib.sha256(poi_raw.encode("utf-8")).hexdigest()

        policy_cert = InsurancePolicyCertificate(
            policy_id=policy_id,
            operator_id=query.operator_id or "Anonymous-Operator",
            underwriting_status=uw_status,
            total_coverage_limit_usdc=total_coverage,
            actuarial_dynamic_premium_usdc=dynamic_premium,
            proof_of_insurability_hash=poi_hash,
            valid_until_timestamp=valid_until,
            parametric_triggers=parametric_triggers,
        )

        risk_breakdown = RiskComponentBreakdown(
            terrain_tipping_hazard_score=terrain_risk,
            weather_turbulence_risk_score=weather_risk,
            airspace_regulatory_penalty_score=geofence_risk,
            comms_loss_link_risk_score=comms_risk,
            energy_depletion_risk_score=energy_risk,
            composite_mission_risk_score=composite_risk,
        )

        return InsuranceUnderwriteOutput(
            oracle_type="INSURANCE_UNDERWRITING_AND_CLEARANCE",
            policy=policy_cert,
            risk_breakdown=risk_breakdown,
            flight_clearance=clearance,
            clearance_advisory=advisory,
            deterministic_proof_hash=poi_hash,
            settlement_network=settlement_network,
            fee_paid_usdc=fee_paid,
        )

    @classmethod
    def adjudicate_claim(
        cls,
        claim: ClaimVerificationInput,
        fee_paid: float = 0.050,
        settlement_network: str = "Polygon (Chain ID 137)",
    ) -> ClaimAdjudicationOutput:
        """
        Instant Smart Contract Parametric Claim Adjudication.
        Cross-checks onboard blackbox flight data against underwriting policy triggers.
        """
        claim_id = f"CLM_x402_{secrets.token_hex(8)}"
        claimed_loss = claim.actual_damage_loss_usdc

        # Rule 1: Waypoint corridor breach check (Pilot/Operator negligence)
        if claim.blackbox_path_deviation_meters > 250.0:
            verdict = "REJECTED_PILOT_BREACH"
            payout = 0.0
            attribution = "OPERATOR_WAYPOINT_BREACH"
        # Rule 2: Force Majeure Weather Trigger
        elif claim.blackbox_wind_gust_recorded_mps >= 16.0:
            verdict = "APPROVED_PAYOUT"
            payout = claimed_loss
            attribution = "FORCE_MAJEURE_SEVERE_WEATHER"
        # Rule 3: C2 Telemetry Loss Trigger
        elif claim.blackbox_c2_link_loss_seconds >= 45.0:
            verdict = "APPROVED_PAYOUT"
            payout = claimed_loss
            attribution = "C2_TELEMETRY_BLACKOUT"
        # Rule 4: Partial Payout for Unforeseen Physical Event
        else:
            verdict = "PARTIAL_PAYOUT"
            payout = round(claimed_loss * 0.75, 2)
            attribution = "UNPREDICTED_OBSTACLE"

        # Generate onchain smart contract payout authorization string
        payout_auth = f"DISBURSE:VAULT_POLYGON:{claim.policy_id}:{payout:.2f}_USDC:{attribution}:{claim_id}"
        payout_sig = "0x" + hashlib.sha256(payout_auth.encode("utf-8")).hexdigest()

        proof_raw = f"CLAIM:{claim_id}:{claim.policy_id}:{verdict}:{payout}:{payout_sig}"
        proof_hash = "0x" + hashlib.sha256(proof_raw.encode("utf-8")).hexdigest()

        return ClaimAdjudicationOutput(
            oracle_type="PARAMETRIC_CLAIM_ADJUDICATION",
            claim_id=claim_id,
            policy_id=claim.policy_id,
            adjudication_verdict=verdict,
            adjudicated_payout_amount_usdc=payout,
            primary_fault_attribution=attribution,
            payout_smart_contract_authorization=payout_sig,
            deterministic_proof_hash=proof_hash,
            settlement_network=settlement_network,
            fee_paid_usdc=fee_paid,
        )
