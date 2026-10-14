"""
Pydantic Schemas for Geo-Terrain & Trafficability Oracle.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class GeoCoordinateInput(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="WGS84 Latitude (-90 to +90 degrees)")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="WGS84 Longitude (-180 to +180 degrees)")
    sampling_radius_meters: Optional[float] = Field(default=30.0, ge=5.0, le=1000.0, description="Analysis radius in meters")
    agent_id: Optional[str] = Field(default="generic-physical-agent", description="Calling autonomous agent identifier")


class TrafficabilityMetrics(BaseModel):
    wheeled_rover_score: float = Field(..., ge=0.0, le=1.0, description="Mobility score for wheeled rovers (0.0 to 1.0)")
    tracked_vehicle_score: float = Field(..., ge=0.0, le=1.0, description="Mobility score for tracked/tank vehicles")
    quadruped_bot_score: float = Field(..., ge=0.0, le=1.0, description="Mobility score for legged/quadruped robots")
    drone_landing_score: float = Field(..., ge=0.0, le=1.0, description="Flatness and clearance score for drone landing")
    overall_status: str = Field(..., description="Classification: GO, CAUTION, HAZARDOUS, or IMPASSABLE")


class SurfacePhysics(BaseModel):
    friction_coefficient_mu: float = Field(..., description="Estimated static ground friction coefficient")
    roughness_length_z0_m: float = Field(..., description="Aerodynamic roughness length in meters")
    max_safe_speed_mps: float = Field(..., description="Maximum recommended velocity in m/s")
    tip_over_risk_index: float = Field(..., ge=0.0, le=1.0, description="Roll/pitch tipping probability index")


class TerrainPhysicsOutput(BaseModel):
    oracle_type: str = Field(default="TERRAIN_PHYSICS", description="Oracle capability type")
    latitude: float
    longitude: float
    elevation_meters: float
    slope_gradient_degrees: float
    slope_gradient_percentage: float
    aspect_degrees: float
    aspect_compass: str
    solar_exposure_index: float
    terrain_classification: str
    soil_roughness_score: float
    trafficability: TrafficabilityMetrics
    physics: SurfacePhysics
    deterministic_proof_hash: str
    settlement_network: str
    fee_paid_usdc: float
