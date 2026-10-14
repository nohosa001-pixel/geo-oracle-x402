"""
Deterministic RF Propagation, Cellular Link-Budget, and SatCom Mesh Engine.
"""

import math
import hashlib
from app.oracles.rf_coverage.schemas import (
    RFQueryInput,
    CellularCoverage,
    SatelliteVisibility,
    LinkMarginEvaluation,
    RFCoverageOutput,
)


class RFEngine:
    """
    Computes 3D terrestrial RF path loss, cellular line-of-sight probability,
    and satellite sky clearance mask angles.
    """

    @classmethod
    def analyze(
        cls,
        query: RFQueryInput,
        fee_paid: float = 0.005,
        settlement_network: str = "Polygon (Chain ID 137)",
    ) -> RFCoverageOutput:
        lat = query.latitude
        lon = query.longitude
        alt = max(1.0, query.altitude_agl_meters or 50.0)
        req_mbps = query.required_throughput_mbps or 5.0
        tx_pwr = query.tx_power_dbm or 23.0
        ant_gain = query.antenna_gain_dbi or 3.0

        phi = math.radians(lat)
        lam = math.radians(lon)

        # 1. Terrestrial Base Station Distance & Urban/Rural Density Approximation
        urban_density = abs(math.sin(5.0 * phi) * math.cos(7.0 * lam))
        d_tower_km = max(0.2, 0.5 + 4.5 * (1.0 - urban_density))

        # 2. Line of Sight (LoS) Probability
        # Altitude improves LoS; terrain/urban obstacles reduce it
        los_prob = max(15.0, min(99.0, (1.0 - math.exp(-alt / 35.0)) * 90.0 + 10.0))

        # 3. Path Loss & Received Power (3.5 GHz 5G / 1.8 GHz LTE)
        freq_mhz = 3500.0 if urban_density > 0.4 else 1800.0
        fspl_db = 20.0 * math.log10(d_tower_km * 1000.0) + 20.0 * math.log10(freq_mhz) - 27.55
        shadowing_db = (1.0 - (los_prob / 100.0)) * 18.0
        
        rx_power_dbm = tx_pwr + ant_gain + 15.0 - fspl_db - shadowing_db
        rsrp_dbm = round(max(-135.0, min(-55.0, rx_power_dbm)), 1)
        
        sinr_db = round(max(-10.0, min(30.0, (rsrp_dbm + 110.0) * 0.8)), 1)
        rsrq_db = round(max(-20.0, min(-3.0, (sinr_db - 15.0) * 0.5 - 6.0)), 1)

        # 4. Carrier Tech & Throughput
        if rsrp_dbm > -85.0 and sinr_db > 12.0:
            tech = "5G_NR_SA"
            throughput = max(15.0, 180.0 * (sinr_db / 30.0))
        elif rsrp_dbm > -102.0 and sinr_db > 3.0:
            tech = "5G_NSA"
            throughput = max(8.0, 75.0 * (sinr_db / 20.0))
        elif rsrp_dbm > -118.0:
            tech = "4G_LTE_ADVANCED"
            throughput = max(2.0, 25.0 * ((rsrp_dbm + 120.0) / 20.0))
        else:
            tech = "3G_FALLBACK"
            throughput = 0.5

        # 5. Satellite Sky Clearance & GNSS
        # Higher altitude drastically clears the horizon mask angle
        mask_angle = max(5.0, min(65.0, 45.0 * math.exp(-alt / 80.0) + (1.0 - urban_density) * 10.0))
        starlink_los = round(max(30.0, min(100.0, 100.0 - mask_angle * 1.1)), 1)
        
        gnss_sats = int(max(6, min(24, 18 - int(mask_angle / 5.0))))
        pdop = round(max(0.9, min(4.5, 1.2 + (mask_angle / 30.0))), 2)
        multipath = round(max(0.05, min(0.90, (mask_angle / 65.0) * 0.7 + urban_density * 0.2)), 3)

        # 6. Link Margin & Health Assessment
        link_margin = round(rsrp_dbm - (-115.0), 1)  # relative to -115 dBm sensitivity
        latency = round(15.0 + 35.0 * (1.0 - los_prob / 100.0) + (10.0 if "5G" not in tech else 0.0), 1)

        if link_margin >= 18.0 and throughput >= req_mbps:
            health = "EXCELLENT"
            rec = "PRIMARY_5G_BROADBAND"
        elif link_margin >= 6.0 and throughput >= req_mbps * 0.5:
            health = "ADEQUATE"
            rec = "HYBRID_CELLULAR_READY"
        elif link_margin >= 0.0 or starlink_los > 75.0:
            health = "MARGINAL"
            rec = "FAILOVER_STARLINK_RECOMMENDED"
        else:
            health = "BLACKOUT_RISK"
            rec = "IMMEDIATE_MESH_OR_SATELLITE_EMERGENCY"

        # 7. Deterministic Proof Hash
        proof_raw = f"RF:{lat:.6f}:{lon:.6f}:{alt:.1f}:{rsrp_dbm:.1f}:{tech}:{fee_paid}"
        proof_hash = "0x" + hashlib.sha256(proof_raw.encode("utf-8")).hexdigest()

        return RFCoverageOutput(
            oracle_type="RF_COVERAGE_SATCOM_MESH",
            latitude=lat,
            longitude=lon,
            altitude_agl_meters=round(alt, 1),
            cellular=CellularCoverage(
                carrier_technology=tech,
                rsrp_dbm=rsrp_dbm,
                rsrq_db=rsrq_db,
                sinr_db=sinr_db,
                estimated_throughput_mbps=round(throughput, 1),
                base_station_los_pct=round(los_prob, 1),
            ),
            satellite=SatelliteVisibility(
                leo_starlink_los_pct=starlink_los,
                sky_view_clearance_angle_deg=round(mask_angle, 1),
                visible_gnss_satellites=gnss_sats,
                gnss_pdop=pdop,
                multipath_risk_index=multipath,
            ),
            link_margin=LinkMarginEvaluation(
                link_margin_db=link_margin,
                estimated_latency_ms=latency,
                comms_health_status=health,
                failover_recommendation=rec,
            ),
            deterministic_proof_hash=proof_hash,
            settlement_network=settlement_network,
            fee_paid_usdc=fee_paid,
        )
