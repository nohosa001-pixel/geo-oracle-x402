"""
Pydantic Schemas for Airspace & Regulatory Geofence Oracle.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class GeofenceCheckInput(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="WGS84 Latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="WGS84 Longitude")
    altitude_agl_meters: Optional[float] = Field(default=50.0, ge=0.0, le=10000.0, description="Requested altitude Above Ground Level (AGL) in meters")
    flight_radius_meters: Optional[float] = Field(default=100.0, ge=10.0, le=5000.0, description="Operational safety buffer radius in meters")
    vehicle_category: Optional[str] = Field(default="DRONE_COMMERCIAL", description="Vehicle type: DRONE_COMMERCIAL, DRONE_HOBBY, VTOL_TAXI, or GROUND_ROVER")


class AirspaceClassInfo(BaseModel):
    class_code: str = Field(..., description="ICAO / FAA Airspace Class (A, B, C, D, E, or G)")
    is_controlled: bool = Field(..., description="Whether ATC control is mandatory")
    floor_altitude_m: float = Field(..., description="Lower altitude boundary in meters AGL")
    ceiling_altitude_m: float = Field(..., description="Upper altitude boundary in meters AGL")


class NoFlyZoneAssessment(BaseModel):
    in_prohibited_zone: bool = Field(..., description="Whether location intersects a strict No-Fly Zone")
    zone_type: str = Field(..., description="Zone classification: AIRPORT_RUNWAY_BUFFER, MILITARY_PROHIBITED, CRITICAL_INFRASTRUCTURE, or CLEAR")
    nearest_boundary_distance_km: float = Field(..., description="Distance to nearest restricted perimeter in km")
    restricted_zone_name: Optional[str] = Field(default=None, description="Identifier of the restricted facility or boundary")


class RegulatoryCompliance(BaseModel):
    max_legal_altitude_agl_m: float = Field(..., description="Maximum allowable flight ceiling in meters AGL")
    remote_id_broadcast_required: bool = Field(..., description="Whether Open Drone ID / ASTM F3411 broadcast is mandatory")
    utm_authorization_protocol: str = Field(..., description="Authorization gateway: FAA_LAANC, EASA_U_SPACE, ICAO_UTM, or EXEMPT")
    compliance_status: str = Field(..., description="Status: CLEAR_TO_OPERATE, AUTHORIZATION_REQUIRED, or FLIGHT_PROHIBITED")
    advisory_notice: str = Field(..., description="Legal and regulatory operating instructions")


class GeofenceCheckOutput(BaseModel):
    oracle_type: str = Field(default="AIRSPACE_GEOFENCE_REGULATORY", description="Oracle capability type")
    latitude: float
    longitude: float
    altitude_agl_meters: float
    airspace: AirspaceClassInfo
    no_fly_zone: NoFlyZoneAssessment
    regulation: RegulatoryCompliance
    deterministic_proof_hash: str
    settlement_network: str
    fee_paid_usdc: float
