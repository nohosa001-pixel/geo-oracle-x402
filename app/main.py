"""
A.GRID Earth Physical Infrastructure Risk Hub (geo-oracle-x402 v3.0.0) - FastAPI Unified Hub.
Aggregates WGS84 Terrain, Micro-Weather, 5G/Starlink RF Connectivity, and live Cloud Run
Seismic & Climate Sub-Oracles for Global Physical Infrastructure (Data Centers, Ports, Mines,
Power Grids, Subsea Cables, Farms, Logistics Hubs).
"""

import json
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse, Response

from app.core.x402_verifier import (
    ORACLE_RECIPIENT_WALLET,
    SOLANA_ORACLE_VAULT,
    SOLANA_USDC_MINT,
)
from app.sync.data_registry import LiveDataRegistry
from app.sync.scheduler import DataSyncScheduler

from app.oracles.infrastructure.router import (
    CLIMATE_ORACLE_URL,
    SEISMIC_ORACLE_URL,
    router as infrastructure_router,
)
from app.oracles.rf_coverage.router import router as rf_router
from app.oracles.terrain.router import router as terrain_router
from app.oracles.weather.router import router as weather_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager: launches periodic background data sync on startup and stops on shutdown."""
    DataSyncScheduler.start()
    yield
    DataSyncScheduler.stop()


app = FastAPI(
    title="A.GRID Earth Physical Infrastructure Risk Hub (geo-oracle-x402)",
    description=(
        "Global Earth Physical Infrastructure Risk Database & Oracle Hub (x402 Multi-Chain & Solana). "
        "Synthesizes WGS84 terrain, micro-weather, 5G/Starlink connectivity redundancy, and live "
        "seismic & climate sub-oracles for AI Data Centers, Ports, Mines, Power Grids, Subsea Cables, "
        "Farms, and Logistics Hubs."
    ),
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

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
    ],
)

# Register Earth Physical Infrastructure Routers (legacy drone/robotics/insurance modules removed)
app.include_router(infrastructure_router)
app.include_router(terrain_router)
app.include_router(weather_router)
app.include_router(rf_router)


@app.get("/", tags=["Earth Infrastructure Hub"])
async def root_info():
    """Returns Earth Physical Infrastructure Risk Hub metadata and active oracle catalog."""
    return {
        "service": "geo-oracle-x402",
        "name": "A.GRID Earth Physical Infrastructure Risk Hub",
        "version": "3.0.0",
        "live_sync_daemon": "ACTIVE",
        "connected_sub_oracles": {
            "seismic": SEISMIC_ORACLE_URL,
            "climate": CLIMATE_ORACLE_URL,
        },
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
        "oracles_catalog": [
            {
                "id": "earth-infrastructure-hub",
                "name": "Earth Physical Infrastructure Risk Hub (Unified)",
                "endpoint": "POST /v1/infrastructure/assess",
                "free_preview": "POST /v1/infrastructure/preview",
                "price_usdc": "0.015",
                "description": "Unified physical risk assessment for DATA_CENTER, PORT, MINE, POWER_GRID, SUBSEA_CABLE, FARM, and LOGISTICS_HUB combining Terrain + Weather + 5G/Starlink + live Seismic & Climate sub-oracles.",
            },
            {
                "id": "terrain-oracle",
                "name": "WGS84 Geo-Terrain & Elevation Oracle",
                "endpoint": "POST /v1/terrain/analyze",
                "price_usdc": "0.005",
                "description": "WGS84 elevation, slope vectors, and surface stability scoring for physical sites.",
            },
            {
                "id": "weather-oracle",
                "name": "Site Micro-Weather & Atmospheric Oracle",
                "endpoint": "POST /v1/weather/analyze",
                "price_usdc": "0.005",
                "description": "Site-level wind fields, ambient temperature, humidity, and icing risk.",
            },
            {
                "id": "rf-coverage-oracle",
                "name": "5G/LTE & Starlink SatCom Redundancy Oracle",
                "endpoint": "POST /v1/rf/coverage",
                "price_usdc": "0.005",
                "description": "Terrestrial 5G/LTE RSRP, Starlink LEO visibility, and GNSS PDOP failover readiness.",
            },
        ],
        "standards": {
            "llms_txt": "/llms.txt",
            "robots_txt": "/robots.txt",
            "sitemap_xml": "/sitemap.xml",
            "agent_card": "/.well-known/agent-card.json",
            "x402_manifest": "/.well-known/x402.json",
            "google_ap2_manifest": "/.well-known/ap2.json",
            "openapi_docs": "/docs",
            "live_sync_telemetry": "/v1/system/sync-status",
        },
    }


@app.get("/llms.txt", response_class=PlainTextResponse, tags=["Agent Standards"])
async def serve_llms_txt():
    """Standard llms.txt descriptor for AI agents and infrastructure risk analysts."""
    return (
        "# A.GRID Earth Physical Infrastructure Risk Hub (geo-oracle-x402 v3.0.0)\n\n"
        "> Unified physical risk database and real-time hazard oracle for Earth's critical infrastructure: "
        "AI Data Centers, Ports, Mines, Power Grids, Subsea Cables, Farms, and Logistics Hubs.\n\n"
        "## Core Endpoints\n"
        "- `GET /v1/infrastructure/catalog` (Free): Supported asset classes & live sub-oracle endpoints.\n"
        "- `POST /v1/infrastructure/preview` (Free): Run a live multi-layer physical risk preview for any WGS84 coordinate.\n"
        "- `POST /v1/infrastructure/assess` (x402, 0.015 USDC): Verified assessment with deterministic proof hash.\n"
        "- `POST /v1/terrain/analyze` (x402, 0.005 USDC): WGS84 terrain elevation & slope.\n"
        "- `POST /v1/weather/analyze` (x402, 0.005 USDC): Site micro-weather & atmospheric conditions.\n"
        "- `POST /v1/rf/coverage` (x402, 0.005 USDC): 5G/LTE & Starlink LEO connectivity redundancy.\n"
    )


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
        "service": "geo-oracle-x402",
        "version": "3.0.0",
        "active_oracles": 4,
        "ecosystem": "A.GRID Earth Physical Infrastructure Risk Hub",
        "live_sync_daemon": "RUNNING",
        "connected_sub_oracles": {
            "seismic": SEISMIC_ORACLE_URL,
            "climate": CLIMATE_ORACLE_URL,
        },
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
        "message": "Full synchronization cycle executed successfully.",
        "status": LiveDataRegistry.get_sync_status(),
    }


@app.get("/.well-known/agent.json", tags=["Agent Standards"])
@app.get("/.well-known/agent-card.json", tags=["Agent Standards"])
@app.get("/.well-known/agents.json", tags=["Agent Standards"])
async def get_agent_card():
    """A2A standard agent-card.json manifest for Earth Physical Infrastructure Risk Hub."""
    return {
        "schema_version": "v1",
        "name": "geo-oracle-x402",
        "display_name": "A.GRID Earth Physical Infrastructure Risk Hub",
        "version": "3.0.0",
        "description": (
            "Evaluates real-time physical infrastructure risks for AI Data Centers, Ports, Mines, "
            "Power Grids, Subsea Cables, Farms, and Logistics Hubs by combining WGS84 terrain, "
            "micro-weather, 5G/Starlink connectivity redundancy, and live seismic & climate sub-oracles."
        ),
        "endpoints": {
            "free_catalog": "/v1/infrastructure/catalog",
            "free_assets": "/v1/infrastructure/assets",
            "free_preview": "/v1/infrastructure/preview",
            "paid_assess": "/v1/infrastructure/assess",
            "llms_txt": "/llms.txt",
            "x402_manifest": "/.well-known/x402.json",
            "sitemap_xml": "/sitemap.xml",
            "openapi": "/openapi.json",
        },
        "settlement": {
            "protocol": "x402",
            "evm_recipient": ORACLE_RECIPIENT_WALLET,
            "solana_vault": SOLANA_ORACLE_VAULT,
        },
    }


@app.get("/.well-known/ap2", tags=["Agent Standards"])
@app.get("/.well-known/ap2.json", tags=["Agent Standards"])
async def get_google_ap2_manifest():
    """Google AP2 (Agent Protocol 2) machine-readable manifest."""
    return {
        "$schema": "https://agentprotocol.ai/schemas/ap2-manifest.json",
        "name": "geo-oracle-x402",
        "display_name": "A.GRID Earth Physical Infrastructure Risk Hub",
        "version": "3.0.0",
        "recipient_address": ORACLE_RECIPIENT_WALLET,
        "solana_vault": SOLANA_ORACLE_VAULT,
    }


_GEO_CANONICAL_BASE = "https://geo-oracle-x402-7qxtp3324q-du.a.run.app"


@app.api_route("/robots.txt", methods=["GET", "HEAD"], response_class=PlainTextResponse, tags=["Agent Standards"], include_in_schema=False)
async def serve_robots_txt():
    """Crawler & AI agent discovery directives."""
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "Allow: /llms.txt\n"
        "Allow: /sitemap.xml\n"
        "Allow: /.well-known/agent-card.json\n"
        "Allow: /.well-known/x402.json\n"
        "Allow: /v1/infrastructure/catalog\n"
        "Allow: /v1/infrastructure/assets\n"
        f"Sitemap: {_GEO_CANONICAL_BASE}/sitemap.xml\n"
        f"LLMs-Txt: {_GEO_CANONICAL_BASE}/llms.txt\n"
    )


@app.api_route("/sitemap.xml", methods=["GET", "HEAD"], tags=["Agent Standards"], include_in_schema=False)
async def serve_sitemap_xml():
    """Canonical XML sitemap for search engines and AI indexers."""
    urls = [
        ("/", "1.0", "daily"),
        ("/llms.txt", "1.0", "daily"),
        ("/.well-known/agent-card.json", "0.95", "daily"),
        ("/.well-known/x402.json", "0.95", "daily"),
        ("/.well-known/ap2.json", "0.9", "weekly"),
        ("/v1/infrastructure/catalog", "0.95", "daily"),
        ("/v1/infrastructure/assets", "0.95", "daily"),
        ("/docs", "0.8", "weekly"),
        ("/health", "0.7", "hourly"),
    ]
    entries = "\n".join(
        f"  <url>\n    <loc>{_GEO_CANONICAL_BASE}{path}</loc>\n    <lastmod>2026-11-22</lastmod>\n    <changefreq>{freq}</changefreq>\n    <priority>{prio}</priority>\n  </url>"
        for path, prio, freq in urls
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{entries}\n"
        "</urlset>\n"
    )
    return Response(content=xml, media_type="application/xml")


@app.api_route("/.well-known/x402", methods=["GET", "HEAD"], tags=["Agent Standards"])
@app.api_route("/.well-known/x402.json", methods=["GET", "HEAD"], tags=["Agent Standards"])
async def get_x402_manifest():
    """Machine-readable x402 payment & pricing discovery manifest."""
    return {
        "x402Version": 1,
        "service": "geo-oracle-x402",
        "name": "A.GRID Earth Physical Infrastructure Risk Hub",
        "version": "3.0.0",
        "base_url": _GEO_CANONICAL_BASE,
        "settlement": {
            "networks": ["solana", "polygon", "base", "arbitrum", "ethereum"],
            "currency": "USDC",
            "evm_recipient": ORACLE_RECIPIENT_WALLET,
            "solana_vault": SOLANA_ORACLE_VAULT,
            "solana_usdc_mint": SOLANA_USDC_MINT,
        },
        "free_endpoints": [
            {"method": "GET", "path": "/v1/infrastructure/catalog"},
            {"method": "GET", "path": "/v1/infrastructure/assets"},
            {"method": "POST", "path": "/v1/infrastructure/preview"},
        ],
        "paid_endpoints": [
            {"method": "POST", "path": "/v1/infrastructure/assess", "price_usdc": 0.015},
            {"method": "POST", "path": "/v1/terrain/analyze", "price_usdc": 0.005},
            {"method": "POST", "path": "/v1/weather/analyze", "price_usdc": 0.005},
            {"method": "POST", "path": "/v1/rf/coverage", "price_usdc": 0.005},
        ],
    }
