"""
Deterministic Atmospheric Boundary Layer & Micro-Weather Physics Engine.
"""

import math
import hashlib
from app.oracles.weather.schemas import (
    WeatherQueryInput,
    WindVector3D,
    AtmosphericParameters,
    FlightStabilityAssessment,
    MicroWeatherOutput,
)


class WeatherEngine:
    """
    Computes 3D micro-wind fields, boundary layer shear, EDR turbulence,
    barometric density, and VTOL flight stability scores.
    """

    GAS_CONSTANT_AIR = 287.05  # J/(kg*K)
    GRAVITY = 9.80665          # m/s^2

    @classmethod
    def analyze(
        cls,
        query: WeatherQueryInput,
        fee_paid: float = 0.005,
        settlement_network: str = "Polygon (Chain ID 137)",
    ) -> MicroWeatherOutput:
        lat = query.latitude
        lon = query.longitude
        alt = max(1.0, query.altitude_agl_meters or 50.0)
        heading = query.heading_degrees or 0.0
        mass = query.vehicle_mass_kg or 5.0

        phi = math.radians(lat)
        lam = math.radians(lon)

        # 1. Base Sea-Level Surface State
        t_base_c = 15.0 - 0.45 * abs(lat) + 8.0 * math.sin(3.0 * lam + 1.2) * math.cos(2.0 * phi)
        p_base_hpa = 1013.25 + 18.0 * math.cos(5.0 * phi) * math.sin(4.0 * lam)
        rh_base_pct = max(20.0, min(95.0, 55.0 + 30.0 * math.sin(7.0 * phi) * math.cos(5.0 * lam)))

        # 2. Atmospheric Barometric Lapse
        lapse_rate = 0.0065  # 6.5 C per 1000m
        t_alt_c = t_base_c - (lapse_rate * alt)
        t_kelvin = t_alt_c + 273.15
        
        # Barometric pressure formula
        p_alt_hpa = p_base_hpa * ((1.0 - (lapse_rate * alt) / (t_base_c + 273.15)) ** (cls.GRAVITY / (cls.GAS_CONSTANT_AIR * lapse_rate)))
        p_pascals = p_alt_hpa * 100.0
        rho = p_pascals / (cls.GAS_CONSTANT_AIR * t_kelvin)  # kg/m^3

        # 3. 3D Wind Vector Simulation using Boundary Layer Log-Profile
        z0 = 0.05  # aerodynamic roughness
        ref_speed = 4.5 + 4.0 * abs(math.sin(4.0 * phi + 0.8)) + 3.0 * abs(math.cos(6.0 * lam))
        
        # Logarithmic vertical wind shear profile
        alt_factor = math.log(max(1.0, alt) / z0) / math.log(10.0 / z0)
        horiz_speed = max(0.5, ref_speed * alt_factor)
        
        wind_dir = (210.0 + 90.0 * math.sin(2.0 * phi) + 45.0 * math.cos(3.0 * lam)) % 360.0
        wind_rad = math.radians(wind_dir)
        
        # Meteorological convention: wind from direction
        u_east = -horiz_speed * math.sin(wind_rad)
        v_north = -horiz_speed * math.cos(wind_rad)
        w_vert = 0.8 * math.sin(11.0 * phi) * math.cos(13.0 * lam) * (1.0 + alt / 200.0)
        
        gust_speed = horiz_speed * (1.35 + 0.25 * abs(math.sin(9.0 * phi)))
        wind_shear = max(0.01, (horiz_speed - ref_speed) / max(10.0, alt))

        # 4. Turbulence Eddy Dissipation Rate (EDR)
        edr = round(max(0.02, min(0.85, 0.08 * (horiz_speed / 5.0) * (gust_speed / horiz_speed) + wind_shear * 0.5)), 3)

        # 5. Icing Risk Index
        if -10.0 <= t_alt_c <= 2.0 and rh_base_pct > 75.0:
            icing_risk = round(min(1.0, (rh_base_pct - 70.0) / 30.0 * (1.0 - abs(t_alt_c + 3.0) / 7.0)), 3)
        else:
            icing_risk = 0.05

        # 6. Relative Wind Components relative to Drone Heading
        rel_angle_rad = math.radians((wind_dir - heading + 360.0) % 360.0)
        crosswind = abs(horiz_speed * math.sin(rel_angle_rad))
        headwind = horiz_speed * math.cos(rel_angle_rad)

        # 7. VTOL Stability Score (0.0 to 1.0)
        mass_penalty = max(0.5, min(1.5, mass / 5.0))
        stability_raw = 1.0 - (gust_speed / 25.0)**1.4 - (edr / 0.7)**1.2 - (crosswind / 18.0) * (1.0 / mass_penalty) - icing_risk * 0.3
        vtol_score = round(max(0.0, min(1.0, stability_raw)), 3)

        if vtol_score > 0.75:
            cat = "VFR_SAFE"
        elif vtol_score > 0.45:
            cat = "MARGINAL_CAUTION"
        elif vtol_score > 0.15:
            cat = "SEVERE_TURBULENCE"
        else:
            cat = "FLIGHT_PROHIBITED"

        # 8. Deterministic Hash
        proof_raw = f"WEATHER:{lat:.6f}:{lon:.6f}:{alt:.1f}:{horiz_speed:.2f}:{t_alt_c:.2f}:{fee_paid}"
        proof_hash = "0x" + hashlib.sha256(proof_raw.encode("utf-8")).hexdigest()

        return MicroWeatherOutput(
            oracle_type="MICRO_WEATHER_TURBULENCE",
            latitude=lat,
            longitude=lon,
            altitude_agl_meters=round(alt, 1),
            wind_vector=WindVector3D(
                u_eastward_mps=round(u_east, 2),
                v_northward_mps=round(v_north, 2),
                w_vertical_mps=round(w_vert, 2),
                horizontal_speed_mps=round(horiz_speed, 2),
                gust_speed_mps=round(gust_speed, 2),
                wind_direction_from_degrees=round(wind_dir, 1),
            ),
            atmosphere=AtmosphericParameters(
                temperature_celsius=round(t_alt_c, 1),
                pressure_hpa=round(p_alt_hpa, 1),
                air_density_kg_per_m3=round(rho, 3),
                relative_humidity_pct=round(rh_base_pct, 1),
                icing_risk_index=icing_risk,
            ),
            flight_stability=FlightStabilityAssessment(
                wind_shear_gradient_per_sec=round(wind_shear, 4),
                eddy_dissipation_rate_edr=edr,
                crosswind_component_mps=round(crosswind, 2),
                headwind_component_mps=round(headwind, 2),
                vtol_stability_score=vtol_score,
                flight_safety_category=cat,
            ),
            deterministic_proof_hash=proof_hash,
            settlement_network=settlement_network,
            fee_paid_usdc=fee_paid,
        )
