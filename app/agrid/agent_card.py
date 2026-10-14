"""
A.GRID Standard Semantic Agent Card & Service Discovery Manifest Generator.
Conforms to A.GRID DePIN Physical AI Specifications and EIP-712 machine monetization.
"""

from typing import Dict, Any
from app.core.x402_verifier import (
    ORACLE_RECIPIENT_WALLET,
    POLYGON_CHAIN_ID,
    USDC_POLYGON_ADDRESS,
    SOLANA_ORACLE_VAULT,
    SOLANA_USDC_MINT,
)

def get_agrid_agent_card() -> Dict[str, Any]:
    """Generates the official A.GRID Agent Card / Semantic Manifest for geo-oracle-x402."""
    return {
        "$schema": "https://agrid.network/schemas/v1/agent-card.json",
        "agent_id": "did:agrid:polygon:geo-oracle-x402",
        "name": "A.GRID Physical AI & Autonomous Logistics Oracle Node",
        "display_name": "A.GRID Geo-Terrain, Actuarial Risk & Logistics Escrow Arbiter",
        "version": "3.0.0",
        "category": "infrastructure.physical_ai.oracle_escrow",
        "network": {
            "chain": "polygon",
            "chain_id": POLYGON_CHAIN_ID,
            "settlement_token": "USDC",
            "token_symbol": "USDC",
            "token_address": USDC_POLYGON_ADDRESS,
            "recipient_vault": ORACLE_RECIPIENT_WALLET,
            "smart_contracts": {
                "logistics_escrow": "0x402EscrowLogisticsContractAddressPolygonMainnet",
                "machine_credit_scorer": "0x402MachineCreditScorerAddressPolygonMainnet",
                "staking_manager": "0x402OracleStakingManagerAddressPolygonMainnet",
            },
        },
        "multi_chain_settlement": {
            "supported_chains": ["polygon", "solana", "base", "arbitrum", "ethereum"],
            "default_chain": "polygon",
            "solana": {
                "cluster": "mainnet-beta",
                "token": "USDC",
                "token_mint": SOLANA_USDC_MINT,
                "recipient_vault": SOLANA_ORACLE_VAULT,
                "signature_scheme": "Ed25519",
            },
            "base": {
                "chain_id": 8453,
                "token": "USDC",
                "signature_scheme": "EIP-712",
            },
            "arbitrum": {
                "chain_id": 42161,
                "token": "USDC",
                "signature_scheme": "EIP-712",
            },
            "ethereum": {
                "chain_id": 1,
                "token": "USDC",
                "signature_scheme": "EIP-712",
            },
        },
        "capabilities": [
            {
                "id": "terrain-3d-physics",
                "endpoint": "/v1/terrain/analyze",
                "fee_usdc": 0.005,
                "description": "Calculates WGS84 3D terrain elevation, slopes, aspects, and multi-robot locomotion."
            },
            {
                "id": "micro-weather-turbulence",
                "endpoint": "/v1/weather/analyze",
                "fee_usdc": 0.005,
                "description": "Provides 3D atmospheric boundary layer winds, wind shear, EDR turbulence, and VTOL flight stability."
            },
            {
                "id": "airspace-regulatory-geofence",
                "endpoint": "/v1/geofence/check",
                "fee_usdc": 0.005,
                "description": "Class A-G airspace classification, airport NFZ proximity, and dynamic NOTAM safety compliance."
            },
            {
                "id": "rf-satcom-line-of-sight",
                "endpoint": "/v1/rf/coverage",
                "fee_usdc": 0.005,
                "description": "Computes 5G/LTE path loss, Starlink LEO clearance angles, and GNSS satellite geometry."
            },
            {
                "id": "energy-optimal-3d-routing",
                "endpoint": "/v1/routing/energy-optimal",
                "fee_usdc": 0.010,
                "description": "Synthesizes kinematic 3D waypoint paths minimizing Watt-hour battery drain."
            },
            {
                "id": "logistics-poi-dispatch-arbiter",
                "endpoint": "/v1/agrid/escrow/dispatch-verify",
                "fee_usdc": 0.025,
                "description": "Evaluates full pre-flight risk and issues EIP-712 Proof of Insurability (PoI) certificate for escrow dispatch."
            },
            {
                "id": "logistics-pod-delivery-arbiter",
                "endpoint": "/v1/agrid/escrow/delivery-verify",
                "fee_usdc": 0.025,
                "description": "Verifies destination GPS coordinates, telemetry, and issues EIP-712 Proof of Delivery (PoD) for instant escrow fund release."
            },
            {
                "id": "machine-credit-evaluation",
                "endpoint": "/v1/agrid/credit/evaluate",
                "fee_usdc": 0.010,
                "description": "Computes onchain FICO-style credit score (300-850) and recommended credit line for autonomous agents."
            },
            {
                "id": "realtime-telemetry-streaming",
                "endpoint": "/v1/agrid/stream/telemetry",
                "type": "websocket",
                "description": "1Hz bidirectional telemetry streaming with active G-force, temperature, and micro-weather boundary violation alerts."
            }
        ],
        "supported_cargo_categories": [
            "MicroDelivery",
            "StandardParcel",
            "ColdChainBio",
            "HeavyMoving",
            "HighValueAsset"
        ],
        "staking_sla": {
            "node_collateral_usdc": 5000,
            "slashing_guarantee": "Immediate full cargo value compensation upon verified oracle data error"
        }
    }
