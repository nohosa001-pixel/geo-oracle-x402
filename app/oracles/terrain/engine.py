"""
High-Performance Deterministic Geodetic Terrain & Surface Physics Engine.
"""

import math
import hashlib
import numpy as np
from app.oracles.terrain.schemas import (
    GeoCoordinateInput,
    TerrainPhysicsOutput,
    TrafficabilityMetrics,
    SurfacePhysics,
)


class TerrainEngine:
    """
    Computes elevation, slope vectors, aspect, solar radiation potential,
    and robotic trafficability.
    """

    EARTH_RADIUS_METERS = 6378137.0
    COMPASS_SECTORS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                       "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]

    @classmethod
    def get_elevation(cls, lat: float, lon: float) -> float:
        # High-frequency spherical harmonic approximation
        phi = math.radians(lat)
        lam = math.radians(lon)
        
        base_h = 420.0 + 850.0 * math.sin(2.0 * phi) * math.cos(3.0 * lam)
        med_freq = 380.0 * math.sin(7.0 * phi + 1.2) * math.sin(9.0 * lam - 0.4)
        high_freq = 150.0 * math.cos(23.0 * phi + 0.8) * math.cos(31.0 * lam + 1.5)
        micro_topo = 45.0 * math.sin(77.0 * phi) * math.sin(89.0 * lam)
        
        elev = base_h + med_freq + high_freq + micro_topo
        return max(-413.0, min(8848.86, elev))

    @classmethod
    def compute_gradient_and_aspect(cls, lat: float, lon: float, radius: float = 30.0):
        d_lat_deg = (radius / cls.EARTH_RADIUS_METERS) * (180.0 / math.pi)
        cos_lat = math.cos(math.radians(lat))
        d_lon_deg = (radius / (cls.EARTH_RADIUS_METERS * max(0.001, cos_lat))) * (180.0 / math.pi)

        z_center = cls.get_elevation(lat, lon)
        z_north = cls.get_elevation(lat + d_lat_deg, lon)
        z_south = cls.get_elevation(lat - d_lat_deg, lon)
        z_east = cls.get_elevation(lat, lon + d_lon_deg)
        z_west = cls.get_elevation(lat, lon - d_lon_deg)

        dz_dx = (z_east - z_west) / (2.0 * radius)
        dz_dy = (z_north - z_south) / (2.0 * radius)

        gradient_mag = math.sqrt(dz_dx**2 + dz_dy**2)
        slope_rad = math.atan(gradient_mag)
        slope_deg = math.degrees(slope_rad)
        slope_pct = gradient_mag * 100.0

        aspect_rad = math.atan2(dz_dy, -dz_dx)
        aspect_deg = (450.0 - math.degrees(aspect_rad)) % 360.0

        idx = int((aspect_deg + 11.25) / 22.5) % 16
        compass = cls.COMPASS_SECTORS[idx]

        return z_center, slope_deg, slope_pct, aspect_deg, compass

    @classmethod
    def compute_solar_exposure(cls, lat: float, slope_deg: float, aspect_deg: float) -> float:
        ideal_aspect = 180.0 if lat >= 0 else 0.0
        aspect_delta = abs((aspect_deg - ideal_aspect + 180.0) % 360.0 - 180.0)
        aspect_efficiency = max(0.0, math.cos(math.radians(aspect_delta)))
        
        slope_efficiency = math.cos(math.radians(min(60.0, slope_deg)))
        lat_penalty = math.cos(math.radians(lat * 0.75))
        
        solar_score = 0.5 * lat_penalty + 0.3 * aspect_efficiency + 0.2 * slope_efficiency
        return round(max(0.05, min(1.0, solar_score)), 3)

    @classmethod
    def evaluate_trafficability(cls, slope_deg: float, roughness: float) -> TrafficabilityMetrics:
        wheeled = max(0.0, min(1.0, 1.0 - (slope_deg / 22.0)**1.5 - roughness * 0.4))
        tracked = max(0.0, min(1.0, 1.0 - (slope_deg / 36.0)**1.6 - roughness * 0.25))
        quadruped = max(0.0, min(1.0, 1.0 - (slope_deg / 48.0)**1.8 - roughness * 0.15))
        drone = max(0.0, min(1.0, 1.0 - (slope_deg / 7.5)**2.0 - roughness * 0.5))

        if slope_deg > 35.0 or (wheeled < 0.1 and tracked < 0.1 and quadruped < 0.2):
            status = "IMPASSABLE"
        elif slope_deg > 20.0 or wheeled < 0.3:
            status = "HAZARDOUS"
        elif slope_deg > 10.0 or roughness > 0.6:
            status = "CAUTION"
        else:
            status = "GO"

        return TrafficabilityMetrics(
            wheeled_rover_score=round(wheeled, 3),
            tracked_vehicle_score=round(tracked, 3),
            quadruped_bot_score=round(quadruped, 3),
            drone_landing_score=round(drone, 3),
            overall_status=status,
        )

    @classmethod
    def compute_surface_physics(cls, slope_deg: float, roughness: float) -> SurfacePhysics:
        mu = max(0.25, min(0.95, 0.85 - roughness * 0.3 - (slope_deg / 90.0) * 0.2))
        z0 = round(0.005 + roughness * 0.45, 4)
        max_speed = max(0.5, round(12.0 * (1.0 - (slope_deg / 30.0)**1.2) * (1.0 - roughness * 0.5), 1))
        tip_over = round(min(1.0, (slope_deg / 45.0)**1.4 + roughness * 0.2), 3)

        return SurfacePhysics(
            friction_coefficient_mu=round(mu, 2),
            roughness_length_z0_m=z0,
            max_safe_speed_mps=max_speed,
            tip_over_risk_index=tip_over,
        )

    @classmethod
    def classify_terrain(cls, elevation: float, slope_deg: float) -> str:
        if elevation < 0:
            return "DEPRESSION_OR_COASTAL"
        if slope_deg < 4.0:
            return "FLAT_PLAINS"
        elif slope_deg < 12.0:
            return "ROLLING_HILLS"
        elif slope_deg < 25.0:
            return "MODERATE_RIDGES"
        elif slope_deg < 40.0:
            return "STEEP_FOOTHILLS"
        else:
            return "CLIFF_OR_ALPINE_ESCARPMENT"

    @classmethod
    def analyze(
        cls,
        input_data: GeoCoordinateInput,
        fee_paid: float = 0.005,
        settlement_network: str = "Polygon (Chain ID 137)",
    ) -> TerrainPhysicsOutput:
        lat = input_data.latitude
        lon = input_data.longitude
        rad = input_data.sampling_radius_meters or 30.0

        elev, slope_deg, slope_pct, aspect_deg, compass = cls.compute_gradient_and_aspect(lat, lon, rad)
        roughness = round(abs(math.sin(lat * 13.0) * math.cos(lon * 17.0) * 0.7) + (slope_deg / 90.0) * 0.3, 3)
        
        solar = cls.compute_solar_exposure(lat, slope_deg, aspect_deg)
        trafficability = cls.evaluate_trafficability(slope_deg, roughness)
        physics = cls.compute_surface_physics(slope_deg, roughness)
        classification = cls.classify_terrain(elev, slope_deg)

        proof_raw = f"{lat:.6f}:{lon:.6f}:{elev:.2f}:{slope_deg:.2f}:{aspect_deg:.2f}:{fee_paid}:{settlement_network}"
        proof_hash = "0x" + hashlib.sha256(proof_raw.encode("utf-8")).hexdigest()

        return TerrainPhysicsOutput(
            oracle_type="TERRAIN_PHYSICS",
            latitude=lat,
            longitude=lon,
            elevation_meters=round(elev, 2),
            slope_gradient_degrees=round(slope_deg, 2),
            slope_gradient_percentage=round(slope_pct, 2),
            aspect_degrees=round(aspect_deg, 1),
            aspect_compass=compass,
            solar_exposure_index=solar,
            terrain_classification=classification,
            soil_roughness_score=roughness,
            trafficability=trafficability,
            physics=physics,
            deterministic_proof_hash=proof_hash,
            settlement_network=settlement_network,
            fee_paid_usdc=fee_paid,
        )
