"""
Full Multi-Chain Deployment Script for geo-oracle-x402 Suite:
1. AutonomousLogisticsEscrow.sol (M2M Logistics Escrow)
2. ParametricInsurancePool.sol   (Instant Parametric Claim Payout Pool)
3. MachineCreditScorer.sol       (Autonomous Agent Credit Bureau & Scoring)
4. OracleStakingManager.sol      (Node Staking & Slashing Insurance)
5. x402Settlement.sol            (x402 Micropayment & EIP-712 Settlement)

Deploys and registers on:
1. Polygon Mainnet (137)
2. Base Mainnet (8453)
3. Arbitrum One (42161)
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
import solcx
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

load_dotenv()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DEPLOYMENT_RECORD_FILE = Path("deployed_contracts_multichain.json")

CHAIN_CONFIGS = {
    "polygon": {
        "name": "Polygon Mainnet",
        "chain_id": 137,
        "symbol": "POL",
        "min_balance": 0.05,
        "usdc_token": os.getenv("USDC_POLYGON_ADDRESS", "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"),
        "explorer": "https://polygonscan.com",
        "rpcs": [
            "https://polygon-bor-rpc.publicnode.com",
            "https://polygon-rpc.com",
            "https://1rpc.io/matic"
        ]
    },
    "base": {
        "name": "Base Mainnet",
        "chain_id": 8453,
        "symbol": "ETH",
        "min_balance": 0.0001,
        "usdc_token": os.getenv("USDC_BASE_ADDRESS", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"),
        "explorer": "https://basescan.org",
        "rpcs": [
            "https://mainnet.base.org",
            "https://base.llamarpc.com",
            "https://1rpc.io/base"
        ]
    },
    "arbitrum": {
        "name": "Arbitrum One",
        "chain_id": 42161,
        "symbol": "ETH",
        "min_balance": 0.0001,
        "usdc_token": os.getenv("USDC_ARBITRUM_ADDRESS", "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"),
        "explorer": "https://arbiscan.io",
        "rpcs": [
            "https://arb1.arbitrum.io/rpc",
            "https://arbitrum.llamarpc.com",
            "https://1rpc.io/arb"
        ]
    }
}


def compile_all_contracts():
    """Compiles all 5 contracts using solc 0.8.20 with via-IR."""
    print("\n📦 Compiling all 5 smart contracts with solc 0.8.20 (via-IR)...")
    solcx.install_solc("0.8.20")
    
    contract_names = [
        "AutonomousLogisticsEscrow",
        "ParametricInsurancePool",
        "MachineCreditScorer",
        "OracleStakingManager",
        "x402Settlement"
    ]
    
    standard_input = {
        "language": "Solidity",
        "sources": {f"{c}.sol": {"urls": [f"contracts/{c}.sol"]} for c in contract_names},
        "settings": {
            "optimizer": {"enabled": True, "runs": 200},
            "viaIR": True,
            "outputSelection": {"*": {"*": ["abi", "evm.bytecode"]}}
        }
    }
    compiled = solcx.compile_standard(standard_input, solc_version="0.8.20", allow_paths=["contracts"])
    
    artifacts = {}
    for name in contract_names:
        artifacts[name] = {
            "abi": compiled["contracts"][f"{name}.sol"][name]["abi"],
            "bin": compiled["contracts"][f"{name}.sol"][name]["evm"]["bytecode"]["object"]
        }
    print("✅ All 5 contracts compiled successfully!")
    return artifacts


def connect_rpc(chain_key: str):
    from web3.middleware import ExtraDataToPOAMiddleware
    config = CHAIN_CONFIGS[chain_key]
    for rpc in config["rpcs"]:
        try:
            w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 15}))
            if chain_key == "polygon":
                w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
            if w3.is_connected():
                print(f"🔗 Connected to {config['name']} via {rpc} (Block: {w3.eth.block_number})")
                return w3
        except Exception as e:
            print(f"   [WARN] RPC {rpc} failed: {e}. Trying fallback...")
    raise ConnectionError(f"Failed to connect to any RPC for {chain_key}")


def send_tx_robust(w3: Web3, account: Account, tx_dict: dict, chain_key: str):
    tx_params = dict(tx_dict)
    tx_params["from"] = account.address
    tx_params["chainId"] = CHAIN_CONFIGS[chain_key]["chain_id"]
    
    if "nonce" not in tx_params:
        tx_params["nonce"] = w3.eth.get_transaction_count(account.address, "pending")

    gas_price = w3.eth.gas_price
    try:
        fee_hist = w3.eth.fee_history(1, "latest", [50])
        base_fee = fee_hist["baseFeePerGas"][-1]
        priority_fee = w3.to_wei(0.001, "gwei") if chain_key in ("base", "arbitrum") else w3.to_wei(40, "gwei")
        tx_params["maxFeePerGas"] = int(base_fee * 2.0) + priority_fee
        tx_params["maxPriorityFeePerGas"] = priority_fee
        if "gasPrice" in tx_params:
            del tx_params["gasPrice"]
    except Exception:
        tx_params["gasPrice"] = max(int(gas_price * 1.4), 40000000000 if chain_key == "polygon" else gas_price)
        if "maxFeePerGas" in tx_params:
            del tx_params["maxFeePerGas"]
        if "maxPriorityFeePerGas" in tx_params:
            del tx_params["maxPriorityFeePerGas"]

    if "gas" not in tx_params:
        try:
            estimated = w3.eth.estimate_gas(tx_params)
            tx_params["gas"] = max(int(estimated * 1.5), 2500000)
        except Exception:
            tx_params["gas"] = 3500000

    tx_hash = None
    for attempt in range(5):
        try:
            signed = account.sign_transaction(tx_params)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            break
        except Exception as e:
            err_str = str(e)
            if any(term in err_str for term in ["in-flight", "already known", "nonce", "-32000"]):
                print(f"   [WARN] RPC busy (attempt {attempt+1}/5): {err_str[:70]}... waiting 5s")
                time.sleep(5)
                tx_params["nonce"] = w3.eth.get_transaction_count(account.address, "pending")
            else:
                raise

    print(f"   🚀 Sent Tx: {tx_hash.hex()} ... waiting for confirmation")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    if receipt.status != 1:
        raise RuntimeError(f"Transaction failed on-chain: {tx_hash.hex()}")
    print(f"   ✅ Confirmed in block {receipt.blockNumber} (Gas used: {receipt.gasUsed:,})")
    time.sleep(3)
    return receipt


def deploy_chain(chain_key: str, artifacts: dict, existing_record: dict):
    config = CHAIN_CONFIGS[chain_key]
    print("\n" + "═" * 78)
    print(f"🏛️  DEPLOYING COMPLETE GEO-ORACLE 5-CONTRACT SUITE TO {config['name'].upper()}")
    print("═" * 78)

    w3 = connect_rpc(chain_key)
    deployer_pk = os.getenv("DEPLOYER_PRIVATE_KEY") or os.getenv("GATE_PRIVATE_KEY")
    if not deployer_pk:
        raise ValueError("Missing DEPLOYER_PRIVATE_KEY in .env")
    
    account = Account.from_key(deployer_pk.strip().strip('"').strip("'"))
    
    bal = w3.eth.get_balance(account.address)
    bal_eth = float(w3.from_wei(bal, "ether"))
    print(f"👛 Deployer Address: {account.address}")
    print(f"💰 Balance: {bal_eth:.6f} {config['symbol']}")
    if bal_eth < config["min_balance"]:
        raise ValueError(f"Insufficient balance on {config['name']} ({bal_eth} < {config['min_balance']})")

    oracle_signer = os.getenv("ORACLE_RECIPIENT_WALLET") or account.address
    usdc_token = config["usdc_token"]
    print(f"🛡️ Oracle Signer: {oracle_signer}")
    print(f"💵 Canonical USDC: {usdc_token}")

    record = dict(existing_record or {})
    record["chain_id"] = config["chain_id"]
    record["network"] = config["name"]
    record["deployer"] = account.address
    record["oracle_signer"] = oracle_signer
    record["usdc_token"] = usdc_token

    # 1. AutonomousLogisticsEscrow
    escrow_addr = record.get("logistics_escrow")
    if escrow_addr and len(w3.eth.get_code(escrow_addr)) > 0:
        print(f"⚡ [1/5] AutonomousLogisticsEscrow already active: {escrow_addr}")
    else:
        print(f"\n1️⃣ [1/5] Deploying AutonomousLogisticsEscrow on {config['name']}...")
        contract = w3.eth.contract(abi=artifacts["AutonomousLogisticsEscrow"]["abi"], bytecode=artifacts["AutonomousLogisticsEscrow"]["bin"])
        tx = contract.constructor(Web3.to_checksum_address(usdc_token), Web3.to_checksum_address(oracle_signer)).build_transaction({"from": account.address, "gas": 3500000})
        rc = send_tx_robust(w3, account, tx, chain_key)
        record["logistics_escrow"] = rc.contractAddress
        record["logistics_escrow_deploy_tx"] = rc.transactionHash.hex()
        print(f"🎉 Deployed: {rc.contractAddress} ({config['explorer']}/address/{rc.contractAddress})")

    # 2. ParametricInsurancePool
    ins_addr = record.get("parametric_insurance_pool")
    if ins_addr and len(w3.eth.get_code(ins_addr)) > 0:
        print(f"⚡ [2/5] ParametricInsurancePool already active: {ins_addr}")
    else:
        print(f"\n2️⃣ [2/5] Deploying ParametricInsurancePool on {config['name']}...")
        contract = w3.eth.contract(abi=artifacts["ParametricInsurancePool"]["abi"], bytecode=artifacts["ParametricInsurancePool"]["bin"])
        tx = contract.constructor(Web3.to_checksum_address(oracle_signer)).build_transaction({"from": account.address, "gas": 2500000})
        rc = send_tx_robust(w3, account, tx, chain_key)
        record["parametric_insurance_pool"] = rc.contractAddress
        record["parametric_insurance_pool_deploy_tx"] = rc.transactionHash.hex()
        print(f"🎉 Deployed: {rc.contractAddress} ({config['explorer']}/address/{rc.contractAddress})")

    # 3. MachineCreditScorer
    credit_addr = record.get("machine_credit_scorer")
    if credit_addr and len(w3.eth.get_code(credit_addr)) > 0:
        print(f"⚡ [3/5] MachineCreditScorer already active: {credit_addr}")
    else:
        print(f"\n3️⃣ [3/5] Deploying MachineCreditScorer on {config['name']}...")
        contract = w3.eth.contract(abi=artifacts["MachineCreditScorer"]["abi"], bytecode=artifacts["MachineCreditScorer"]["bin"])
        tx = contract.constructor(Web3.to_checksum_address(oracle_signer)).build_transaction({"from": account.address, "gas": 2500000})
        rc = send_tx_robust(w3, account, tx, chain_key)
        record["machine_credit_scorer"] = rc.contractAddress
        record["machine_credit_scorer_deploy_tx"] = rc.transactionHash.hex()
        print(f"🎉 Deployed: {rc.contractAddress} ({config['explorer']}/address/{rc.contractAddress})")

    # 4. OracleStakingManager
    staking_addr = record.get("oracle_staking_manager")
    if staking_addr and len(w3.eth.get_code(staking_addr)) > 0:
        print(f"⚡ [4/5] OracleStakingManager already active: {staking_addr}")
    else:
        print(f"\n4️⃣ [4/5] Deploying OracleStakingManager on {config['name']}...")
        contract = w3.eth.contract(abi=artifacts["OracleStakingManager"]["abi"], bytecode=artifacts["OracleStakingManager"]["bin"])
        tx = contract.constructor(Web3.to_checksum_address(usdc_token), Web3.to_checksum_address(account.address)).build_transaction({"from": account.address, "gas": 2500000})
        rc = send_tx_robust(w3, account, tx, chain_key)
        record["oracle_staking_manager"] = rc.contractAddress
        record["oracle_staking_manager_deploy_tx"] = rc.transactionHash.hex()
        print(f"🎉 Deployed: {rc.contractAddress} ({config['explorer']}/address/{rc.contractAddress})")

    # 5. x402Settlement
    settlement_addr = record.get("x402_settlement")
    if settlement_addr and len(w3.eth.get_code(settlement_addr)) > 0:
        print(f"⚡ [5/5] x402Settlement already active: {settlement_addr}")
    else:
        print(f"\n5️⃣ [5/5] Deploying x402Settlement on {config['name']}...")
        contract = w3.eth.contract(abi=artifacts["x402Settlement"]["abi"], bytecode=artifacts["x402Settlement"]["bin"])
        tx = contract.constructor(Web3.to_checksum_address(usdc_token)).build_transaction({"from": account.address, "gas": 2500000})
        rc = send_tx_robust(w3, account, tx, chain_key)
        record["x402_settlement"] = rc.contractAddress
        record["x402_settlement_deploy_tx"] = rc.transactionHash.hex()
        print(f"🎉 Deployed: {rc.contractAddress} ({config['explorer']}/address/{rc.contractAddress})")

    record["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return record


def main():
    parser = argparse.ArgumentParser(description="Multi-Chain Deployer for geo-oracle-x402 Complete Suite")
    parser.add_argument("--chain", choices=["polygon", "base", "arbitrum"], help="Target chain")
    parser.add_argument("--all", action="store_true", help="Deploy to all 3 chains")
    args = parser.parse_args()

    if not args.chain and not args.all:
        parser.print_help()
        sys.exit(1)

    artifacts = compile_all_contracts()

    records = {}
    if DEPLOYMENT_RECORD_FILE.exists():
        try:
            with open(DEPLOYMENT_RECORD_FILE, "r", encoding="utf-8") as f:
                records = json.load(f)
        except Exception:
            records = {}

    targets = ["polygon", "base", "arbitrum"] if args.all else [args.chain]
    for target in targets:
        existing = records.get(target, {})
        rec = deploy_chain(target, artifacts, existing)
        records[target] = rec
        with open(DEPLOYMENT_RECORD_FILE, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)
        print(f"💾 Saved deployment record for {target} to {DEPLOYMENT_RECORD_FILE}")

    print("\n" + "═" * 78)
    print("🏆 COMPLETE 5-CONTRACT MULTI-CHAIN SUITE DEPLOYMENT FINISHED!")
    print("═" * 78)
    for chain_key, rec in records.items():
        print(f"\n[{rec['network']}]")
        print(f"  • Logistics Escrow:    {rec.get('logistics_escrow')}")
        print(f"  • Parametric Insurance:{rec.get('parametric_insurance_pool')}")
        print(f"  • Machine Credit:      {rec.get('machine_credit_scorer')}")
        print(f"  • Oracle Staking:      {rec.get('oracle_staking_manager')}")
        print(f"  • x402 Settlement:     {rec.get('x402_settlement')}")


if __name__ == "__main__":
    main()
