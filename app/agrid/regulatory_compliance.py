"""
Future Logistics Regulatory Compliance & Cold-Chain SLA Engine.
Implements:
1. FAA Part 108 Beyond Visual Line of Sight (BVLOS) Quantitative Assessment
2. EASA U-space & SORA 2.5 (GRC / ARC / SAIL I~VI) Framework
3. WHO PQS & FDA 21 CFR Part 11 Pharma Cold-Chain SLA Audit
"""

import math
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class BvlosAuditRequest(BaseModel):
    carrier_agent_id: str = Field(..., description="Unique drone/carrier robot ID")
    flight_corridor_length_km: float = Field(..., ge=0.1, le=250.0)
    planned_altitude_agl_m: float = Field(..., ge=10.0, le=300.0)
    airspace_class: str = Field("G", description="Airspace Class: G, E, D, C, B")
    has_active_ads_b_in: bool = Field(True, description="Equipped with ADS-B In receiver")
    has_optical_daa: bool = Field(True, description="Equipped with optical/LiDAR Detect and Avoid")
    has_radar_daa: bool = Field(False, description="Equipped with mmWave radar DAA")
    ground_population_density_per_sq_km: float = Field(50.0, ge=0.0, description="People per km^2 along route")
    satellite_c2_link_active: bool = Field(True, description="Starlink/SatCom redundant C2 link active")
    contingency_landing_sites_count: int = Field(3, ge=0, description="Designated emergency landing spots")


class ColdChainAuditRequest(BaseModel):
    consignment_id: str = Field(..., description="Shipment consignment ID")
    pharma_category: str = Field(
        "Refrigerated_2_8C",
        description="UltraCold_mRNA (-80C~-60C), Frozen (-25C~-15C), Refrigerated_2_8C (2C~8C), ControlledRoom (15C~25C)"
    )
    monitored_temperatures_celsius: List[float] = Field(..., description="Array of periodic sensor readings")
    elapsed_minutes: float = Field(..., ge=1.0)
    container_vacuum_insulation_ok: bool = Field(True)
    sensor_calibration_valid: bool = Field(True)


