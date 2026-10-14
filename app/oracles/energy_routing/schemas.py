"""
Pydantic Schemas for Kinematic & Energy-Optimal Routing Oracle.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class EnergyRoutingInput(BaseModel):
    origin_latitude: float = Field(..., ge=-90.0, le=90.0, description="Start WGS84 Latitude")
    origin_longitude: float = Field(..., ge=-180.0, le=180.0, description="Start WGS84 Longitude")
    destination_latitude: float = Field(..., ge=-90.0, le=90.0, description="Target WGS84 Latitude")
    destination_longitude: float = Field(..., ge=-180.0, le=180.0, description="Target WGS84 Longitude")
    cruise_altitude_agl_meters: Optional[float] = Field(default=60.0, ge=5.0, le=2000.0, description="Cruising altitude AGL")
    vehicle_mass_kg: Optional[float] = Field(default=8.0, ge=0.5, le=500.0, description="Total all-up vehicle mass in kg")
    battery_capacity_wh: Optional[float] = Field(default=280.0, ge=10.0, le=10000.0, description="Total battery pack capacity in Watt-hours")
    initial_soc_pct: Optional[float] = Field(default=100.0, ge=10.0, le=100.0, description="Starting Battery State-of-Charge percentage")
    vehicle_type: Optional[str] = Field(default="QUADCOPTER_VTOL", description="Type: QUADCOPTER_VTOL, FIXED_WING_DRONE, or WHEELED_ROVER")
    cruise_speed_mps: Optional[float] = Field(default=12.0, ge=1.0, le=60.0, description="Target nominal speed in m/s")


class Waypoint3D(BaseModel):
    index: int = Field(..., description="Waypoint order index")
    latitude: float = Field(..., description="WGS84 Latitude")
    longitude: float = Field(..., description="WGS84 Longitude")
    altitude_agl_m: float = Field(..., description="Target altitude AGL in meters")
    segment_distance_m: float = Field(..., description="Distance from previous waypoint in meters")
    segment_energy_wh: float = Field(..., description="Energy consumed in this segment (Wh)")
    remaining_soc_pct: float = Field(..., description="Remaining battery SoC after segment (%)")


class EnergyBudgetBreakdown(BaseModel):
    potential_energy_wh: float = Field(..., description="Work against gravity during climbs (Wh)")
    aerodynamic_drag_wh: float = Field(..., description="Work against air resistance (Wh)")
    hover_or_rolling_wh: float = Field(..., description="Base lift/traction energy (Wh)")
    total_energy_consumed_wh: float = Field(..., description="Total energy expenditure for full mission (Wh)")
    final_soc_pct: float = Field(..., description="Final battery State-of-Charge upon arrival (%)")
    is_mission_feasible: bool = Field(..., description="Whether battery capacity satisfies mission safety reserve (>15% SoC)")


class MissionPerformance(BaseModel):
    total_distance_km: float = Field(..., description="Total 3D trajectory distance in km")
    total_duration_minutes: float = Field(..., description="Estimated mission duration in minutes")
    average_power_watts: float = Field(..., description="Mean power draw in Watts")
    energy_efficiency_wh_per_km: float = Field(..., description="Vehicle energy economy metric (Wh/km)")


class EnergyRoutingOutput(BaseModel):
    oracle_type: str = Field(default="ENERGY_OPTIMAL_ROUTING", description="Oracle capability type")
    origin: dict
    destination: dict
    vehicle_profile: dict
    performance: MissionPerformance
    energy_budget: EnergyBudgetBreakdown
    waypoints: List[Waypoint3D]
    deterministic_proof_hash: str
    settlement_network: str
    fee_paid_usdc: float
