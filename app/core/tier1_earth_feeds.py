"""
Tier-1 Official, Free, Commercially Usable Earth & Digital Infrastructure Feeds:
  1. USGS Earthquake Hazards API (ComCat GeoJSON — official global parametric seismic trigger)
  2. NASA EONET v3 API (live active global Wildfires, Severe Storms, Volcanoes, Floods)
  3. TeleGeography Submarine Cable Map (1,929+ global subsea cable landing stations)
  4. PeeringDB API (real global Data Centers, IXPs, and network peering density)

All feeds use aggressive TTL caching (10m–24h) and graceful offline fallbacks.
"""

from __future__ import annotations

import math
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

_USGS_CACHE: Dict[Tuple[float, float], Tuple[float, Dict[str, Any]]] = {}
_PEERING_CACHE: Dict[Tuple[float, float], Tuple[float, Dict[str, Any]]] = {}
_EONET_GLOBAL_CACHE: Tuple[float, List[Dict[str, Any]]] = (0.0, [])
_TELEGEO_GLOBAL_CACHE: Tuple[float, List[Dict[str, Any]]] = (0.0, [])

_USGS_TTL_SEC = 600.0        # 10 minutes
_EONET_TTL_SEC = 900.0       # 15 minutes (global list fetched once)
_TELEGEO_TTL_SEC = 86400.0   # 24 hours (1,929 landing stations fetched once)
_PEERING_TTL_SEC = 86400.0   # 24 hours


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two WGS84 points in kilometers."""
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2.0) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2.0) ** 2
    return 2.0 * r * math.asin(min(1.0, math.sqrt(a)))


def _round_coord(lat: float, lon: float, digits: int = 2) -> Tuple[float, float]:
    return (round(float(lat), digits), round(float(lon), digits))


async def fetch_usgs_seismic(
    lat: float, lon: float, radius_km: float = 300.0, days: int = 30, timeout_sec: float = 5.0
) -> Dict[str, Any]:
    """Fetches real 30-day M3.5+ earthquakes within radius_km from USGS ComCat API."""
    key = _round_coord(lat, lon, 2)
    now = time.time()
    cached = _USGS_CACHE.get(key)
    if cached and (now - cached[0]) < _USGS_TTL_SEC:
        return cached[1]

    start_time = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            resp = await client.get(
                "https://earthquake.usgs.gov/fdsnws/event/1/query",
                params={
                    "format": "geojson",
                    "starttime": start_time,
                    "latitude": round(lat, 4),
                    "longitude": round(lon, 4),
                    "maxradiuskm": radius_km,
                    "minmagnitude": 3.5,
                    "orderby": "magnitude",
                    "limit": 20,
                },
            )
            resp.raise_for_status()
            features = resp.json().get("features") or []

            max_mag = 0.0
            nearest_km: Optional[float] = None
            nearest_place: Optional[str] = None
            for feat in features:
                props = feat.get("properties") or {}
                coords = (feat.get("geometry") or {}).get("coordinates") or []
                mag = float(props.get("mag") or 0.0)
                if mag > max_mag:
                    max_mag = mag
                if len(coords) >= 2:
                    dist = round(haversine_km(lat, lon, float(coords[1]), float(coords[0])), 1)
                    if nearest_km is None or dist < nearest_km:
                        nearest_km = dist
                        nearest_place = props.get("place")

            result = {
                "event_count_30d": len(features),
                "max_magnitude_30d": round(max_mag, 2),
                "nearest_event_km": nearest_km,
                "nearest_event_place": nearest_place,
                "radius_km": radius_km,
                "observed_at": int(now),
                "source": "LIVE_USGS_COMCAT",
            }
            _USGS_CACHE[key] = (now, result)
            return result
    except Exception:
        return {
            "event_count_30d": 0,
            "max_magnitude_30d": 0.0,
            "nearest_event_km": None,
            "nearest_event_place": None,
            "radius_km": radius_km,
            "observed_at": int(now),
            "source": "UNAVAILABLE_FALLBACK",
        }


def filter_eonet_events_near(
    events: List[Dict[str, Any]], lat: float, lon: float, radius_km: float = 250.0
) -> Dict[str, Any]:
    """Filters cached NASA EONET v3 global events within radius_km of (lat, lon)."""
    wildfires = 0
    storms = 0
    volcanoes = 0
    matched: List[Dict[str, Any]] = []

    for ev in events:
        geoms = ev.get("geometry") or []
        if not geoms:
            continue
        latest = geoms[-1]
        coords = latest.get("coordinates")
        if not isinstance(coords, list) or len(coords) < 2 or not isinstance(coords[0], (int, float)):
            continue
        ev_lon, ev_lat = float(coords[0]), float(coords[1])
        dist = round(haversine_km(lat, lon, ev_lat, ev_lon), 1)
        if dist <= radius_km:
            cat_id = (ev.get("categories") or [{}])[0].get("id", "unknown")
            if cat_id == "wildfires":
                wildfires += 1
            elif cat_id == "severeStorms":
                storms += 1
            elif cat_id == "volcanoes":
                volcanoes += 1
            matched.append({
                "title": ev.get("title"),
                "category": cat_id,
                "distance_km": dist,
                "date": latest.get("date"),
            })

    matched.sort(key=lambda x: x["distance_km"])
    return {
        "active_events_within_radius": len(matched),
        "wildfires_nearby": wildfires,
        "storms_nearby": storms,
        "volcanoes_nearby": volcanoes,
        "nearest_event": matched[0] if matched else None,
        "radius_km": radius_km,
    }


async def fetch_nasa_eonet_hazards(
    lat: float, lon: float, radius_km: float = 250.0, timeout_sec: float = 5.0
) -> Dict[str, Any]:
    """Fetches active global natural hazards (wildfires, storms, volcanoes) from NASA EONET v3."""
    global _EONET_GLOBAL_CACHE
    now = time.time()
    cached_ts, events = _EONET_GLOBAL_CACHE

    if not events or (now - cached_ts) >= _EONET_TTL_SEC:
        try:
            async with httpx.AsyncClient(timeout=timeout_sec) as client:
                resp = await client.get(
                    "https://eonet.gsfc.nasa.gov/api/v3/events",
                    params={"status": "open", "limit": 200},
                )
                resp.raise_for_status()
                events = resp.json().get("events") or []
                _EONET_GLOBAL_CACHE = (now, events)
        except Exception:
            if not events:
                return {
                    "active_events_within_radius": 0,
                    "wildfires_nearby": 0,
                    "storms_nearby": 0,
                    "volcanoes_nearby": 0,
                    "nearest_event": None,
                    "radius_km": radius_km,
                    "observed_at": int(now),
                    "source": "UNAVAILABLE_FALLBACK",
                }

    summary = filter_eonet_events_near(events, lat, lon, radius_km=radius_km)
    summary["observed_at"] = int(now)
    summary["source"] = "LIVE_NASA_EONET_V3"
    return summary


def filter_telegeography_near(
    features: List[Dict[str, Any]], lat: float, lon: float, radius_km: float = 150.0
) -> Dict[str, Any]:
    """Finds subsea cable landing stations near (lat, lon) from cached TeleGeography GeoJSON."""
    nearby_count = 0
    nearest: Optional[Dict[str, Any]] = None
    nearest_dist: Optional[float] = None

    for feat in features:
        coords = (feat.get("geometry") or {}).get("coordinates") or []
        if len(coords) < 2:
            continue
        dist = round(haversine_km(lat, lon, float(coords[1]), float(coords[0])), 1)
        if dist <= radius_km:
            nearby_count += 1
        if nearest_dist is None or dist < nearest_dist:
            nearest_dist = dist
            props = feat.get("properties") or {}
            nearest = {
                "id": props.get("id"),
                "name": props.get("name"),
                "distance_km": dist,
            }

    return {
        "landing_stations_within_150km": nearby_count,
        "nearest_landing_station": nearest,
    }


async def fetch_telegeography_subsea(
    lat: float, lon: float, radius_km: float = 150.0, timeout_sec: float = 5.0
) -> Dict[str, Any]:
    """Fetches official TeleGeography global submarine cable landing station proximity."""
    global _TELEGEO_GLOBAL_CACHE
    now = time.time()
    cached_ts, features = _TELEGEO_GLOBAL_CACHE

    if not features or (now - cached_ts) >= _TELEGEO_TTL_SEC:
        try:
            async with httpx.AsyncClient(timeout=timeout_sec, follow_redirects=True) as client:
                resp = await client.get(
                    "https://www.submarinecablemap.com/api/v3/landing-point/landing-point-geo.json"
                )
                resp.raise_for_status()
                features = resp.json().get("features") or []
                _TELEGEO_GLOBAL_CACHE = (now, features)
        except Exception:
            if not features:
                return {
                    "landing_stations_within_150km": 0,
                    "nearest_landing_station": None,
                    "observed_at": int(now),
                    "source": "UNAVAILABLE_FALLBACK",
                }

    summary = filter_telegeography_near(features, lat, lon, radius_km=radius_km)
    summary["observed_at"] = int(now)
    summary["source"] = "LIVE_TELEGEOGRAPHY_SUBSEA"
    return summary


async def fetch_peeringdb_facilities(
    lat: float, lon: float, radius_deg: float = 0.5, timeout_sec: float = 5.0
) -> Dict[str, Any]:
    """Fetches real nearby Data Center / IXP facilities and network peering density from PeeringDB."""
    key = _round_coord(lat, lon, 2)
    now = time.time()
    cached = _PEERING_CACHE.get(key)
    if cached and (now - cached[0]) < _PEERING_TTL_SEC:
        return cached[1]

    try:
        async with httpx.AsyncClient(timeout=timeout_sec, follow_redirects=True) as client:
            resp = await client.get(
                "https://www.peeringdb.com/api/fac",
                params={
                    "latitude__gte": round(max(-90.0, lat - radius_deg), 4),
                    "latitude__lte": round(min(90.0, lat + radius_deg), 4),
                    "longitude__gte": round(max(-180.0, lon - radius_deg), 4),
                    "longitude__lte": round(min(180.0, lon + radius_deg), 4),
                    "limit": 25,
                },
            )
            resp.raise_for_status()
            facs = resp.json().get("data") or []

            total_nets = 0
            nearest: Optional[Dict[str, Any]] = None
            nearest_dist: Optional[float] = None
            for f in facs:
                net_c = int(f.get("net_count") or 0)
                total_nets += net_c
                f_lat, f_lon = f.get("latitude"), f.get("longitude")
                if f_lat is not None and f_lon is not None:
                    dist = round(haversine_km(lat, lon, float(f_lat), float(f_lon)), 1)
                    if nearest_dist is None or dist < nearest_dist:
                        nearest_dist = dist
                        nearest = {
                            "name": f.get("name"),
                            "city": f.get("city"),
                            "country": f.get("country"),
                            "net_count": net_c,
                            "distance_km": dist,
                        }

            result = {
                "nearby_dc_ixp_count": len(facs),
                "total_peering_networks": total_nets,
                "nearest_facility": nearest,
                "observed_at": int(now),
                "source": "LIVE_PEERINGDB",
            }
            _PEERING_CACHE[key] = (now, result)
            return result
    except Exception:
        return {
            "nearby_dc_ixp_count": 0,
            "total_peering_networks": 0,
            "nearest_facility": None,
            "observed_at": int(now),
            "source": "UNAVAILABLE_FALLBACK",
        }
