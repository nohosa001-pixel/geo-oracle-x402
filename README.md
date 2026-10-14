# Autonomous Physical AI & Insurance Oracle Suite (x402 Multi-Chain & Solana)

> High-performance Python FastAPI multi-oracle hub delivering deterministic WGS84 terrain physics, atmospheric micro-weather, airspace geofencing, 5G/SatCom coverage, 3D energy-optimal trajectory planning, and full-lifecycle Actuarial Risk Underwriting & Parametric Smart Contract Insurance for autonomous robotics and physical AI agents.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![x402 Protocol](https://img.shields.io/badge/Monetization-x402%20Multi--Chain-8247E5.svg)](https://x402.org)
[![Solana Integration](https://img.shields.io/badge/Solana-Ed25519%20SPL%20USDC-14F195.svg)](https://solana.com)
[![Polygon Network](https://img.shields.io/badge/Polygon-Chain%20ID%20137-8247E5.svg)](https://polygon.technology)
[![Base & Arbitrum](https://img.shields.io/badge/L2-Base%20%26%20Arbitrum-0052FF.svg)](https://base.org)
[![A.GRID Node](https://img.shields.io/badge/A.GRID-Physical%20AI%20Node-00D26A.svg)](https://agrid.network)
[![Google AP2](https://img.shields.io/badge/Agent%20Standard-Google%20AP2-4285F4.svg)](https://agentprotocol.ai)
[![FastMCP](https://img.shields.io/badge/MCP-FastMCP%20Ready-purple.svg)](https://modelcontextprotocol.io)

---

## 1. Overview & Multi-Chain Architecture

The **Autonomous Physical AI & Insurance Oracle Suite** is a unified, production-grade micro-oracle hub built for autonomous field rovers, delivery bots, quadrupeds, and VTOL drones. Every oracle query supports multi-chain settlement across:
- **Solana Mainnet-Beta**: Zero-friction Ed25519 cryptographic authorization in SPL USDC (`EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`)
- **Polygon PoS (137)**: Native USDC EIP-712 structured data micropayments
- **Base L2 (8453)**: Low-gas Coinbase L2 micro-settlements
- **Arbitrum One (42161)**: High-throughput L2 micro-settlements
- **Ethereum Mainnet (1)**: Tier-1 collateral and parametric underwriting settlement

```text
                               +-------------------------------------+
                               |      Autonomous Physical Agent      |
                               | (Delivery Drone / Rover / LLM Bot)  |
                               +------------------+------------------+
                                                  |
                                   HTTP 402 + EIP-712 Signature
                                                  v
   ================================================================================================
   |                 AUTONOMOUS PHYSICAL AI & PARAMETRIC INSURANCE ORACLE SUITE                   |
   ================================================================================================
   |  [1. Geo-Terrain]        [2. Micro-Weather]     [3. Airspace Geofence]   [4. RF & SatCom]    |
   |  • WGS84 Elevation       • 3D Wind Vector (u,v) • Airspace Class A-G     • 5G/LTE Path Loss  |
   |  • 3D Slope Normal       • Wind Shear & EDR     • No-Fly Zones (NFZ)     • Starlink Mask     |
   |  • Locomotion Scores     • Icing & Stability    • UTM Compliance         • Link Margin (dB)  |
   |                                                                                              |
   |  [5. Kinematic 3D Energy Routing]               [6. Actuarial Underwriting & Insurance]      |
   |  • 3D Waypoint Path                             • 5-Factor Actuarial Risk Synthesis (0.0~1.0)|
   |  • Watt-hour Battery Decay                      • Proof of Insurability (PoI) Certificate    |
   |  • Gravitational & Drag Work                    • Instant Blackbox Parametric Claim Payout   |
   ================================================================================================
                                                  |
                                 HTTP 200 OK + PoI Proof Hash
                                                  v
                               +------------------+------------------+
                               |     Safe Insured Autonomous Flight  |
                               +-------------------------------------+
```

---

## 2. Complete Oracle Endpoints Catalog

| # | Oracle Name | Endpoint | Fee | Key Outputs |
| :-: | :--- | :--- | :-: | :--- |
| **1** | **Geo-Terrain & Trafficability** | `POST /v1/terrain/analyze` | `0.005 USDC` | Elevation, Slope ($\theta$), Aspect ($\alpha$), Wheeled/Tracked/Quadruped/Drone Locomotion Scores |
| **2** | **Micro-Weather & Turbulence** | `POST /v1/weather/analyze` | `0.005 USDC` | 3D Wind Vector, Wind Shear Gradient, EDR Turbulence, Icing Risk, VTOL Stability Score |
| **3** | **Airspace & Regulatory Geofence** | `POST /v1/geofence/check` | `0.005 USDC` | Class A-G Airspace, Airport NFZ Proximity, 120m AGL Limit, FAA LAANC / EASA U-Space Compliance |
| **4** | **RF Line-of-Sight & SatCom Mesh** | `POST /v1/rf/coverage` | `0.005 USDC` | Terrestrial 5G/LTE RSRP (dBm), Starlink LEO Mask Angle, GNSS PDOP, Failover Recommendation |
| **5** | **Kinematic Energy-Optimal Routing** | `POST /v1/routing/energy-optimal` | `0.010 USDC` | 3D Waypoints, Gravitational Climbing Work, Aerodynamic Drag, Total Energy (Wh), Battery SoC |
| **6** | **Risk Underwriting & Insurance (PoI)** | `POST /v1/insurance/underwrite` | `0.025 USDC` | 5-Factor Actuarial Risk Score, Dynamic Micro-Premium, EIP-712 Proof of Insurability Certificate |
| **7** | **Parametric Claim Adjudication** | `POST /v1/insurance/claim-verify` | `0.050 USDC` | Automated Blackbox Telemetry Cross-Check, Fault Attribution, Onchain Smart Contract Payout Signature |
| **8** | **A.GRID Escrow Dispatch Clearance** | `POST /v1/agrid/escrow/dispatch-verify` | `0.025 USDC` | Route weather, terrain, geofence audit, EIP-712 PoI certificate to unlock escrow dispatch |
| **9** | **A.GRID Escrow Delivery & Release** | `POST /v1/agrid/escrow/delivery-verify` | `0.025 USDC` | GPS destination (<25m), shock G-force, cold-chain temp check, EIP-712 PoD for instant 3-way release |
| **10** | **Solana Escrow Dispatch (Anchor)** | `POST /v1/agrid/escrow/solana/dispatch-verify` | `0.025 USDC` | Solana Anchor 64-byte Ed25519 PoI authorization signature |
| **11** | **Solana Escrow Delivery (Anchor)** | `POST /v1/agrid/escrow/solana/delivery-verify` | `0.025 USDC` | Solana Anchor 64-byte Ed25519 PoD settlement signature (SPL USDC release) |
| **12** | **FAA Part 108 & EASA SORA 2.5 Audit** | `POST /v1/agrid/compliance/bvlos-audit` | `0.015 USDC` | DAA equipage, ground/air risk class (GRC/ARC), SAIL level, BVLOS clearance |
| **13** | **WHO PQS / FDA Cold-Chain Bio Audit** | `POST /v1/agrid/compliance/coldchain-audit` | `0.015 USDC` | Mean Kinetic Temperature (MKT), thermal envelope excursion, pharma release SLA |
| **14** | **Machine Credit Evaluation** | `POST /v1/agrid/credit/evaluate` | `0.010 USDC` | Deterministic machine credit rating (300-850), default risk, and collateral-free loan line |
| **15** | **Live Telemetry Stream (1Hz)** | `WS /v1/agrid/stream/telemetry/{mission_id}` | `Stream` | Real-time G-force shock, cold-chain breach, low battery, and auto-reroute alerts |

---

## 3. Directory Layout

```text
geo-oracle-x402/
├── app/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── x402_verifier.py          # Unified Polygon EIP-712 payment & nonce verifier
│   │   └── base_schemas.py           # Shared x402 payment schemas
│   ├── oracles/                      # 6 Modular Oracle Sub-Systems
│   │   ├── terrain/                  # 1. Geo-Terrain Oracle (0.005 USDC)
│   │   ├── weather/                  # 2. Micro-Weather Oracle (0.005 USDC)
│   │   ├── geofence/                 # 3. Airspace Geofence Oracle (0.005 USDC)
│   │   ├── rf_coverage/              # 4. RF & SatCom Coverage Oracle (0.005 USDC)
│   │   ├── energy_routing/           # 5. Energy-Optimal Routing Oracle (0.010 USDC)
│   │   └── insurance/                # 6. Actuarial Risk & Parametric Insurance Oracle (0.025~0.050 USDC)
│   ├── sync/                         # Background Live Ingestion Daemon (Open-Meteo, NOTAM, CelesTrak)
│   │   ├── data_registry.py
│   │   └── scheduler.py
│   └── main.py                       # Unified Hub Router & AP2/MCP Hub
├── contracts/                        # Smart Contracts (EVM & Solana Anchor)
│   ├── AutonomousLogisticsEscrow.sol # Universal M2M Logistics Escrow (EVM)
│   ├── MachineCreditScorer.sol       # Autonomous Agent Credit Bureau & Scoring (EVM)
│   ├── OracleStakingManager.sol      # Node Staking & Slashing Insurance (EVM)
│   ├── ParametricInsurancePool.sol   # Blackbox parametric claim payout pool
│   └── solana/
│       └── autonomous_logistics_escrow.rs # Solana Anchor Program (SPL Token Escrow)
├── .well-known/
│   ├── agrid.json                    # A.GRID Semantic Manifest & Multi-Chain Capability Card
│   └── ap2.json                      # Google Agent Protocol (AP2) manifest (7 tools)
├── mcp_tool_spec.json                # FastMCP tool schema (7 tools)
├── tests/
│   ├── test_client.py                # Payment challenge & unit integration tests
│   ├── test_oracle_suite.py          # End-to-end multi-oracle test suite (7/7 pass)
│   ├── test_agrid_suite.py           # A.GRID Escrow & Credit Bureau test suite
│   ├── test_solana_and_multichain.py # Solana Ed25519 & Multi-Chain test suite (5/5 pass)
│   └── test_future_logistics_compliance.py # FAA BVLOS, WHO ColdChain & Solana Escrow suite (5/5 pass)
├── demo_solana_and_multichain_payments.py # Live Solana (Ed25519) & EVM Multi-Chain demo
├── simulate_agrid_logistics_economy.py    # A.GRID Logistics Escrow & Machine Finance simulation
├── simulate_future_logistics_bvlos_coldchain.py # FAA BVLOS, Ultra-Cold mRNA & Solana Escrow simulation
├── live_mission_demonstration.py          # Full autonomous drone mission & insurance demo
├── Dockerfile                        # Multi-stage production container
├── requirements.txt                  # Python dependencies
├── .env.example                      # Configuration template
└── README.md
```

---

## 4. Quick Start & Local Run

### Prerequisites

- Python 3.11+
- Docker (optional)

### Installation

```bash
git clone https://github.com/autonomous-oracles/global-geo-oracle-x402.git
cd global-geo-oracle-x402
pip install -r requirements.txt
```

### Run Server

```bash
# Run locally
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Run full test suite
python -m pytest tests/test_oracle_suite.py -v
```

Interactive Swagger API docs available at [http://localhost:8000/docs](http://localhost:8000/docs).

---

## 5. Autonomous Mission Simulations & Multi-Chain Demos

```bash
# 1. Multi-Chain & Solana (Ed25519) Micro-Payment Demonstration
python demo_solana_and_multichain_payments.py

# 2. A.GRID Autonomous Logistics Escrow & Machine Credit Finance Simulation
python simulate_agrid_logistics_economy.py

# 3. 7-Step Multi-Oracle Drone Mission & Parametric Insurance Underwriting Demo
python live_mission_demonstration.py

# 4. Future Logistics BVLOS (FAA Part 108 & EASA SORA 2.5), WHO Cold-Chain & Solana Escrow Simulation
python simulate_future_logistics_bvlos_coldchain.py

# 5. Severe Weather Emergency & Instant Parametric Insurance Adjudication Simulation
python simulate_future_logistics_emergency_claim.py
```

---

## 6. Docker Deployment

```bash
# Build
docker build -t global-geo-oracle-x402 .

# Run
docker run -d -p 8000:8000 --env-file .env --name geo-oracle global-geo-oracle-x402
```

---

## 7. Standards Compliance

- **Google AP2 Protocol**: `GET /.well-known/ap2`
- **FastMCP Protocol**: `GET /mcp/tools` (Claude Desktop, Cursor, Gemini toolkits)
- **OpenAPI 3.1**: `GET /docs`

---

## 8. Verified Smart Contracts & Multi-Chain / Solscan Registry

All 5 core contracts have been deployed and verified on mainnet block explorers:

| Network | Chain ID | AutonomousLogisticsEscrow | ParametricInsurancePool | MachineCreditScorer | OracleStakingManager | x402Settlement |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Polygon PoS** | 137 | [`0x0b6f...a3ad`](https://polygonscan.com/address/0x0b6f3aeb26aCb6a6e451406503131Aaced83a3ad#code) | [`0x1a56...8B89`](https://polygonscan.com/address/0x1a56D8b8f13234d83e6F3b682ff51eacdBA58B89#code) | [`0xd816...9596`](https://polygonscan.com/address/0xd816a7c801229f2264259F414B28E92645Be9596#code) | [`0xb9a0...EEb5`](https://polygonscan.com/address/0xb9a0d0cA18bf728c23A84f8DA60541963836EEb5#code) | [`0x5478...CB80`](https://polygonscan.com/address/0x54786360Db4582AEC2435E216479FD4ff093CB80#code) |
| **Base L2** | 8453 | [`0xaA03...9cfA`](https://basescan.org/address/0xaA03fB8eD6c015858d35616F45761BcB9dE39cfA#code) | [`0x0b6f...a3ad`](https://basescan.org/address/0x0b6f3aeb26aCb6a6e451406503131Aaced83a3ad#code) | [`0x1a56...8B89`](https://basescan.org/address/0x1a56D8b8f13234d83e6F3b682ff51eacdBA58B89#code) | [`0xd816...9596`](https://basescan.org/address/0xd816a7c801229f2264259F414B28E92645Be9596#code) | [`0xb9a0...EEb5`](https://basescan.org/address/0xb9a0d0cA18bf728c23A84f8DA60541963836EEb5#code) |
| **Arbitrum One** | 42161 | [`0xaA03...9cfA`](https://arbiscan.io/address/0xaA03fB8eD6c015858d35616F45761BcB9dE39cfA#code) | [`0x0b6f...a3ad`](https://arbiscan.io/address/0x0b6f3aeb26aCb6a6e451406503131Aaced83a3ad#code) | [`0x1a56...8B89`](https://arbiscan.io/address/0x1a56D8b8f13234d83e6F3b682ff51eacdBA58B89#code) | [`0xd816...9596`](https://arbiscan.io/address/0xd816a7c801229f2264259F414B28E92645Be9596#code) | [`0xb9a0...EEb5`](https://arbiscan.io/address/0xb9a0d0cA18bf728c23A84f8DA60541963836EEb5#code) |

### Solana & Solscan Registry
- **Solana Treasury Wallet**: [`411ksMz9RHYVtVMe6RUUErzZYtrU9zzvkgzswKbqx9qp`](https://solscan.io/account/411ksMz9RHYVtVMe6RUUErzZYtrU9zzvkgzswKbqx9qp)
- **Universal Escrow Program**: [`AGR3W3R9pKxnuZGYrpaggfkbMKVrjoniLaGvi1voBFSC`](https://solscan.io/account/AGR3W3R9pKxnuZGYrpaggfkbMKVrjoniLaGvi1voBFSC)
- **Agent Payment Vault**: [`7oZ16YaazQzN6z5uA1nAZWD9oGUDXyvHwXGJLFYyWi3y`](https://solscan.io/account/7oZ16YaazQzN6z5uA1nAZWD9oGUDXyvHwXGJLFYyWi3y)
- **Anchor IDL**: `contracts/verification/solana/autonomous_logistics_escrow.idl.json`
- **Solscan Registration Guide**: `contracts/verification/solana/SOLSCAN_REGISTRATION_GUIDE.md`

---

## 9. License

MIT License. Built for autonomous physical AI agents across terrestrial and planetary robotic deployments.

