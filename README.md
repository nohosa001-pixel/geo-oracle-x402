# A.GRID Earth Physical Infrastructure Risk MCP Server (`geo-oracle-x402` v3.0.0)

> **Model Context Protocol (MCP) Server** & Real-Time Earth Physical Infrastructure Risk Hub (x402 Multi-Chain & Solana). Exposes **5 MCP tools** over both **Streamable HTTP (`POST /mcp`)** and **Stdio (`mcp_server.py`)** combining 10 live Tier-1 Earth & Digital Infrastructure feeds (USGS ComCat, NASA EONET, Copernicus 5-pt DEM, Open-Meteo & Stull Wet-Bulb, ECMWF GloFAS Flood, PeeringDB DC/IXP, TeleGeography subsea cables, Starlink orbital physics) for AI Data Centers, Ports, Mines, Power Grids, Subsea Cables, Farms, and Logistics Hubs.

[![Glama score](https://glama.ai/mcp/servers/nohosa001-pixel/geo-oracle-x402/badges/score.svg)](https://glama.ai/mcp/servers/nohosa001-pixel/geo-oracle-x402)
[![CI](https://github.com/nohosa001-pixel/geo-oracle-x402/actions/workflows/ci.yml/badge.svg)](https://github.com/nohosa001-pixel/geo-oracle-x402/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol%202024--11--05-purple.svg)](https://modelcontextprotocol.io)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![x402 Protocol](https://img.shields.io/badge/Monetization-x402%20Multi--Chain-8247E5.svg)](https://x402.org)

---

## 1. Model Context Protocol (MCP) Server

`geo-oracle-x402` implements the **Model Context Protocol (MCP JSON-RPC 2.0, `2024-11-05`)** via:
- **Hosted Streamable HTTP MCP Endpoint**: `POST https://geo-oracle-x402-212942243360.asia-northeast3.run.app/mcp` (`initialize`, `ping`, `tools/list`, `tools/call`)
- **MCP Tool Discovery**: `GET https://geo-oracle-x402-212942243360.asia-northeast3.run.app/mcp/tools`
- **Local Stdio MCP Server (`mcp_server.py`)**: Thin JSON-RPC 2.0 stdio transport compatible with Claude Desktop, Cursor, Windsurf, and Glama.ai.

### MCP Tools Catalog

| MCP Tool Name | Fee | Description |
| :--- | :---: | :--- |
| `preview_infrastructure_risk` | `Free` | Multi-layer physical & digital infrastructure risk preview for any WGS84 coordinate combining 10 live Tier-1 feeds (USGS, NASA EONET, Copernicus 5-pt DEM, Open-Meteo & Stull Wet-Bulb, ECMWF GloFAS Flood, PeeringDB, TeleGeography subsea cables). |
| `assess_infrastructure_risk` | `0.015 USDC` (x402) | Verified physical infrastructure risk assessment returning deterministic SHA-256 `proof_hash`, BCBS resilience flags, and full `data_provenance`. |
| `get_geo_brain_status` | `Free` | Live telemetry, sequential Brier score, episodic memory stats, and GCS persistence status of the 24/7 `geo-oracle-elizaos-brain`. |
| `get_federation_mesh_status` | `Free` | Live health and routing directory across A.GRID sister MCP/x402 servers (`security-gate`, `cleanweb`, `eudr`, `minerals`). |
| `get_security_gate_status` | `Free` | 4-tier Security Gate governance status, neutralized prompt-injection threats, EU AI Act Art. 50 watermark policy, and spend guardrails. |

### Claude Desktop / Cursor MCP Configuration (`stdio`)

```json
{
  "mcpServers": {
    "geo-oracle-x402": {
      "command": "python",
      "args": ["mcp_server.py"],
      "env": {
        "GEO_ORACLE_URL": "https://geo-oracle-x402-212942243360.asia-northeast3.run.app"
      }
    }
  }
}
```

### Remote Streamable HTTP MCP Test (`cURL`)

```bash
curl -X POST https://geo-oracle-x402-212942243360.asia-northeast3.run.app/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

---

## 2. REST API & Multi-Chain x402 Endpoints

Every paid oracle query supports multi-chain x402 settlement across **Solana Mainnet-Beta (Ed25519 SPL USDC)**, **Polygon PoS (137)**, **Base L2 (8453)**, **Arbitrum One (42161)**, and **Ethereum Mainnet (1)**.

| Endpoint | Method & Path | Fee | Key Outputs |
| :--- | :--- | :---: | :--- |
| **MCP JSON-RPC 2.0** | `POST /mcp` | `Free / x402` | Standard MCP `initialize`, `tools/list`, `tools/call` |
| **MCP Tool Catalog** | `GET /mcp/tools` | `Free` | Machine-readable MCP tool schemas |
| **Infrastructure Catalog** | `GET /v1/infrastructure/catalog` | `Free` | Supported asset classes & live sub-oracles |
| **Infrastructure Risk Preview** | `POST /v1/infrastructure/preview` | `Free` | 10-layer live Tier-1 Earth & digital infrastructure risk preview |
| **Infrastructure Risk Assess** | `POST /v1/infrastructure/assess` | `0.015 USDC` | Verified assessment with `X-402-Proof-Hash` & `data_provenance` |
| **Geo-Terrain & Elevation** | `POST /v1/terrain/analyze` | `0.005 USDC` | Copernicus 5-point DEM elevation, 3D slope, aspect |
| **Micro-Weather & Wind** | `POST /v1/weather/analyze` | `0.005 USDC` | Live Open-Meteo weather, Stull wet-bulb, 3D wind vector |
| **RF & Starlink Coverage** | `POST /v1/rf/coverage` | `0.005 USDC` | Orbital-shell Starlink LoS + DEM horizon mask + GNSS PDOP |
| **elizaOS Brain & Security Gate** | `GET /v1/brain/status`, `GET /v1/brain/federation`, `GET /v1/brain/security-gate/status` | `Free` | 24/7 Cloud Scheduler learning, GCS persistence, 4-tier Security Gate |
| **Agent Discovery** | `GET /llms.txt`, `GET /.well-known/agent-card.json`, `GET /.well-known/x402.json` | `Free` | A2A, x402, and LLM discovery manifests |

---

## 3. Quick Start & Local Development

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### Run Tests (38 Tests)

```bash
python -m pytest -v
```

### Run End-to-End Agent Quickstart

```bash
python examples/quickstart_agent.py --url https://geo-oracle-x402-212942243360.asia-northeast3.run.app
```

### Docker (Cloud Run & Glama Ready)

```bash
docker build -t geo-oracle-x402:3.0.0 .
docker run -p 8080:8080 geo-oracle-x402:3.0.0
```

- Live deployment verification: `python scripts/smoke_test_live.py --url https://geo-oracle-x402-212942243360.asia-northeast3.run.app`
- CI/CD Cloud Run workflow: `.github/workflows/deploy-cloudrun.yml`
- Operations & monitoring guide: `docs/OPERATIONS_GUIDE.md`
