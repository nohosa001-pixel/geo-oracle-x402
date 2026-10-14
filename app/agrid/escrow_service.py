"""
A.GRID Logistics Escrow Arbiter Service.
Performs pre-dispatch PoI risk assessment and post-arrival PoD verification.
Generates deterministic EIP-712 signatures for AutonomousLogisticsEscrow.sol.
"""

import os
import time
import math
import hashlib
from typing import Dict, Any, Optional
from eth_account import Account
from eth_account.messages import encode_typed_data
from pydantic import BaseModel, Field

from app.core.x402_verifier import (
    POLYGON_CHAIN_ID,
    ORACLE_RECIPIENT_WALLET,
)
from app.core.solana_utils import SolanaKeypair, b58encode, b58decode, is_valid_solana_address
from app.oracles.weather.engine import WeatherEngine
from app.oracles.weather.schemas import WeatherQueryInput
from app.oracles.terrain.engine import TerrainEngine
from app.oracles.terrain.schemas import GeoCoordinateInput
from app.oracles.geofence.engine import GeofenceEngine
from app.oracles.geofence.schemas import GeofenceCheckInput


ESCROW_CONTRACT_NAME = "A.GRID-Autonomous-Logistics-Escrow"
ESCROW_CONTRACT_VERSION = "1.0.0"
ORACLE_SIGNER_PRIVATE_KEY = os.getenv("ORACLE_SIGNER_PRIVATE_KEY", "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d")

# Deterministic 32-byte seed for Solana Oracle Ed25519 Authority
SOLANA_ORACLE_SEED = os.getenv(
    "SOLANA_ORACLE_SEED", "geo402_solana_oracle_seed_32byt"
).encode("utf-8")[:32].ljust(32, b"0")
solana_oracle_keypair = SolanaKeypair.from_seed(SOLANA_ORACLE_SEED)


class DispatchVerificationRequest(BaseModel):
    mission_id: str = Field(..., description="Hex or string unique mission identifier (bytes32 hex)")
    carrier_agent: str = Field(..., description="Ethereum wallet address of the autonomous carrier agent")
    cargo_category: str = Field("StandardParcel", description="MicroDelivery, StandardParcel, ColdChainBio, HeavyMoving, HighValueAsset")
    origin_lat: float = Field(..., ge=-90.0, le=90.0)
    origin_lon: float = Field(..., ge=-180.0, le=180.0)
    dest_lat: float = Field(..., ge=-90.0, le=90.0)
    dest_lon: float = Field(..., ge=-180.0, le=180.0)
    planned_cruise_altitude_m: float = Field(60.0, ge=0.0, le=500.0)
    carrier_mass_kg: float = Field(15.0, ge=1.0)
    cargo_weight_kg: float = Field(2.5, ge=0.1)


class SolanaDispatchVerificationRequest(BaseModel):
    mission_id: str = Field(..., description="Hex or base58 or string unique mission identifier (32 bytes)")
    carrier_agent_solana: str = Field(..., description="Solana Base58 public key of the autonomous carrier agent")
    cargo_category: str = Field("ColdChainBio", description="StandardParcel, ColdChainBio, MicroDelivery")
    origin_lat: float = Field(..., ge=-90.0, le=90.0)
    origin_lon: float = Field(..., ge=-180.0, le=180.0)
    dest_lat: float = Field(..., ge=-90.0, le=90.0)
    dest_lon: float = Field(..., ge=-180.0, le=180.0)
    planned_cruise_altitude_m: float = Field(60.0, ge=0.0, le=500.0)
    carrier_mass_kg: float = Field(15.0, ge=1.0)
    cargo_weight_kg: float = Field(2.5, ge=0.1)