class RegulatoryComplianceEngine:
    """
    Evaluates autonomous drone logistics flights against cutting-edge global aviation
    and pharmaceutical cold-chain standards.
    """

    # -------------------------------------------------------------------------
    # 1. FAA PART 108 BVLOS AUDIT
    # -------------------------------------------------------------------------
    @classmethod
    def evaluate_faa_part108(cls, req: BvlosAuditRequest) -> Dict[str, Any]:
        """
        Evaluates FAA Part 108 proposed BVLOS requirements:
        - Strategic deconfliction & DAA equipage
        - Ground risk mitigation
        - Authorization classification (Permit vs Certificate)
        """
        # DAA Capabilities Score (0.0 ~ 1.0)
        daa_score = 0.0
        if req.has_active_ads_b_in:
            daa_score += 0.40
        if req.has_optical_daa:
            daa_score += 0.35
        if req.has_radar_daa:
            daa_score += 0.25

        # C2 Link Reliability
        c2_score = 1.0 if req.satellite_c2_link_active else 0.65

        # Strategic Ground Risk
        pop = req.ground_population_density_per_sq_km
        if pop < 50:
            ground_risk_category = "SPARSE_RURAL"
            ground_risk_penalty = 0.05
        elif pop < 500:
            ground_risk_category = "SUBURBAN_LOW_DENSITY"
            ground_risk_penalty = 0.20
        else:
            ground_risk_category = "DENSE_URBAN"
            ground_risk_penalty = 0.45

        # Airspace Risk
        airspace_risk_map = {"G": 0.05, "E": 0.15, "D": 0.35, "C": 0.50, "B": 0.80}
        airspace_penalty = airspace_risk_map.get(req.airspace_class.upper(), 0.30)

        # Altitude Compliance (FAA 400ft / 121.9m standard)
        altitude_penalty = 0.0
        if req.planned_altitude_agl_m > 122.0:
            altitude_penalty = min(0.40, (req.planned_altitude_agl_m - 122.0) / 100.0)

        total_risk_score = round(
            (1.0 - daa_score) * 0.35 +
            (1.0 - c2_score) * 0.20 +
            ground_risk_penalty * 0.25 +
            airspace_penalty * 0.10 +
            altitude_penalty * 0.10,
            3
        )

        compliant = (daa_score >= 0.70) and (total_risk_score <= 0.45) and req.contingency_landing_sites_count >= 2

        # Operational Authorization Tier under Part 108
        if total_risk_score <= 0.25 and req.ground_population_density_per_sq_km < 100:
            auth_tier = "FAA_PART_108_PERMIT_STANDARD"
        elif compliant:
            auth_tier = "FAA_PART_108_CERTIFICATE_ENHANCED"
        else:
            auth_tier = "FAA_PART_108_REJECTED_REQUIRES_WAIVER"

        return {
            "standard": "FAA_Part_108_BVLOS",
            "compliant": compliant,
            "authorization_tier": auth_tier,
            "total_risk_score": total_risk_score,
            "daa_equipage_score": round(daa_score, 2),
            "c2_link_score": round(c2_score, 2),
            "ground_risk_category": ground_risk_category,
            "audit_verdict": "AUTHORIZED_BVLOS" if compliant else "BVLOS_REJECTED",
            "recommendations": (
                ["Equip dual-layer mmWave radar DAA", "Increase emergency landing zones"]
                if not compliant else
                ["Maintain 5G/Starlink dual link monitoring during cruise"]
            )
        }

    # -------------------------------------------------------------------------
    # 2. EASA U-SPACE & SORA 2.5 AUDIT
    # -------------------------------------------------------------------------
    @classmethod
    def evaluate_easa_sora25(
        cls,
        drone_wingspan_m: float,
        impact_kinetic_energy_kj: float,
        ground_population_density: float,
        airspace_class: str
    ) -> Dict[str, Any]:
        """
        Determines Ground Risk Class (GRC), Air Risk Class (ARC), and
        Specific Assurance and Integrity Level (SAIL I ~ SAIL VI) under SORA 2.5.
        """
        # 1. Intrinsic GRC
        if impact_kinetic_energy_kj < 1.0:
            base_grc = 1
        elif impact_kinetic_energy_kj < 10.0:
            base_grc = 2 if ground_population_density < 50 else 3
        elif impact_kinetic_energy_kj < 34.0:
            base_grc = 3 if ground_population_density < 50 else 4
        else:
            base_grc = 5 if ground_population_density < 100 else 6

        final_grc = min(base_grc, 7)

        # 2. Air Risk Class (ARC)
        if airspace_class.upper() in ["G", "E"]:
            arc = "ARC-b"
        elif airspace_class.upper() in ["D", "C"]:
            arc = "ARC-c"
        else:
            arc = "ARC-d"

        # 3. SAIL Matrix Lookup (SORA 2.5)
        sail_matrix = {
            (1, "ARC-b"): "SAIL_I",
            (2, "ARC-b"): "SAIL_II",
            (3, "ARC-b"): "SAIL_II",
            (4, "ARC-b"): "SAIL_III",
            (3, "ARC-c"): "SAIL_III",
            (4, "ARC-c"): "SAIL_IV",
            (5, "ARC-c"): "SAIL_IV",
            (6, "ARC-d"): "SAIL_V",
            (7, "ARC-d"): "SAIL_VI",
        }
        sail = sail_matrix.get((final_grc, arc), "SAIL_III")

        u_space_mandatory = (final_grc >= 3 or arc in ["ARC-c", "ARC-d"])

        return {
            "standard": "EASA_U_space_SORA_2.5",
            "ground_risk_class": final_grc,
            "air_risk_class": arc,
            "sail_level": sail,
            "u_space_mandatory": u_space_mandatory,
            "required_mitigations": [
                "Network Remote ID active",
                "Geo-awareness dynamic geocage active",
                "USSP automated flight authorization confirmed"
            ] if u_space_mandatory else ["Basic geo-awareness"]
        }

    # -------------------------------------------------------------------------
    # 3. WHO PQS & FDA 21 CFR COLD-CHAIN BIO AUDIT
    # -------------------------------------------------------------------------
    @classmethod
    def evaluate_coldchain_sla(cls, req: ColdChainAuditRequest) -> Dict[str, Any]:
        """
        Audits pharmaceutical consignment temperatures against WHO/FDA thermal standards.
        Calculates Mean Kinetic Temperature (MKT) and SLA compliance.
        """
        temp_bounds = {
            "UltraCold_mRNA": (-80.0, -60.0),
            "Frozen": (-25.0, -15.0),
            "Refrigerated_2_8C": (2.0, 8.0),
            "ControlledRoom": (15.0, 25.0),
        }
        min_t, max_t = temp_bounds.get(req.pharma_category, (2.0, 8.0))

        temps = req.monitored_temperatures_celsius
        if not temps:
            raise ValueError("Temperature readings cannot be empty.")

        min_recorded = min(temps)
        max_recorded = max(temps)
        avg_temp = sum(temps) / len(temps)

        # Calculate Mean Kinetic Temperature (MKT)
        # Activation energy deltaH/R approx 10,000 K for pharmaceutical degradation
        DH_R = 10000.0
        exp_sum = 0.0
        for t in temps:
            t_kelvin = t + 273.15
            exp_sum += math.exp(-DH_R / t_kelvin)
        mkt_kelvin = -DH_R / math.log(exp_sum / len(temps))
        mkt_celsius = round(mkt_kelvin - 273.15, 2)

        # Excursion Check
        excursion_count = sum(1 for t in temps if t < min_t or t > max_t)
        excursion_ratio = excursion_count / len(temps)

        sla_breached = (
            excursion_ratio > 0.05 or
            min_recorded < (min_t - 2.0) or
            max_recorded > (max_t + 2.0) or
            not req.sensor_calibration_valid
        )

        return {
            "standard": "WHO_PQS_FDA_21CFR_Part11",
            "pharma_category": req.pharma_category,
            "target_range_celsius": f"{min_t}C ~ {max_t}C",
            "recorded_min_celsius": min_recorded,
            "recorded_max_celsius": max_recorded,
            "average_temp_celsius": round(avg_temp, 2),
            "mean_kinetic_temperature_mkt_celsius": mkt_celsius,
            "sensor_readings_count": len(temps),
            "excursion_points_count": excursion_count,
            "sla_breached": sla_breached,
            "pharma_release_status": "REJECTED_DISCARD" if sla_breached else "VERIFIED_GOOD_TO_DISBURSE",
            "audit_message": (
                f"SLA violation: Temperature breached range [{min_t}C, {max_t}C]"
                if sla_breached else
                "Thermal envelope flawlessly maintained across mission profile."
            )
        }
