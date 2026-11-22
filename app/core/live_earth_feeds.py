"""
Live Earth Physical Telemetry Feeds:
  - Copernicus DEM 5-Point Elevation & True 3D Slope/Aspect/Horizon Mask (Open-Meteo Elevation API)
  - Site-Level Real-Time Weather & Stull Wet-Bulb Temperature (Open-Meteo Forecast API)
  - Global River Discharge & 3-Day Flood Surge Forecast (Open-Meteo ECMWF GloFAS Flood API)
All feeds use TTL in-memory caching and deterministic physics fallbacks.
"""

from __future__ import annotations

import math
import time
from typing import Any, Dict, Tuple

import httpx

_DEM_CACHE: Dict[Tuple[float, float, int], Tuple[float, Dict[str, Any]]] = {}
_WEATHER_CACHE: Dict[Tuple[float, float], Tuple[float, Dict[str, Any]]] = {}
_FLOOD_CACHE: Dict[Tuple[float, float], Tuple[float, Dict[str, Any]]] = {}

_DEM_TTL_SEC = 86400.0      # 24 hours (terrain elevation is static)
_WEATHER_TTL_SEC = 300.0    # 5 minutes
_FLOOD_TTL_SEC = 3600.0     # 1 hour (daily GloFAS river discharge)

_EARTH_RADIUS_M = 6378137.0


def _round_coord(lat: float, lon: float) -> Tuple[float, float]:
    return (round(float(lat), 3), round(float(lon), 3))


def compute_wet_bulb_celsius(temp_c: float, rh_pct: float) -> float:
    """
    Computes meteorological Wet-Bulb Temperature (deg C) using Stull's (2011) empirical formula.
    Critical metric for Data Center evaporative cooling efficiency (PUE) and industrial heat stress.
    """
    rh = max(5.0, min(100.0, float(rh_pct)))
    t = float(temp_c)
    tw = (
        t * math.atan(0.151977 * math.sqrt(rh + 8.313659))
        + math.atan(t + rh)
        - math.atan(rh - 1.676331)
        + 0.00391838 * (rh ** 1.5) * math.atan(0.023101 * rh)
        - 4.686035
    )
    return round(tw, 2)


def _fallback_elevation(lat: float, lon: float) -> float:
    phi = math.radians(lat)
    lam = math.radians(lon)
    elev = (
        120.0
        + 180.0 * abs(math.sin(2.0 * phi) * math.cos(3.0 * lam))
        + 40.0 * math.cos(7.0 * phi)
    )
    return round(max(0.0, min(8848.86, elev)), 1)


def _compute_dem_derivatives(
    z_c: float, z_n: float, z_s: float, z_e: float, z_w: float, radius_m: float
) -> Dict[str, float]:
    """Computes true finite-difference 3D slope, aspect, and horizon mask angle from 5 DEM samples."""
    dz_dx = (z_e - z_w) / (2.0 * radius_m)
    dz_dy = (z_n - z_s) / (2.0 * radius_m)
    grad_mag = math.sqrt(dz_dx ** 2 + dz_dy ** 2)
    slope_deg = math.degrees(math.atan(grad_mag))
    slope_pct = grad_mag * 100.0

    aspect_rad = math.atan2(dz_dy, -dz_dx)
    aspect_deg = (450.0 - math.degrees(aspect_rad)) % 360.0

    max_neighbor_rise = max(0.0, z_n - z_c, z_s - z_c, z_e - z_c, z_w - z_c)
    horizon_mask_deg = math.degrees(math.atan2(max_neighbor_rise, radius_m))

    return {
        "elevation_meters": round(z_c, 1),
        "slope_degrees": round(slope_deg, 2),
        "slope_percentage": round(slope_pct, 2),
        "aspect_degrees": round(aspect_deg, 1),
        "horizon_mask_deg": round(horizon_mask_deg, 2),
    }


def _fallback_weather(lat: float, lon: float) -> Dict[str, Any]:
    phi = math.radians(lat)
    lam = math.radians(lon)
    temp_c = round(18.0 - 0.35 * abs(lat) + 6.0 * math.sin(3.0 * lam + 1.2) * math.cos(2.0 * phi), 1)
    rh_pct = round(max(25.0, min(90.0, 55.0 + 20.0 * math.sin(7.0 * phi))), 1)
    wind_mps = round(3.5 + 3.0 * abs(math.sin(4.0 * phi + 0.8)) + 2.0 * abs(math.cos(6.0 * lam)), 1)
    return {
        "temperature_celsius": temp_c,
        "humidity_pct": rh_pct,
        "wet_bulb_celsius": compute_wet_bulb_celsius(temp_c, rh_pct),
        "surface_pressure_hpa": 1013.25,
        "wind_speed_mps": wind_mps,
        "wind_direction_deg": round((210.0 + 90.0 * math.sin(2.0 * phi)) % 360.0, 1),
        "precipitation_mm": 0.0,
        "observed_at": int(time.time()),
        "source": "DETERMINISTIC_FALLBACK",
    }