class DeliveryVerificationRequest(BaseModel):
    mission_id: str = Field(..., description="Hex or string mission ID")
    carrier_agent: str = Field(..., description="Carrier robot address")
    current_lat: float = Field(..., ge=-90.0, le=90.0)
    current_lon: float = Field(..., ge=-180.0, le=180.0)
    target_dest_lat: float = Field(..., ge=-90.0, le=90.0)
    target_dest_lon: float = Field(..., ge=-180.0, le=180.0)
    max_recorded_g_force: float = Field(1.2, description="Max peak acceleration experienced (G)")
    min_recorded_temp_celsius: Optional[float] = Field(None, description="Recorded min temp")
    max_recorded_temp_celsius: Optional[float] = Field(None, description="Recorded max temp")
    required_min_temp: Optional[float] = Field(None)
    required_max_temp: Optional[float] = Field(None)
    max_allowed_g_force: float = Field(2.5, description="Max allowed G force")


class SolanaDeliveryVerificationRequest(BaseModel):
    mission_id: str = Field(..., description="32-byte mission ID hex or string")
    carrier_agent_solana: str = Field(..., description="Carrier robot Solana Base58 pubkey")
    current_lat: float = Field(..., ge=-90.0, le=90.0)
    current_lon: float = Field(..., ge=-180.0, le=180.0)
    target_dest_lat: float = Field(..., ge=-90.0, le=90.0)
    target_dest_lon: float = Field(..., ge=-180.0, le=180.0)
    max_recorded_g_force: float = Field(1.2, description="Max peak acceleration experienced (G)")
    min_recorded_temp_celsius: Optional[float] = Field(None)
    max_recorded_temp_celsius: Optional[float] = Field(None)
    required_min_temp: Optional[float] = Field(None)
    required_max_temp: Optional[float] = Field(None)
    max_allowed_g_force: float = Field(2.5)


