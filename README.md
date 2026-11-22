# A.GRID Earth Physical Infrastructure Risk Hub (`geo-oracle-x402` v3.0.0)

> Global Earth Physical Infrastructure Risk Database & Real-Time Oracle Hub (x402 Multi-Chain & Solana). Synthesizes deterministic WGS84 terrain physics, micro-weather, 5G/Starlink connectivity redundancy, and live Cloud Run seismic & climate sub-oracles for AI Data Centers, Ports, Mines, Power Grids, Subsea Cables, Farms, and Logistics Hubs.

[![CI](https://github.com/nohosa001-pixel/geo-oracle-x402/actions/workflows/ci.yml/badge.svg)](https://github.com/nohosa001-pixel/geo-oracle-x402/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![x402 Protocol](https://img.shields.io/badge/Monetization-x402%20Multi--Chain-8247E5.svg)](https://x402.org)
[![Solana Integration](https://img.shields.io/badge/Solana-Ed25519%20SPL%20USDC-14F195.svg)](https://solana.com)
[![Polygon Network](https://img.shields.io/badge/Polygon-Chain%20ID%20137-8247E5.svg)](https://polygon.technology)
[![Base & Arbitrum](https://img.shields.io/badge/L2-Base%20%26%20Arbitrum-0052FF.svg)](https://base.org)

---

## 1. Overview & Multi-Chain Architecture

`geo-oracle-x402` v3.0.0 evaluates real-time physical infrastructure hazards across seven asset classes (`DATA_CENTER`, `PORT`, `MINE`, `POWER_GRID`, `SUBSEA_CABLE`, `FARM`, `LOGISTICS_HUB`). Every paid oracle query supports multi-chain x402 settlement across:

- **Solana Mainnet-Beta**: Ed25519 cryptographic authorization in SPL USDC (`EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`)
- **Polygon PoS (137)**: Native USDC EIP-712 structured data micropayments
- **Base L2 (8453)**: Low-gas Coinbase L2 micro-settlements
- **Arbitrum One (42161)**: High-throughput L2 micro-settlements
- **Ethereum Mainnet (1)**: Tier-1 settlement

---

## 2. Core Endpoints Catalog

| Oracle / Endpoint | Method & Path | Fee | Key Outputs |
| :--- | :--- | :---: | :--- |
| **Infrastructure Catalog** | `GET /v1/infrastructure/catalog` | `Free` | Supported asset types, live sub-oracle URLs, endpoint directory |
| **Infrastructure Risk Preview** | `POST /v1/infrastructure/preview` | `Free` | Multi-layer physical risk preview (Terrain + Weather + RF + Seismic + Climate) |
| **Infrastructure Risk Assess** | `POST /v1/infrastructure/assess` | `0.015 USDC` | Verified multi-layer assessment with `X-402-Proof-Hash` & BCBS resilience flags |
| **Geo-Terrain & Elevation** | `POST /v1/terrain/analyze` | `0.005 USDC` | WGS84 elevation, slope gradient, aspect, surface trafficability |
| **Micro-Weather & Wind** | `POST /v1/weather/analyze` | `0.005 USDC` | 3D wind vector, barometric density, EDR turbulence, icing risk |
| **RF & Starlink Coverage** | `POST /v1/rf/coverage` | `0.005 USDC` | Terrestrial 5G/LTE RSRP (dBm), Starlink LEO LoS %, GNSS PDOP |
| **Agent Discovery** | `GET /llms.txt`, `GET /.well-known/agent-card.json`, `GET /.well-known/ap2` | `Free` | Machine-readable descriptors for AI agents & A2A/AP2 discovery |

---

## 3. Quick Start

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### Run Tests

```bash
python -m pytest -v
```

### Docker (Cloud Run Ready)

```bash
docker build -t geo-oracle-x402:3.0.0 .
docker run -p 8080:8080 geo-oracle-x402:3.0.0
```

---

## 4. Agent Quickstart & cURL Examples

### Free Risk Preview (cURL)

```bash
curl -X POST http://localhost:8080/v1/infrastructure/preview \
  -H "Content-Type: application/json" \
  -d '{"asset_id":"DC-SEOUL-01","asset_type":"DATA_CENTER","latitude":37.5665,"longitude":126.9780}'
```

### End-to-End Python Agent (Free Preview → Paid x402 Assess)

```bash
python examples/quickstart_agent.py --url http://localhost:8080
```

### Live Deployment Smoke Test & Operations

- Live deployment verification: `python scripts/smoke_test_live.py --url https://<YOUR-CLOUD-RUN-URL>`
- CI/CD Cloud Run workflow: `.github/workflows/deploy-cloudrun.yml`
- Operations, Cloud Logging alerts & Redis scaling guide: `docs/OPERATIONS_GUIDE.md`