async def fetch_live_dem_patch(
    lat: float, lon: float, radius_m: float = 90.0, timeout_sec: float = 4.0
) -> Dict[str, Any]:
    """
    Fetches a 5-point Copernicus DEM elevation patch (Center, N, S, E, W) in a single HTTP request
    to compute true geodetic elevation, 3D slope, aspect, and terrain horizon mask angle.
    """
    r_m = max(30.0, float(radius_m))
    key = (*_round_coord(lat, lon), int(round(r_m)))
    now = time.time()
    cached = _DEM_CACHE.get(key)
    if cached and (now - cached[0]) < _DEM_TTL_SEC:
        return cached[1]

    d_lat = (r_m / _EARTH_RADIUS_M) * (180.0 / math.pi)
    cos_lat = max(0.05, math.cos(math.radians(lat)))
    d_lon = (r_m / (_EARTH_RADIUS_M * cos_lat)) * (180.0 / math.pi)

    lats = [
        round(lat, 6),
        round(min(90.0, lat + d_lat), 6),
        round(max(-90.0, lat - d_lat), 6),
        round(lat, 6),
        round(lat, 6),
    ]
    lons = [
        round(lon, 6),
        round(lon, 6),
        round(lon, 6),
        round(min(180.0, lon + d_lon), 6),
        round(max(-180.0, lon - d_lon), 6),
    ]

    try:
        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            resp = await client.get(
                "https://api.open-meteo.com/v1/elevation",
                params={
                    "latitude": ",".join(str(v) for v in lats),
                    "longitude": ",".join(str(v) for v in lons),
                },
            )
            resp.raise_for_status()
            elev_list = resp.json().get("elevation") or []
            if len(elev_list) == 5:
                z_c, z_n, z_s, z_e, z_w = (float(x) for x in elev_list)
                deriv = _compute_dem_derivatives(z_c, z_n, z_s, z_e, z_w, r_m)
                result = {
                    **deriv,
                    "sampling_radius_m": r_m,
                    "observed_at": int(now),
                    "source": "LIVE_COPERNICUS_DEM_5PT",
                }
                _DEM_CACHE[key] = (now, result)
                return result
    except Exception:
        pass

    z_c = _fallback_elevation(lat, lon)
    return {
        "elevation_meters": z_c,
        "slope_degrees": None,
        "slope_percentage": None,
        "aspect_degrees": None,
        "horizon_mask_deg": None,
        "sampling_radius_m": r_m,
        "observed_at": int(now),
        "source": "DETERMINISTIC_FALLBACK",
    }


async def fetch_live_elevation(lat: float, lon: float, timeout_sec: float = 4.0) -> Dict[str, Any]:
    """Backwards-compatible elevation helper backed by 5-point Copernicus DEM patch."""
    return await fetch_live_dem_patch(lat, lon, radius_m=90.0, timeout_sec=timeout_sec)


async def fetch_live_weather(lat: float, lon: float, timeout_sec: float = 4.0) -> Dict[str, Any]:
    """Fetches real-time site weather & Stull Wet-Bulb Temperature from Open-Meteo Forecast API (5m cache)."""
    key = _round_coord(lat, lon)
    now = time.time()
    cached = _WEATHER_CACHE.get(key)
    if cached and (now - cached[0]) < _WEATHER_TTL_SEC:
        return cached[1]

    try:
        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            resp = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m,wind_direction_10m,precipitation",
                    "wind_speed_unit": "ms",
                },
            )
            resp.raise_for_status()
            curr = resp.json().get("current", {})
            if "temperature_2m" in curr:
                temp_c = round(float(curr["temperature_2m"]), 1)
                rh_pct = round(float(curr.get("relative_humidity_2m", 55.0)), 1)
                result = {
                    "temperature_celsius": temp_c,
                    "humidity_pct": rh_pct,
                    "wet_bulb_celsius": compute_wet_bulb_celsius(temp_c, rh_pct),
                    "surface_pressure_hpa": round(float(curr.get("surface_pressure", 1013.25)), 1),
                    "wind_speed_mps": round(float(curr.get("wind_speed_10m", 3.0)), 1),
                    "wind_direction_deg": round(float(curr.get("wind_direction_10m", 0.0)), 1),
                    "precipitation_mm": round(float(curr.get("precipitation", 0.0)), 2),
                    "observed_at": int(now),
                    "source": "LIVE_OPEN_METEO",
                }
                _WEATHER_CACHE[key] = (now, result)
                return result
    except Exception:
        pass

    return _fallback_weather(lat, lon)


async def fetch_live_flood(lat: float, lon: float, timeout_sec: float = 4.0) -> Dict[str, Any]:
    """
    Fetches real-time river discharge & 3-day flood peak forecast from Open-Meteo ECMWF GloFAS Flood API.
    """
    key = _round_coord(lat, lon)
    now = time.time()
    cached = _FLOOD_CACHE.get(key)
    if cached and (now - cached[0]) < _FLOOD_TTL_SEC:
        return cached[1]

    try:
        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            resp = await client.get(
                "https://flood-api.open-meteo.com/v1/flood",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "daily": "river_discharge,river_discharge_max",
                    "forecast_days": 3,
                },
            )
            resp.raise_for_status()
            daily = resp.json().get("daily", {})
            discharges = [float(v) for v in (daily.get("river_discharge") or []) if v is not None]
            maxes = [float(v) for v in (daily.get("river_discharge_max") or []) if v is not None]
            if discharges:
                curr_q = round(discharges[0], 2)
                peak_q = round(max(maxes) if maxes else max(discharges), 2)
                surge_ratio = round(peak_q / max(0.5, curr_q), 2)
                result = {
                    "river_discharge_m3s": curr_q,
                    "river_discharge_3d_max_m3s": peak_q,
                    "flood_surge_ratio": surge_ratio,
                    "observed_at": int(now),
                    "source": "LIVE_ECMWF_GLOFAS_FLOOD",
                }
                _FLOOD_CACHE[key] = (now, result)
                return result
    except Exception:
        pass

    return {
        "river_discharge_m3s": 0.0,
        "river_discharge_3d_max_m3s": 0.0,
        "flood_surge_ratio": 1.0,
        "observed_at": int(now),
        "source": "DETERMINISTIC_FALLBACK",
    }
