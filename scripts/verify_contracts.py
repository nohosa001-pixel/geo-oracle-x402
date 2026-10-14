"""
Contract Verification & Green Checkmark Guide Generator for geo-oracle-x402 Suite.
Generates:
1. Standard JSON input files for Polygonscan, BaseScan, and ArbiScan.
2. Direct 1-click verification URLs for all 15 deployed contracts.
3. Pre-calculated Constructor Arguments ABI-encoded hex strings.
"""

import os
import sys
import json
from pathlib import Path
from eth_abi import encode

ROOT_DIR = Path(__file__).parent.parent
DEPLOYMENT_FILE = ROOT_DIR / "deployed_contracts_multichain.json"
VERIFICATION_DIR = ROOT_DIR / "contracts" / "verification"
VERIFICATION_DIR.mkdir(parents=True, exist_ok=True)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ORACLE_SIGNER = "0xA185B43fDD19619f99952AAed6eabf1029bF36a1"

USDC_ADDRESSES = {
    "polygon": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
    "base": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "arbitrum": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
}

EXPLORERS = {
    "polygon": "https://polygonscan.com",
    "base": "https://basescan.org",
    "arbitrum": "https://arbiscan.io"
}

CONTRACT_SOURCES = {
    "AutonomousLogisticsEscrow": "contracts/AutonomousLogisticsEscrow.sol",
    "ParametricInsurancePool": "contracts/ParametricInsurancePool.sol",
    "MachineCreditScorer": "contracts/MachineCreditScorer.sol",
    "OracleStakingManager": "contracts/OracleStakingManager.sol",
    "x402Settlement": "contracts/x402Settlement.sol"
}


def get_constructor_hex(cname: str, chain: str) -> str:
    usdc = USDC_ADDRESSES[chain]
    if cname == "AutonomousLogisticsEscrow":
        return encode(["address", "address"], [usdc, ORACLE_SIGNER]).hex()
    elif cname == "ParametricInsurancePool":
        return encode(["address"], [ORACLE_SIGNER]).hex()
    elif cname == "MachineCreditScorer":
        return encode(["address"], [ORACLE_SIGNER]).hex()
    elif cname == "OracleStakingManager":
        return encode(["address", "address"], [usdc, ORACLE_SIGNER]).hex()
    elif cname == "x402Settlement":
        return encode(["address"], [usdc]).hex()
    return ""


def generate_standard_json(cname: str):
    source_path = ROOT_DIR / CONTRACT_SOURCES[cname]
    with open(source_path, "r", encoding="utf-8") as f:
        source_content = f.read()

    std_json = {
        "language": "Solidity",
        "sources": {
            f"{cname}.sol": {
                "content": source_content
            }
        },
        "settings": {
            "optimizer": {
                "enabled": True,
                "runs": 200
            },
            "viaIR": True,
            "outputSelection": {
                "*": {
                    "*": [
                        "abi",
                        "evm.bytecode",
                        "evm.deployedBytecode",
                        "evm.methodIdentifiers",
                        "metadata"
                    ],
                    "": [
                        "ast"
                    ]
                }
            }
        }
    }
    
    out_file = VERIFICATION_DIR / f"{cname}.standard-json.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(std_json, f, indent=2)
    return out_file


def main():
    if not DEPLOYMENT_FILE.exists():
        print("❌ No deployment records found.")
        return

    with open(DEPLOYMENT_FILE, "r", encoding="utf-8") as f:
        deployments = json.load(f)

    # 1. Generate Standard-JSON files
    for cname in CONTRACT_SOURCES:
        json_file = generate_standard_json(cname)
        print(f"📄 Created Standard-JSON: {json_file.name}")

    print("\n" + "═" * 84)
    print("      BLOCK EXPLORER VERIFICATION & GREEN CHECKMARK (공식 녹색 인증) 가이드        ")
    print("═" * 84)
    print("공통 컴파일러 설정:")
    print("  • Compiler Type:    Solidity (Standard-JSON-Input) [가장 추천] 또는 Solidity (Single file)")
    print("  • Compiler Version: v0.8.20+commit.a1b79de6")
    print("  • Open Source License: MIT License (MIT)")
    print("  • Optimization:     Yes (Runs: 200)")
    print("  • viaIR:            true")

    key_map = {
        "logistics_escrow": "AutonomousLogisticsEscrow",
        "parametric_insurance_pool": "ParametricInsurancePool",
        "machine_credit_scorer": "MachineCreditScorer",
        "oracle_staking_manager": "OracleStakingManager",
        "x402_settlement": "x402Settlement"
    }

    for chain, data in deployments.items():
        if chain == "solana":
            explorer = "https://solscan.io"
            print("\n" + "─" * 84)
            print(f"🪐 [{data['network'].upper()}] - {explorer}")
            print("─" * 84)
            print(f"\n[UniversalEscrowCore]")
            print(f"  • Program ID:         {data.get('universal_escrow')}")
            print(f"  • Solscan Verify URL: {explorer}/account/{data.get('universal_escrow')}")
            print(f"  • Anchor IDL File:    contracts/verification/solana/autonomous_logistics_escrow.idl.json")
            print(f"\n[AgentPaymentVault]")
            print(f"  • Program ID:         {data.get('agent_payment_vault')}")
            print(f"  • Solscan Verify URL: {explorer}/account/{data.get('agent_payment_vault')}")
            print(f"\n[Treasury Wallet]")
            print(f"  • Wallet Address:     {data.get('treasury_wallet')}")
            print(f"  • Solscan URL:        {explorer}/account/{data.get('treasury_wallet')}")
            continue

        explorer = EXPLORERS[chain]
        print("\n" + "─" * 84)
        print(f"🌐 [{data['network'].upper()}] - {explorer}")
        print("─" * 84)

        for json_key, cname in key_map.items():
            addr = data.get(json_key)
            if not addr:
                continue
            verify_url = f"{explorer}/verifyContract?a={addr}"
            c_hex = get_constructor_hex(cname, chain)
            json_filename = f"{cname}.standard-json.json"

            print(f"\n[{cname}]")
            print(f"  • Address:            {addr}")
            print(f"  • Direct Verify URL:  {verify_url}")
            print(f"  • Standard-JSON File: contracts/verification/{json_filename}")
            print(f"  • Constructor Hex:    {c_hex}")


if __name__ == "__main__":
    main()
