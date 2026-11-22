"""
Live Earth Physical Telemetry Feeds (Open-Meteo Weather & Copernicus DEM Elevation)
with TTL in-memory caching and deterministic fallback.
"""

from __future__ import annotations

import math
import time
from typing import Any, Dict, Tuple

import httpx

_ELEVATION_CACHE: Dict[Tuple[float, float], Tuple[float, Dict[str, Any]]] = {}
_WEATHER_CACHE: Dict[Tuple[float, float], Tuple[float, Dict[str, Any]]] = {}

_ELEVATION_TTL_SEC = 86400.0  # 24 hours
_WEATHER_TTL_SEC = 300.0      # 5 minutes


def _round_coord(lat: float, lon: float) -> Tuple[float, float]:
    return (round(float(lat), 3), round(float(lon), 3))


def _fallback_elevation(lat: float, lon: float) -> float:
    phi = math.radians(lat)
    lam = math.radians(lon)
    elev = (
        120.0
        + 180.0 * abs(math.sin(2.0 * phi) * math.cos(3.0 * lam))
        + 40.0 * math.cos(7.0 * phi)
    )
    return round(max(0.0, min(8848.86, elev)), 1)


def _fallback_weather(lat: float, lon: float) -> Dict[str, Any]:
    phi = math.radians(lat)
    lam = math.radians(lon)
    temp_c = round(18.0 - 0.35 * abs(lat) + 6.0 * math.sin(3.0 * lam + 1.2) * math.cos(2.0 * phi), 1)
    wind_mps = round(3.5 + 3.0 * abs(math.sin(4.0 * phi + 0.8)) + 2.0 * abs(math.cos(6.0 * lam)), 1)
    return {
        "temperature_celsius": temp_c,
        "humidity_pct": round(max(25.0, min(90.0, 55.0 + 20.0 * math.sin(7.0 * phi))), 1),
        "surface_pressure_hpa": 1013.25,
        "wind_speed_mps": wind_mps,
        "wind_direction_deg": round((210.0 + 90.0 * math.sin(2.0 * phi)) % 360.0, 1),
        "precipitation_mm": 0.0,
        "source": "DETERMINISTIC_FALLBACK",
    }


async def fetch_live_elevation(lat: float, lon: float, timeout_sec: float = 3.0) -> Dict[str, Any]:
    """Fetches real Copernicus DEM elevation (meters) from Open-Meteo Elevation API with 24h cache."""
    key = _round_coord(lat, lon)
    now = time.time()
    cached = _ELEVATION_CACHE.get(key)
    if cached and (now - cached[0]) < _ELEVATION_TTL_SEC:
        return cached[1]

    try:
        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            resp = await client.get(
                "https://api.open-meteo.com/v1/elevation",
                params={"latitude": lat, "longitude": lon},
            )
            resp.raise_for_status()
            data = resp.json()
            elev_list = data.get("elevation") or []
            if elev_list:
                result = {
                    "elevation_meters": round(float(elev_list[0]), 1),
                    "source": "LIVE_OPEN_METEO_DEM",
                }
                _ELEVATION_CACHE[key] = (now, result)
                return result
    except Exception:
        pass

    return {
        "elevation_meters": _fallback_elevation(lat, lon),
        "source": "DETERMINISTIC_FALLBACK",
    }


async def fetch_live_weather(lat: float, lon: float, timeout_sec: float = 3.0) -> Dict[str, Any]:
    """Fetches real-time site weather from Open-Meteo Forecast API with 5m cache."""
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
                result = {
                    "temperature_celsius": round(float(curr["temperature_2m"]), 1),
                    "humidity_pct": round(float(curr.get("relative_humidity_2m", 55.0)), 1),
                    "surface_pressure_hpa": round(float(curr.get("surface_pressure", 1013.25)), 1),
                    "wind_speed_mps": round(float(curr.get("wind_speed_10m", 3.0)), 1),
                    "wind_direction_deg": round(float(curr.get("wind_direction_10m", 0.0)), 1),
                    "precipitation_mm": round(float(curr.get("precipitation", 0.0)), 2),
                    "source": "LIVE_OPEN_METEO",
                }
                _WEATHER_CACHE[key] = (now, result)
                return result
    except Exception:
        pass

    return _fallback_weather(lat, lon)
