"""
Deterministic Airspace Geometry & Regulatory Geofence Engine with Live NOTAM Sync Integration.
"""

import math
import hashlib
from app.sync.data_registry import LiveDataRegistry
from app.oracles.geofence.schemas import (
    GeofenceCheckInput,
    AirspaceClassInfo,
    NoFlyZoneAssessment,
    RegulatoryCompliance,
    GeofenceCheckOutput,
)


class GeofenceEngine:
    """
    Evaluates global geodetic coordinates against airspace boundaries,
    No-Fly Zones (NFZ), and dynamically synced NOTAM restrictions.
    """

    KNOWN_AIRPORTS = [
        {"name": "Incheon International (ICN)", "lat": 37.4602, "lon": 126.4407, "radius_km": 9.3},
        {"name": "Gimpo International (GMP)", "lat": 37.5583, "lon": 126.7906, "radius_km": 9.3},
        {"name": "Tokyo Haneda (HND)", "lat": 35.5494, "lon": 139.7798, "radius_km": 9.3},
        {"name": "Frankfurt Main (FRA)", "lat": 50.0379, "lon": 8.5622, "radius_km": 9.3},
        {"name": "Geneva Cointrin (GVA)", "lat": 46.2370, "lon": 6.1092, "radius_km": 9.3},
        {"name": "Los Angeles Intl (LAX)", "lat": 33.9416, "lon": -118.4085, "radius_km": 9.3},
        {"name": "John F Kennedy (JFK)", "lat": 40.6413, "lon": -73.7781, "radius_km": 9.3},
    ]

    RESTRICTED_GOV_ZONES = [
        {"name": "Seoul Metropolitan Prohibited Airspace (P-73)", "lat": 37.5665, "lon": 126.9780, "radius_km": 8.0},
        {"name": "Washington DC Flight Restricted Zone (FRZ)", "lat": 38.8951, "lon": -77.0364, "radius_km": 24.0},
        {"name": "CERN Particle Accelerator Restricted Facility", "lat": 46.2330, "lon": 6.0557, "radius_km": 3.5},
    ]

    @classmethod
    def haversine_distance_km(cls, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)

        a = math.sin(dphi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0)**2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return 6371.0 * c

    @classmethod
    def check(
        cls,
        query: GeofenceCheckInput,
        fee_paid: float = 0.005,
        settlement_network: str = "Polygon (Chain ID 137)",
    ) -> GeofenceCheckOutput:
        lat = query.latitude
        lon = query.longitude
        alt = query.altitude_agl_meters or 50.0
        v_type = query.vehicle_category or "DRONE_COMMERCIAL"

        in_nfz = False
        zone_type = "CLEAR"
        restricted_name = None
        min_dist_km = 9999.0

        # 1. Check Live Synced Dynamic NOTAM Restrictions
        active_notams = LiveDataRegistry.get_active_notams()
        for notam in active_notams:
            d = cls.haversine_distance_km(lat, lon, notam["lat"], notam["lon"])
            if d < min_dist_km:
                min_dist_km = d
            if d <= notam.get("radius_km", 5.0) and notam.get("min_alt_m", 0) <= alt <= notam.get("max_alt_m", 5000):
                if "PREFERENTIAL_CLEARANCE" in notam.get("restriction_type", ""):
                    zone_type = "APPROVED_DRONE_CORRIDOR"
                    restricted_name = notam["name"]
                else:
                    in_nfz = True
                    zone_type = notam.get("restriction_type", "DYNAMIC_NOTAM_RESTRICTION")
                    restricted_name = notam["name"]
                    break

        # 2. Check Static Permanent Government NFZ
        if not in_nfz:
            for rz in cls.RESTRICTED_GOV_ZONES:
                d = cls.haversine_distance_km(lat, lon, rz["lat"], rz["lon"])
                if d < min_dist_km:
                    min_dist_km = d
                if d <= rz["radius_km"]:
                    in_nfz = True
                    zone_type = "MILITARY_PROHIBITED"
                    restricted_name = rz["name"]
                    break

        # 3. Check Airport Aerodrome Buffers
        if not in_nfz:
            for apt in cls.KNOWN_AIRPORTS:
                d = cls.haversine_distance_km(lat, lon, apt["lat"], apt["lon"])
                if d < min_dist_km:
                    min_dist_km = d
                if d <= apt["radius_km"]:
                    in_nfz = True
                    zone_type = "AIRPORT_RUNWAY_BUFFER"
                    restricted_name = apt["name"]
                    break

        # 4. Determine Airspace Class
        if alt > 5500.0:
            airspace_code = "A"
            is_controlled = True
            floor_m = 5500.0
            ceil_m = 18000.0
        elif in_nfz and zone_type == "AIRPORT_RUNWAY_BUFFER":
            airspace_code = "B"
            is_controlled = True
            floor_m = 0.0
            ceil_m = 3000.0
        elif min_dist_km < 25.0:
            airspace_code = "C" if min_dist_km < 15.0 else "D"
            is_controlled = True
            floor_m = 0.0
            ceil_m = 1200.0
        else:
            airspace_code = "G"
            is_controlled = False
            floor_m = 0.0
            ceil_m = 120.0

        # 5. Standard Drone Ceiling & Regulation
        max_legal_alt = 120.0
        remote_id = (v_type != "GROUND_ROVER")

        if lat >= 24.0 and lat <= 49.0 and lon >= -125.0 and lon <= -66.0:
            protocol = "FAA_LAANC"
        elif lat >= 35.0 and lat <= 70.0 and lon >= -10.0 and lon <= 35.0:
            protocol = "EASA_U_SPACE"
        else:
            protocol = "ICAO_UTM"

        # 6. Final Compliance Status
        if in_nfz:
            compliance = "FLIGHT_PROHIBITED"
            advisory = f"Prohibited zone violation: {restricted_name}. Immediate holding or diversion required."
        elif zone_type == "APPROVED_DRONE_CORRIDOR":
            compliance = "CLEAR_TO_OPERATE"
            advisory = f"Operating inside active certified drone flight corridor: {restricted_name}."
        elif alt > max_legal_alt:
            compliance = "AUTHORIZATION_REQUIRED"
            advisory = f"Requested altitude {alt}m exceeds 120m open ceiling. Dynamic waiver via {protocol} required."
        elif is_controlled:
            compliance = "AUTHORIZATION_REQUIRED"
            advisory = f"Controlled airspace Class {airspace_code}. Automated clearance via {protocol} recommended."
        else:
            compliance = "CLEAR_TO_OPERATE"
            advisory = f"Uncontrolled Class G airspace. Standard autonomous flight permitted up to {max_legal_alt}m AGL."

        proof_raw = f"GEOFENCE:{lat:.6f}:{lon:.6f}:{alt:.1f}:{airspace_code}:{compliance}:{fee_paid}"
        proof_hash = "0x" + hashlib.sha256(proof_raw.encode("utf-8")).hexdigest()

        return GeofenceCheckOutput(
            oracle_type="AIRSPACE_GEOFENCE_REGULATORY",
            latitude=lat,
            longitude=lon,
            altitude_agl_meters=round(alt, 1),
            airspace=AirspaceClassInfo(
                class_code=airspace_code,
                is_controlled=is_controlled,
                floor_altitude_m=floor_m,
                ceiling_altitude_m=ceil_m,
            ),
            no_fly_zone=NoFlyZoneAssessment(
                in_prohibited_zone=in_nfz,
                zone_type=zone_type,
                nearest_boundary_distance_km=round(min_dist_km, 2),
                restricted_zone_name=restricted_name,
            ),
            regulation=RegulatoryCompliance(
                max_legal_altitude_agl_m=max_legal_alt,
                remote_id_broadcast_required=remote_id,
                utm_authorization_protocol=protocol,
                compliance_status=compliance,
                advisory_notice=advisory,
            ),
            deterministic_proof_hash=proof_hash,
            settlement_network=settlement_network,
            fee_paid_usdc=fee_paid,
        )
