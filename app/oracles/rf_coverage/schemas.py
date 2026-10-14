"""
Pydantic Schemas for RF Line-of-Sight & SatCom Mesh Oracle.
"""

from typing import Optional
from pydantic import BaseModel, Field


class RFQueryInput(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="WGS84 Latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="WGS84 Longitude")
    altitude_agl_meters: Optional[float] = Field(default=50.0, ge=0.0, le=5000.0, description="Antenna altitude Above Ground Level (AGL) in meters")
    tx_power_dbm: Optional[float] = Field(default=23.0, description="Transmitter output power in dBm")
    antenna_gain_dbi: Optional[float] = Field(default=3.0, description="Vehicle antenna gain in dBi")
    required_throughput_mbps: Optional[float] = Field(default=5.0, description="Minimum target telemetry/video bitrate in Mbps")


class CellularCoverage(BaseModel):
    carrier_technology: str = Field(..., description="Active band: 5G_NR_SA, 5G_NSA, 4G_LTE_ADVANCED, or 3G_FALLBACK")
    rsrp_dbm: float = Field(..., description="Reference Signal Received Power in dBm (-140 to -40 dBm)")
    rsrq_db: float = Field(..., description="Reference Signal Received Quality in dB")
    sinr_db: float = Field(..., description="Signal-to-Interference-plus-Noise Ratio in dB")
    estimated_throughput_mbps: float = Field(..., description="Achievable downlink bandwidth in Mbps")
    base_station_los_pct: float = Field(..., description="Line-of-Sight probability with nearest gNodeB (0-100%)")


class SatelliteVisibility(BaseModel):
    leo_starlink_los_pct: float = Field(..., description="Clearance probability for LEO satellite constellations (0-100%)")
    sky_view_clearance_angle_deg: float = Field(..., description="Obstructed horizon mask angle in degrees")
    visible_gnss_satellites: int = Field(..., description="Estimated visible GPS/Galileo/Beidou satellites")
    gnss_pdop: float = Field(..., description="Position Dilution of Precision (lower is better, < 2.0 ideal)")
    multipath_risk_index: float = Field(..., ge=0.0, le=1.0, description="Terrain & building echo multipath reflection index")


class LinkMarginEvaluation(BaseModel):
    link_margin_db: float = Field(..., description="Fading margin buffer in dB (positive is safe)")
    estimated_latency_ms: float = Field(..., description="Expected round-trip latency (RTT) in ms")
    comms_health_status: str = Field(..., description="Status: EXCELLENT, ADEQUATE, MARGINAL, or BLACKOUT_RISK")
    failover_recommendation: str = Field(..., description="Recommended network interface (e.g., PRIMARY_5G, FAILOVER_STARLINK, MESH_RELAY)")


class RFCoverageOutput(BaseModel):
    oracle_type: str = Field(default="RF_COVERAGE_SATCOM_MESH", description="Oracle capability type")
    latitude: float
    longitude: float
    altitude_agl_meters: float
    cellular: CellularCoverage
    satellite: SatelliteVisibility
    link_margin: LinkMarginEvaluation
    deterministic_proof_hash: str
    settlement_network: str
    fee_paid_usdc: float
