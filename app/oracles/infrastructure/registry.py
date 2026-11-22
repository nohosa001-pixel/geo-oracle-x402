"""
Curated Global Critical Physical Infrastructure Asset Registry.
Covers AI Data Centers, Maritime Ports, Critical Mineral Mines, Subsea Cable Landings,
Power Grids, and Agricultural Supply Regions.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

GLOBAL_INFRASTRUCTURE_ASSETS: Dict[str, Dict[str, Any]] = {
    "DC-ASHBURN-US": {
        "asset_id": "DC-ASHBURN-US",
        "name": "Northern Virginia AI Data Center Corridor (Ashburn)",
        "asset_type": "DATA_CENTER",
        "country": "US",
        "latitude": 39.0438,
        "longitude": -77.4874,
        "commodity": "AI_COMPUTE",
    },
    "DC-FRANKFURT-DE": {
        "asset_id": "DC-FRANKFURT-DE",
        "name": "Frankfurt DE-CIX Cloud & AI Data Center Hub",
        "asset_type": "DATA_CENTER",
        "country": "DE",
        "latitude": 50.1109,
        "longitude": 8.6821,
        "commodity": "AI_COMPUTE",
    },
    "DC-TOKYO-JP": {
        "asset_id": "DC-TOKYO-JP",
        "name": "Tokyo Bay Hyperscale AI Data Center Cluster",
        "asset_type": "DATA_CENTER",
        "country": "JP",
        "latitude": 35.6762,
        "longitude": 139.6503,
        "commodity": "AI_COMPUTE",
    },
    "DC-SINGAPORE-SG": {
        "asset_id": "DC-SINGAPORE-SG",
        "name": "Singapore Jurong West Data Center Park",
        "asset_type": "DATA_CENTER",
        "country": "SG",
        "latitude": 1.3404,
        "longitude": 103.7090,
        "commodity": "AI_COMPUTE",
    },
    "DC-SEOUL-KR": {
        "asset_id": "DC-SEOUL-KR",
        "name": "Seoul Metro Sangam/Pangyo AI Cloud Cluster",
        "asset_type": "DATA_CENTER",
        "country": "KR",
        "latitude": 37.5665,
        "longitude": 126.9780,
        "commodity": "AI_COMPUTE",
    },
    "PORT-ROTTERDAM-NL": {
        "asset_id": "PORT-ROTTERDAM-NL",
        "name": "Port of Rotterdam EU Import Gateway",
        "asset_type": "PORT",
        "country": "NL",
        "latitude": 51.9244,
        "longitude": 4.4777,
        "commodity": "MARITIME_CORRIDOR",
    },
    "PORT-BUSAN-KR": {
        "asset_id": "PORT-BUSAN-KR",
        "name": "Port of Busan New Port Transshipment Hub",
        "asset_type": "PORT",
        "country": "KR",
        "latitude": 35.0755,
        "longitude": 128.8170,
        "commodity": "MARITIME_CORRIDOR",
    },
    "PORT-PANAMA-PA": {
        "asset_id": "PORT-PANAMA-PA",
        "name": "Panama Canal Colon Maritime Corridor",
        "asset_type": "PORT",
        "country": "PA",
        "latitude": 9.1000,
        "longitude": -79.9200,
        "commodity": "MARITIME_CORRIDOR",
    },
    "MINE-CL-ATACAMA": {
        "asset_id": "MINE-CL-ATACAMA",
        "name": "Salar de Atacama Lithium Brine Basin",
        "asset_type": "MINE",
        "country": "CL",
        "latitude": -23.5000,
        "longitude": -68.2500,
        "commodity": "LITHIUM",
    },
    "MINE-KR-SANGDONG": {
        "asset_id": "MINE-KR-SANGDONG",
        "name": "Sangdong Critical Tungsten Tenement",
        "asset_type": "MINE",
        "country": "KR",
        "latitude": 37.1500,
        "longitude": 128.8330,
        "commodity": "TUNGSTEN",
    },
    "MINE-ID-MOROWALI": {
        "asset_id": "MINE-ID-MOROWALI",
        "name": "Morowali Industrial Nickel Smelting Complex",
        "asset_type": "MINE",
        "country": "ID",
        "latitude": -2.8333,
        "longitude": 122.1667,
        "commodity": "NICKEL",
    },
    "SUBSEA-MARSEILLE-FR": {
        "asset_id": "SUBSEA-MARSEILLE-FR",
        "name": "Marseille Mediterranean Subsea Cable Landing",
        "asset_type": "SUBSEA_CABLE",
        "country": "FR",
        "latitude": 43.2965,
        "longitude": 5.3698,
        "commodity": "FIBER_BACKBONE",
    },
    "SUBSEA-BUSAN-KR": {
        "asset_id": "SUBSEA-BUSAN-KR",
        "name": "Busan Trans-Pacific Subsea Cable Station",
        "asset_type": "SUBSEA_CABLE",
        "country": "KR",
        "latitude": 35.1796,
        "longitude": 129.0756,
        "commodity": "FIBER_BACKBONE",
    },
    "FARM-BR-MATOGROSSO": {
        "asset_id": "FARM-BR-MATOGROSSO",
        "name": "Mato Grosso EUDR Soybean Export Belt",
        "asset_type": "FARM",
        "country": "BR",
        "latitude": -12.5400,
        "longitude": -55.7200,
        "commodity": "SOYBEAN",
    },
}


def get_asset_by_id(asset_id: str) -> Optional[Dict[str, Any]]:
    return GLOBAL_INFRASTRUCTURE_ASSETS.get((asset_id or "").strip().upper())


def list_assets(asset_type: Optional[str] = None) -> List[Dict[str, Any]]:
    assets = list(GLOBAL_INFRASTRUCTURE_ASSETS.values())
    if asset_type:
        target = asset_type.strip().upper()
        assets = [a for a in assets if a["asset_type"] == target]
    return assets
