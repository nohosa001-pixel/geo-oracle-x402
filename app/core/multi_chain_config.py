"""
Multi-Chain Settlement Configurations for x402 Micropayments & A.GRID Ecosystem.
Provides specifications for Polygon, Solana, Base, Arbitrum, and Ethereum mainnets.
"""

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

# Oracle Recipient Wallets
EVM_RECIPIENT_WALLET = os.getenv("ORACLE_RECIPIENT_WALLET", "0xA185B43fDD19619f99952AAed6eabf1029bF36a1")
SOLANA_ORACLE_VAULT = os.getenv(
    "SOLANA_ORACLE_VAULT", "Geo402OracleVaultSolanaMainnetBeta11111111111"
)

# Canonical Multi-Chain Specifications
SUPPORTED_NETWORKS: Dict[str, Dict[str, Any]] = {
    "polygon": {
        "network": "polygon",
        "type": "evm",
        "display_name": "Polygon",
        "chain_id": int(os.getenv("POLYGON_CHAIN_ID", "137")),
        "cluster": None,
        "token_symbol": "USDC",
        "token_address": os.getenv("USDC_POLYGON_ADDRESS", "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"),
        "recipient_address": EVM_RECIPIENT_WALLET,
        "signature_standard": "eip712",
        "decimals": 6,
        "facilitator_url": "https://facilitator.x402.org/v1/verify",
        "block_explorer": "https://polygonscan.com",
    },
    "solana": {
        "network": "solana",
        "type": "svm",
        "display_name": "Solana Mainnet-Beta",
        "chain_id": None,
        "cluster": os.getenv("SOLANA_CLUSTER", "mainnet-beta"),
        "token_symbol": "USDC",
        "token_address": os.getenv("SOLANA_USDC_MINT", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"),
        "recipient_address": SOLANA_ORACLE_VAULT,
        "universal_escrow_program": "AGR3W3R9pKxnuZGYrpaggfkbMKVrjoniLaGvi1voBFSC",
        "agent_payment_vault_program": "7oZ16YaazQzN6z5uA1nAZWD9oGUDXyvHwXGJLFYyWi3y",
        "signature_standard": "ed25519",
        "decimals": 6,
        "facilitator_url": "https://facilitator.x402.org/v1/verify-solana",
        "block_explorer": "https://solscan.io",
    },
    "base": {
        "network": "base",
        "type": "evm",
        "display_name": "Base L2 Mainnet",
        "chain_id": int(os.getenv("BASE_CHAIN_ID", "8453")),
        "cluster": None,
        "token_symbol": "USDC",
        "token_address": os.getenv("USDC_BASE_ADDRESS", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"),
        "recipient_address": EVM_RECIPIENT_WALLET,
        "signature_standard": "eip712",
        "decimals": 6,
        "facilitator_url": "https://facilitator.x402.org/v1/verify",
        "block_explorer": "https://basescan.org",
    },
    "arbitrum": {
        "network": "arbitrum",
        "type": "evm",
        "display_name": "Arbitrum One Mainnet",
        "chain_id": int(os.getenv("ARBITRUM_CHAIN_ID", "42161")),
        "cluster": None,
        "token_symbol": "USDC",
        "token_address": os.getenv("USDC_ARBITRUM_ADDRESS", "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"),
        "recipient_address": EVM_RECIPIENT_WALLET,
        "signature_standard": "eip712",
        "decimals": 6,
        "facilitator_url": "https://facilitator.x402.org/v1/verify",
        "block_explorer": "https://arbiscan.io",
    },
    "ethereum": {
        "network": "ethereum",
        "type": "evm",
        "display_name": "Ethereum Mainnet",
        "chain_id": int(os.getenv("ETHEREUM_CHAIN_ID", "1")),
        "cluster": None,
        "token_symbol": "USDC",
        "token_address": os.getenv("USDC_ETHEREUM_ADDRESS", "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"),
        "recipient_address": EVM_RECIPIENT_WALLET,
        "signature_standard": "eip712",
        "decimals": 6,
        "facilitator_url": "https://facilitator.x402.org/v1/verify",
        "block_explorer": "https://etherscan.io",
    },
}

DEFAULT_NETWORK = os.getenv("DEFAULT_SETTLEMENT_NETWORK", "polygon").lower()


def get_network_config(network_name: Optional[str] = None) -> Dict[str, Any]:
    """Resolves network configuration by name, falling back to default network (Polygon)."""
    if not network_name:
        return SUPPORTED_NETWORKS.get(DEFAULT_NETWORK, SUPPORTED_NETWORKS["polygon"])
    clean_name = network_name.strip().lower()
    if clean_name in ["sol", "solana-mainnet", "solana-mainnet-beta"]:
        clean_name = "solana"
    return SUPPORTED_NETWORKS.get(clean_name, SUPPORTED_NETWORKS["polygon"])