class LogisticsEscrowService:
    @staticmethod
    def _to_bytes32(val: str) -> bytes:
        if val.startswith("0x") and len(val) == 66:
            return bytes.fromhex(val[2:])
        return hashlib.sha256(val.encode("utf-8")).digest()

    @classmethod
    def verify_and_sign_dispatch(
        cls,
        req: DispatchVerificationRequest,
        escrow_contract_address: str = "0x402EscrowLogisticsContractAddressPolygonMainnet"
    ) -> Dict[str, Any]:
        """
        Synthesizes terrain, weather, and geofence along the route.
        Computes actuarial risk score and signs EIP-712 PoI certificate if safe.
        """
        mid_lat = (req.origin_lat + req.dest_lat) / 2.0
        mid_lon = (req.origin_lon + req.dest_lon) / 2.0
        alt = req.planned_cruise_altitude_m

        # 1. Weather analysis
        weather_res = WeatherEngine.analyze(
            WeatherQueryInput(latitude=mid_lat, longitude=mid_lon, altitude_agl_meters=alt)
        )
        wind_speed = weather_res.wind_vector.horizontal_speed_mps
        edr_turb = weather_res.flight_stability.eddy_dissipation_rate_edr
        vtol_stability = weather_res.flight_stability.vtol_stability_score

        # 2. Geofence Check at Dest and Origin
        gf_dest = GeofenceEngine.check(
            GeofenceCheckInput(latitude=req.dest_lat, longitude=req.dest_lon, altitude_agl_meters=alt)
        )
        gf_origin = GeofenceEngine.check(
            GeofenceCheckInput(latitude=req.origin_lat, longitude=req.origin_lon, altitude_agl_meters=alt)
        )

        in_nfz = gf_dest.no_fly_zone.in_prohibited_zone or gf_origin.no_fly_zone.in_prohibited_zone
        is_prohibited = (
            in_nfz or
            gf_dest.regulation.compliance_status == "FLIGHT_PROHIBITED" or
            gf_origin.regulation.compliance_status == "FLIGHT_PROHIBITED"
        )

        # 3. Terrain analysis
        terrain_res = TerrainEngine.analyze(
            GeoCoordinateInput(latitude=req.dest_lat, longitude=req.dest_lon)
        )
        slope_deg = terrain_res.slope_gradient_degrees

        # Actuarial Risk Score (0.0 to 1.0)
        risk = (
            (wind_speed / 25.0) * 0.35 +
            edr_turb * 0.25 +
            (slope_deg / 40.0) * 0.15 +
            (0.8 if is_prohibited else 0.05)
        )
        risk_clamped = round(min(max(risk, 0.05), 1.0), 3)
        risk_ppm = int(risk_clamped * 1_000_000)

        is_approved = (not is_prohibited) and (risk_clamped < 0.70)
        rejection_reason = None
        if is_prohibited:
            rejection_reason = f"Prohibited Airspace or No-Fly Zone breach: {gf_dest.no_fly_zone.zone_type}"
        elif risk_clamped >= 0.70:
            rejection_reason = f"Actuarial physical risk too high ({risk_clamped} >= 0.70) due to severe winds or terrain."

        if not is_approved:
            return {
                "mission_id": req.mission_id,
                "approved_for_dispatch": False,
                "risk_score": risk_clamped,
                "rejection_reason": rejection_reason,
                "poi_signature": None
            }

        valid_until = int(time.time()) + 7200  # 2 hour validity window
        mission_bytes32 = cls._to_bytes32(req.mission_id)

        # Build EIP-712 Typed Data matching AutonomousLogisticsEscrow.sol
        domain_data = {
            "name": ESCROW_CONTRACT_NAME,
            "version": ESCROW_CONTRACT_VERSION,
            "chainId": POLYGON_CHAIN_ID,
            "verifyingContract": escrow_contract_address if (escrow_contract_address.startswith("0x") and len(escrow_contract_address) == 42) else ORACLE_RECIPIENT_WALLET
        }

        message_types = {
            "ProofOfInsurability": [
                {"name": "missionId", "type": "bytes32"},
                {"name": "carrierAgent", "type": "address"},
                {"name": "riskScorePpm", "type": "uint256"},
                {"name": "validUntil", "type": "uint256"}
            ]
        }

        message_data = {
            "missionId": mission_bytes32,
            "carrierAgent": req.carrier_agent,
            "riskScorePpm": risk_ppm,
            "validUntil": valid_until
        }

        structured_data = {
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "verifyingContract", "type": "address"}
                ],
                **message_types
            },
            "primaryType": "ProofOfInsurability",
            "domain": domain_data,
            "message": message_data
        }

        signable_message = encode_typed_data(full_message=structured_data)
        signed_proof = Account.sign_message(signable_message, private_key=ORACLE_SIGNER_PRIVATE_KEY)

        return {
            "mission_id": req.mission_id,
            "approved_for_dispatch": True,
            "risk_score": risk_clamped,
            "risk_score_ppm": risk_ppm,
            "valid_until": valid_until,
            "oracle_signer": ORACLE_RECIPIENT_WALLET,
            "poi_signature": signed_proof.signature.hex(),
            "proof_hash": (getattr(signed_proof, "messageHash", None) or getattr(signed_proof, "message_hash")).hex(),
            "weather_summary": {
                "wind_speed_ms": wind_speed,
                "edr_turbulence": edr_turb,
                "vtol_stability": vtol_stability
            },
            "terrain_trafficability": {
                "elevation_m": terrain_res.elevation_meters,
                "slope_deg": slope_deg,
                "landing_score": terrain_res.trafficability.drone_landing_score
            }
        }

    @classmethod
    def verify_and_sign_delivery(
        cls,
        req: DeliveryVerificationRequest,
        escrow_contract_address: str = "0x402EscrowLogisticsContractAddressPolygonMainnet"
    ) -> Dict[str, Any]:
        """
        Validates spatial arrival (GPS distance < 25m), acceleration/shock threshold,
        and cold-chain temperature SLA. Issues EIP-712 PoD release signature.
        """
        dlat = math.radians(req.current_lat - req.target_dest_lat)
        dlon = math.radians(req.current_lon - req.target_dest_lon)
        a = (
            math.sin(dlat / 2.0) ** 2 +
            math.cos(math.radians(req.target_dest_lat)) *
            math.cos(math.radians(req.current_lat)) *
            math.sin(dlon / 2.0) ** 2
        )
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        distance_meters = 6371000.0 * c

        is_in_range = distance_meters <= 25.0
        gforce_ok = req.max_recorded_g_force <= req.max_allowed_g_force

        temp_ok = True
        temp_violation_reason = None
        if req.required_min_temp is not None and req.min_recorded_temp_celsius is not None:
            if req.min_recorded_temp_celsius < req.required_min_temp:
                temp_ok = False
                temp_violation_reason = f"Temperature dropped below min threshold ({req.min_recorded_temp_celsius:.1f}C < {req.required_min_temp:.1f}C)"
        if req.required_max_temp is not None and req.max_recorded_temp_celsius is not None:
            if req.max_recorded_temp_celsius > req.required_max_temp:
                temp_ok = False
                temp_violation_reason = f"Temperature exceeded max threshold ({req.max_recorded_temp_celsius:.1f}C > {req.required_max_temp:.1f}C)"

        is_delivered = is_in_range and gforce_ok and temp_ok
        if not is_delivered:
            fail_reasons = []
            if not is_in_range:
                fail_reasons.append(f"Carrier is {distance_meters:.1f}m away from destination (must be <= 25m).")
            if not gforce_ok:
                fail_reasons.append(f"Cargo suffered excessive impact shock ({req.max_recorded_g_force:.2f}G > {req.max_allowed_g_force:.2f}G limit).")
            if not temp_ok:
                fail_reasons.append(temp_violation_reason)

            return {
                "mission_id": req.mission_id,
                "delivery_verified": False,
                "distance_to_dest_m": round(distance_meters, 2),
                "rejection_reasons": fail_reasons,
                "pod_signature": None
            }

        completed_at = int(time.time())
        dest_lat_e7 = int(req.target_dest_lat * 1e7)
        dest_lon_e7 = int(req.target_dest_lon * 1e7)
        mission_bytes32 = cls._to_bytes32(req.mission_id)

        domain_data = {
            "name": ESCROW_CONTRACT_NAME,
            "version": ESCROW_CONTRACT_VERSION,
            "chainId": POLYGON_CHAIN_ID,
            "verifyingContract": escrow_contract_address if (escrow_contract_address.startswith("0x") and len(escrow_contract_address) == 42) else ORACLE_RECIPIENT_WALLET
        }

        message_types = {
            "ProofOfDelivery": [
                {"name": "missionId", "type": "bytes32"},
                {"name": "carrierAgent", "type": "address"},
                {"name": "destLatE7", "type": "int256"},
                {"name": "destLonE7", "type": "int256"},
                {"name": "completedAt", "type": "uint256"}
            ]
        }

        message_data = {
            "missionId": mission_bytes32,
            "carrierAgent": req.carrier_agent,
            "destLatE7": dest_lat_e7,
            "destLonE7": dest_lon_e7,
            "completedAt": completed_at
        }

        structured_data = {
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "verifyingContract", "type": "address"}
                ],
                **message_types
            },
            "primaryType": "ProofOfDelivery",
            "domain": domain_data,
            "message": message_data
        }

        signable_message = encode_typed_data(full_message=structured_data)
        signed_pod = Account.sign_message(signable_message, private_key=ORACLE_SIGNER_PRIVATE_KEY)

        return {
            "mission_id": req.mission_id,
            "delivery_verified": True,
            "distance_to_dest_m": round(distance_meters, 2),
            "completed_at": completed_at,
            "dest_lat_e7": dest_lat_e7,
            "dest_lon_e7": dest_lon_e7,
            "oracle_signer": ORACLE_RECIPIENT_WALLET,
            "pod_signature": signed_pod.signature.hex(),
            "proof_hash": (getattr(signed_pod, "messageHash", None) or getattr(signed_pod, "message_hash")).hex(),
            "status": "APPROVED_FOR_INSTANT_ESCROW_DISBURSEMENT"
        }

    @classmethod
    def verify_and_sign_dispatch_solana(
        cls,
        req: SolanaDispatchVerificationRequest,
    ) -> Dict[str, Any]:
        """
        Synthesizes terrain, weather, and geofence along the route for Solana carrier.
        Generates Ed25519 oracle signature compatible with Solana Anchor program.
        """
        # Adapt to EVM request for core risk calculation
        evm_req = DispatchVerificationRequest(
            mission_id=req.mission_id,
            carrier_agent="0x0000000000000000000000000000000000000000",
            cargo_category=req.cargo_category,
            origin_lat=req.origin_lat,
            origin_lon=req.origin_lon,
            dest_lat=req.dest_lat,
            dest_lon=req.dest_lon,
            planned_cruise_altitude_m=req.planned_cruise_altitude_m,
            carrier_mass_kg=req.carrier_mass_kg,
            cargo_weight_kg=req.cargo_weight_kg,
        )

        mid_lat = (req.origin_lat + req.dest_lat) / 2.0
        mid_lon = (req.origin_lon + req.dest_lon) / 2.0
        alt = req.planned_cruise_altitude_m

        weather_res = WeatherEngine.analyze(
            WeatherQueryInput(latitude=mid_lat, longitude=mid_lon, altitude_agl_meters=alt)
        )
        wind_speed = weather_res.wind_vector.horizontal_speed_mps
        edr_turb = weather_res.flight_stability.eddy_dissipation_rate_edr
        vtol_stability = weather_res.flight_stability.vtol_stability_score

        gf_dest = GeofenceEngine.check(
            GeofenceCheckInput(latitude=req.dest_lat, longitude=req.dest_lon, altitude_agl_meters=alt)
        )
        gf_origin = GeofenceEngine.check(
            GeofenceCheckInput(latitude=req.origin_lat, longitude=req.origin_lon, altitude_agl_meters=alt)
        )

        in_nfz = gf_dest.no_fly_zone.in_prohibited_zone or gf_origin.no_fly_zone.in_prohibited_zone
        is_prohibited = (
            in_nfz or
            gf_dest.regulation.compliance_status == "FLIGHT_PROHIBITED" or
            gf_origin.regulation.compliance_status == "FLIGHT_PROHIBITED"
        )

        terrain_res = TerrainEngine.analyze(
            GeoCoordinateInput(latitude=req.dest_lat, longitude=req.dest_lon)
        )
        slope_deg = terrain_res.slope_gradient_degrees

        risk = (
            (wind_speed / 25.0) * 0.35 +
            edr_turb * 0.25 +
            (slope_deg / 40.0) * 0.15 +
            (0.8 if is_prohibited else 0.05)
        )
        risk_clamped = round(min(max(risk, 0.05), 1.0), 3)
        risk_ppm = int(risk_clamped * 1_000_000)

        is_approved = (not is_prohibited) and (risk_clamped < 0.70)
        if not is_approved:
            return {
                "mission_id": req.mission_id,
                "approved_for_dispatch": False,
                "risk_score": risk_clamped,
                "rejection_reason": (
                    f"Prohibited Airspace: {gf_dest.no_fly_zone.zone_type}" if is_prohibited
                    else f"Physical risk too high ({risk_clamped} >= 0.70)"
                ),
                "oracle_signature": None
            }

        valid_until = int(time.time()) + 7200
        mission_bytes = cls._to_bytes32(req.mission_id)

        # Build binary payload matching Solana Anchor verify_poi_dispatch
        # Prefix: "POI:" + mission_id (32B) + risk_score_ppm (4B LE) + valid_until (8B LE)
        serialized_poi = (
            b"POI:" +
            mission_bytes +
            risk_ppm.to_bytes(4, byteorder="little", signed=False) +
            valid_until.to_bytes(8, byteorder="little", signed=True)
        )

        sig_b58 = solana_oracle_keypair.sign_message(serialized_poi)
        sig_raw = b58decode(sig_b58)
        sig_u8_array = list(sig_raw)

        return {
            "mission_id": req.mission_id,
            "carrier_agent_solana": req.carrier_agent_solana,
            "approved_for_dispatch": True,
            "risk_score": risk_clamped,
            "risk_score_ppm": risk_ppm,
            "valid_until": valid_until,
            "oracle_authority_pubkey": solana_oracle_keypair.public_key_b58,
            "oracle_signature_b58": sig_b58,
            "oracle_signature_bytes": sig_u8_array,
            "weather_summary": {
                "wind_speed_ms": wind_speed,
                "edr_turbulence": edr_turb,
                "vtol_stability": vtol_stability,
            },
            "terrain_trafficability": {
                "elevation_m": terrain_res.elevation_meters,
                "slope_deg": slope_deg,
                "landing_score": terrain_res.trafficability.drone_landing_score,
            }
        }

    @classmethod
    def verify_and_sign_delivery_solana(
        cls,
        req: SolanaDeliveryVerificationRequest,
    ) -> Dict[str, Any]:
        """
        Validates spatial arrival, acceleration/shock, and cold-chain temperature for Solana Anchor escrow.
        Signs Ed25519 PoD payload.
        """
        dlat = math.radians(req.current_lat - req.target_dest_lat)
        dlon = math.radians(req.current_lon - req.target_dest_lon)
        a = (
            math.sin(dlat / 2.0) ** 2 +
            math.cos(math.radians(req.target_dest_lat)) *
            math.cos(math.radians(req.current_lat)) *
            math.sin(dlon / 2.0) ** 2
        )
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        distance_meters = 6371000.0 * c

        is_in_range = distance_meters <= 25.0
        gforce_ok = req.max_recorded_g_force <= req.max_allowed_g_force

        temp_ok = True
        temp_violation_reason = None
        if req.required_min_temp is not None and req.min_recorded_temp_celsius is not None:
            if req.min_recorded_temp_celsius < req.required_min_temp:
                temp_ok = False
                temp_violation_reason = f"Temperature dropped below min threshold ({req.min_recorded_temp_celsius:.1f}C < {req.required_min_temp:.1f}C)"
        if req.required_max_temp is not None and req.max_recorded_temp_celsius is not None:
            if req.max_recorded_temp_celsius > req.required_max_temp:
                temp_ok = False
                temp_violation_reason = f"Temperature exceeded max threshold ({req.max_recorded_temp_celsius:.1f}C > {req.required_max_temp:.1f}C)"

        is_delivered = is_in_range and gforce_ok and temp_ok
        if not is_delivered:
            fail_reasons = []
            if not is_in_range:
                fail_reasons.append(f"Carrier is {distance_meters:.1f}m away from destination.")
            if not gforce_ok:
                fail_reasons.append(f"Excessive impact shock ({req.max_recorded_g_force:.2f}G).")
            if not temp_ok:
                fail_reasons.append(temp_violation_reason)
            return {
                "mission_id": req.mission_id,
                "delivery_verified": False,
                "distance_to_dest_m": round(distance_meters, 2),
                "rejection_reasons": fail_reasons,
                "oracle_signature": None
            }

        mission_bytes = cls._to_bytes32(req.mission_id)
        max_g_ppm = int(req.max_recorded_g_force * 1_000_000)
        dist_ppm = int(distance_meters * 1_000_000)
        temp_breached_byte = b"\x00" if temp_ok else b"\x01"

        # Build binary payload matching Solana Anchor verify_pod_and_disburse
        # Prefix: "POD:" + mission_id (32B) + max_g_ppm (4B LE) + dist_ppm (4B LE) + temp_breached (1B)
        serialized_pod = (
            b"POD:" +
            mission_bytes +
            max_g_ppm.to_bytes(4, byteorder="little", signed=False) +
            dist_ppm.to_bytes(4, byteorder="little", signed=False) +
            temp_breached_byte
        )

        sig_b58 = solana_oracle_keypair.sign_message(serialized_pod)
        sig_raw = b58decode(sig_b58)
        sig_u8_array = list(sig_raw)

        return {
            "mission_id": req.mission_id,
            "carrier_agent_solana": req.carrier_agent_solana,
            "delivery_verified": True,
            "distance_to_dest_m": round(distance_meters, 2),
            "distance_to_dest_ppm": dist_ppm,
            "max_recorded_g_force": req.max_recorded_g_force,
            "temperature_breached": not temp_ok,
            "oracle_authority_pubkey": solana_oracle_keypair.public_key_b58,
            "pod_signature_b58": sig_b58,
            "pod_signature_bytes": sig_u8_array,
            "status": "APPROVED_FOR_SOLANA_ESCROW_DISBURSEMENT"
        }

