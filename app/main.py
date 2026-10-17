"""
Global Autonomous Physical AI & Insurance Oracle Suite (x402) - FastAPI Unified Hub.
Includes Background Live Data Sync Daemon for NOAA Weather, NOTAM Airspace, and SatCom Feeds.
"""

import json
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.core.x402_verifier import (
    POLYGON_CHAIN_ID,
    USDC_POLYGON_ADDRESS,
    ORACLE_RECIPIENT_WALLET,
    SOLANA_ORACLE_VAULT,
    SOLANA_USDC_MINT,
)
from app.sync.scheduler import DataSyncScheduler
from app.sync.data_registry import LiveDataRegistry

from app.oracles.terrain.router import router as terrain_router
from app.oracles.weather.router import router as weather_router
from app.oracles.geofence.router import router as geofence_router
from app.oracles.rf_coverage.router import router as rf_router
from app.oracles.energy_routing.router import router as routing_router
from app.oracles.insurance.router import router as insurance_router
from app.agrid.router import router as agrid_router
from app.agrid.agent_card import get_agrid_agent_card


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager: launches periodic background data sync on startup and stops on shutdown."""
    DataSyncScheduler.start()
    yield
    DataSyncScheduler.stop()


app = FastAPI(
    title="Autonomous Physical AI & Insurance Oracle Suite (x402 on Polygon)",
    description=(
        "Production-grade micro-oracle hub delivering deterministic spatial terrain physics, "
        "atmospheric turbulence, airspace regulatory geofencing, 5G/SatCom link margins, "
        "3D energy-optimal trajectory planning, and full-lifecycle Risk Underwriting & "
        "Parametric Smart Contract Insurance for autonomous robotics & physical AI agents. "
        "Maintains continuous background synchronization with NOAA, ICAO NOTAM, and Starlink ephemeris feeds."
    ),
    version="2.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Enable CORS for autonomous agent interop & web tooling
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-402-Payment-Required",
        "X-402-Settlement-Status",
        "X-402-Payer",
        "X-402-Proof-Hash",
        "X-402-Rejection-Reason",
        "X-Insurance-Policy-ID",
        "X-Flight-Clearance",
        "X-Claim-Verdict",
    ],
)

# Register All 6 Modular Oracle Routers
app.include_router(terrain_router)
app.include_router(weather_router)
app.include_router(geofence_router)
app.include_router(rf_router)
app.include_router(routing_router)
app.include_router(insurance_router)
app.include_router(agrid_router)


@app.get("/", tags=["Oracle Hub Info"])
async def root_info():
    """Returns general multi-oracle metadata, catalog endpoints, and protocol specifications."""
    return {
        "service": "autonomous-physical-ai-oracle-suite",
        "name": "Autonomous Physical AI & Insurance Oracle Suite (x402 Multi-Chain & Solana)",
        "version": "2.2.0",
        "live_sync_daemon": "ACTIVE (Continuous Ingestion)",
        "monetization": {
            "protocol": "x402 Multi-Chain & Solana Protocol",
            "settlement_networks": ["solana", "polygon", "base", "arbitrum", "ethereum"],
            "solana_settlement": {
                "network": "solana",
                "cluster": "mainnet-beta",
                "token": f"SPL USDC ({SOLANA_USDC_MINT})",
                "recipient_vault": SOLANA_ORACLE_VAULT,
                "signature_type": "Ed25519",
                "interactive_portal": "/solana-pay",
            },
            "evm_settlement": {
                "networks": ["Polygon (137)", "Base (8453)", "Arbitrum (42161)"],
                "token": "USDC",
                "recipient_wallet": ORACLE_RECIPIENT_WALLET,
                "signature_type": "EIP-712",
            },
        },
        "solana_pay_portal": "/solana-pay",
        "oracles_catalog": [
            {
                "id": "terrain-oracle",
                "name": "Geo-Terrain & Trafficability Oracle",
                "endpoint": "POST /v1/terrain/analyze",
                "price_usdc": "0.005",
                "description": "WGS84 elevation, slope vectors, aspect, and robotic locomotion scoring.",
            },
            {
                "id": "weather-oracle",
                "name": "Micro-Weather & Turbulence Oracle",
                "endpoint": "POST /v1/weather/analyze",
                "price_usdc": "0.005",
                "description": "3D wind fields, boundary layer shear, EDR turbulence, and VTOL stability.",
            },
            {
                "id": "geofence-oracle",
                "name": "Airspace & Regulatory Geofence Oracle",
                "endpoint": "POST /v1/geofence/check",
                "price_usdc": "0.005",
                "description": "Airspace classification (Class A-G), No-Fly Zone (NFZ), and dynamic NOTAM regulations.",
            },
            {
                "id": "rf-coverage-oracle",
                "name": "RF Line-of-Sight & SatCom Mesh Oracle",
                "endpoint": "POST /v1/rf/coverage",
                "price_usdc": "0.005",
                "description": "Terrestrial 5G/LTE path loss, Starlink/GNSS clearance angles, and link margin.",
            },
            {
                "id": "energy-routing-oracle",
                "name": "Kinematic & Energy-Optimal 3D Routing Oracle",
                "endpoint": "POST /v1/routing/energy-optimal",
                "price_usdc": "0.010",
                "description": "3D waypoint trajectory planning minimizing Watt-hour battery expenditure.",
            },
            {
                "id": "insurance-underwrite-oracle",
                "name": "Risk Underwriting & Proof of Insurability (PoI) Oracle",
                "endpoint": "POST /v1/insurance/underwrite",
                "price_usdc": "0.025",
                "description": "Synthesizes 5 physical dimensions into actuarial mission risk, dynamic premium, and Proof of Insurability clearance.",
            },
            {
                "id": "parametric-claim-oracle",
                "name": "Smart Contract Parametric Claim Adjudication Oracle",
                "endpoint": "POST /v1/insurance/claim-verify",
                "price_usdc": "0.050",
                "description": "Automated blackbox telemetry cross-check and instant onchain payout disbursement authorization.",
            },
            {
                "id": "agrid-escrow-dispatch-oracle",
                "name": "A.GRID Pre-Flight Proof of Insurability (PoI) Clearance (EVM)",
                "endpoint": "POST /v1/agrid/escrow/dispatch-verify",
                "aliases": ["POST /v1/agrid/escrow/verify-poi"],
                "price_usdc": "0.025",
                "description": "Verifies atmospheric risk, no-fly zones, and issues EIP-712 dispatch clearance proof for AutonomousLogisticsEscrow.sol.",
            },
            {
                "id": "agrid-escrow-delivery-oracle",
                "name": "A.GRID Proof of Delivery (PoD) Escrow Arbiter (EVM)",
                "endpoint": "POST /v1/agrid/escrow/delivery-verify",
                "aliases": ["POST /v1/agrid/escrow/verify-pod"],
                "price_usdc": "0.025",
                "description": "Verifies destination arrival GPS, cold-chain temperature SLAs, shock G-force, and authorizes instant on-chain fund release.",
            },
            {
                "id": "agrid-solana-dispatch-oracle",
                "name": "A.GRID Solana Anchor Escrow Dispatch (Ed25519 PoI)",
                "endpoint": "POST /v1/agrid/escrow/solana/dispatch-verify",
                "price_usdc": "0.025",
                "description": "Evaluates physical constraints and signs 64-byte Ed25519 PoI authorization proof for Solana Anchor program.",
            },
            {
                "id": "agrid-solana-delivery-oracle",
                "name": "A.GRID Solana Anchor Escrow Delivery Release (Ed25519 PoD)",
                "endpoint": "POST /v1/agrid/escrow/solana/delivery-verify",
                "price_usdc": "0.025",
                "description": "Validates physical arrival, impact shock, and cold-chain envelope, then generates 64-byte Ed25519 PoD signature for Solana SPL USDC instant release.",
            },
            {
                "id": "agrid-bvlos-compliance-oracle",
                "name": "FAA Part 108 BVLOS & EASA SORA 2.5 Airspace Compliance Audit",
                "endpoint": "POST /v1/agrid/compliance/bvlos-audit",
                "price_usdc": "0.015",
                "description": "Quantitative compliance audit against FAA Part 108 BVLOS rulemaking and EASA SORA 2.5 SAIL rating.",
            },
            {
                "id": "agrid-coldchain-compliance-oracle",
                "name": "WHO PQS & FDA 21 CFR Cold-Chain Vaccine & Bio Audit",
                "endpoint": "POST /v1/agrid/compliance/coldchain-audit",
                "price_usdc": "0.015",
                "description": "Calculates Mean Kinetic Temperature (MKT), thermal envelope excursion, and verifies pharma release criteria.",
            },
            {
                "id": "agrid-machine-credit-oracle",
                "name": "A.GRID Autonomous Machine Credit Scorer & Bond Underwriter",
                "endpoint": "POST /v1/agrid/credit/evaluate",
                "price_usdc": "0.010",
                "description": "Computes machine FICO credit score (300-850), default probability, and collateral-free loan & ABS bond tranche limits.",
            },
            {
                "id": "agrid-telemetry-stream",
                "name": "Live Telemetry Stream (1Hz Bidirectional WebSocket)",
                "endpoint": "WS /v1/agrid/stream/telemetry/{mission_id}",
                "price_usdc": "Stream (Included)",
                "description": "Real-time G-force shock, cold-chain breach, low battery, and auto-reroute telemetry stream.",
            },
        ],
        "standards": {
            "google_ap2_manifest": "/.well-known/ap2",
            "agrid_agent_card": "/.well-known/agrid.json",
            "fastmcp_spec": "/mcp/tools",
            "openapi_docs": "/docs",
            "live_sync_telemetry": "/v1/system/sync-status",
        },
    }


@app.get("/solana-pay", response_class=HTMLResponse, tags=["Solana Web3 Portal"])
async def solana_pay_portal():
    """Interactive Web3 Solana Pay & Phantom Wallet Micropayment Dashboard."""
    template_path = Path(__file__).resolve().parent / "templates" / "solana_pay.html"
    if template_path.exists():
        with open(template_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    return HTMLResponse(content="<h2>Solana Pay Template not found</h2>", status_code=404)


@app.get("/health", tags=["System & Ingestion"])
async def health_check():
    """Service liveness, readiness, and background sync probe."""
    return {
        "status": "healthy",
        "active_oracles": 15,
        "ecosystem": "A.GRID Autonomous Agent & Physical AI Logistics Grid",
        "live_sync_daemon": "RUNNING",
        "settlement_networks": ["solana", "polygon", "base", "arbitrum", "ethereum"],
        "solana_treasury_vault": SOLANA_ORACLE_VAULT,
        "evm_recipient_wallet": ORACLE_RECIPIENT_WALLET,
        "x402_verifier": "Active (Ed25519 & EIP-712)",
    }


@app.get("/v1/system/sync-status", tags=["System & Ingestion"])
async def get_sync_status():
    """Returns real-time diagnostics, timestamps, and active feeds of the Background Ingestion Daemon."""
    return LiveDataRegistry.get_sync_status()


@app.post("/v1/system/trigger-sync", tags=["System & Ingestion"])
async def trigger_force_sync():
    """Forces an immediate on-demand synchronization cycle across all data feeds."""
    await DataSyncScheduler.run_full_sync_cycle()
    return {
        "message": "Full synchronization cycle executed successfully across NOAA Weather, NOTAM Airspace, and SatCom feeds.",
        "status": LiveDataRegistry.get_sync_status(),
    }


@app.get("/.well-known/ap2", tags=["Agent Standards"])
@app.get("/.well-known/ap2.json", tags=["Agent Standards"])
async def get_google_ap2_manifest():
    """Google AP2 (Agent Protocol 2) machine-readable manifest."""
    manifest_path = Path(__file__).resolve().parent.parent / ".well-known" / "ap2.json"
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)

    return {
        "$schema": "https://agentprotocol.ai/schemas/ap2-manifest.json",
        "name": "autonomous-physical-ai-oracle-suite",
        "display_name": "Autonomous Physical AI & Insurance Oracle Suite",
        "version": "2.2.0",
        "recipient_address": ORACLE_RECIPIENT_WALLET,
    }


@app.get("/.well-known/agrid", tags=["Agent Standards"])
@app.get("/.well-known/agrid.json", tags=["Agent Standards"])
async def get_agrid_manifest():
    """A.GRID (Agent Grid) Semantic Machine Manifest & Capability Card."""
    return get_agrid_agent_card()


@app.get("/mcp/tools", tags=["Agent Standards"])
async def get_mcp_tool_spec():
    """Returns FastMCP / MCP tool specification definition."""
    spec_path = Path(__file__).resolve().parent.parent / "mcp_tool_spec.json"
    if spec_path.exists():
        with open(spec_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"tools": []}
