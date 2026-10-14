"""
Pydantic Schemas for Micro-Weather & Turbulence Oracle.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class WeatherQueryInput(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="WGS84 Latitude (-90 to +90 degrees)")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="WGS84 Longitude (-180 to +180 degrees)")
    altitude_agl_meters: Optional[float] = Field(default=50.0, ge=0.0, le=5000.0, description="Flight altitude Above Ground Level (AGL) in meters")
    heading_degrees: Optional[float] = Field(default=0.0, ge=0.0, le=360.0, description="Vehicle travel heading azimuth in degrees")
    vehicle_mass_kg: Optional[float] = Field(default=5.0, ge=0.1, le=1000.0, description="Drone or vehicle mass in kg")


class WindVector3D(BaseModel):
    u_eastward_mps: float = Field(..., description="East-West wind velocity vector (m/s)")
    v_northward_mps: float = Field(..., description="North-South wind velocity vector (m/s)")
    w_vertical_mps: float = Field(..., description="Vertical updraft/downdraft velocity vector (m/s)")
    horizontal_speed_mps: float = Field(..., description="Horizontal wind speed in m/s")
    gust_speed_mps: float = Field(..., description="Peak gust speed in m/s")
    wind_direction_from_degrees: float = Field(..., description="Meteorological wind source direction (0-360 degrees)")


class AtmosphericParameters(BaseModel):
    temperature_celsius: float = Field(..., description="Ambient temperature at altitude in Celsius")
    pressure_hpa: float = Field(..., description="Barometric air pressure in hPa")
    air_density_kg_per_m3: float = Field(..., description="Air density (rho) in kg/m^3")
    relative_humidity_pct: float = Field(..., description="Relative humidity percentage")
    icing_risk_index: float = Field(..., ge=0.0, le=1.0, description="Probability of propeller/airframe icing (0.0 to 1.0)")


class FlightStabilityAssessment(BaseModel):
    wind_shear_gradient_per_sec: float = Field(..., description="Vertical wind shear rate (du/dz) in s^-1")
    eddy_dissipation_rate_edr: float = Field(..., description="Atmospheric turbulence Eddy Dissipation Rate (m^(2/3)/s)")
    crosswind_component_mps: float = Field(..., description="Crosswind velocity relative to vehicle heading (m/s)")
    headwind_component_mps: float = Field(..., description="Headwind/tailwind velocity (m/s)")
    vtol_stability_score: float = Field(..., ge=0.0, le=1.0, description="VTOL hover and trajectory stability index (0.0 to 1.0)")
    flight_safety_category: str = Field(..., description="Safety tier: VFR_SAFE, MARGINAL_CAUTION, SEVERE_TURBULENCE, or FLIGHT_PROHIBITED")


class MicroWeatherOutput(BaseModel):
    oracle_type: str = Field(default="MICRO_WEATHER_TURBULENCE", description="Oracle capability type")
    latitude: float
    longitude: float
    altitude_agl_meters: float
    wind_vector: WindVector3D
    atmosphere: AtmosphericParameters
    flight_stability: FlightStabilityAssessment
    deterministic_proof_hash: str
    settlement_network: str
    fee_paid_usdc: float
