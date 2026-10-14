"""
Shared Base Schemas for x402 Payment Protocol & Oracle Metadata.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class X402PaymentRequirement(BaseModel):
    """Returned when an endpoint requires HTTP 402 payment."""
    protocol: str = Field(default="x402", description="Payment protocol standard")
    version: str = Field(default="1.0", description="Protocol version")
    network: str = Field(default="polygon", description="Blockchain network (polygon, solana, base, arbitrum, ethereum)")
    chain_id: Optional[int] = Field(default=137, description="EVM Chain ID (137 for Polygon, None for Solana)")
    cluster: Optional[str] = Field(default=None, description="Solana cluster (e.g. mainnet-beta)")
    token_symbol: str = Field(default="USDC", description="Payment token symbol")
    token_address: str = Field(default="0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", description="USDC contract address or SPL token mint")
    price_usdc: str = Field(default="0.005", description="Price in USDC per call")
    price_units: str = Field(default="5000", description="Raw token atomic units (6 decimals)")
    recipient_address: str = Field(..., description="Oracle creator vault wallet address (EVM 0x or Solana Base58)")
    facilitator_url: Optional[str] = Field(default="https://facilitator.x402.org/v1/verify")
    nonce: str = Field(..., description="Unique cryptographic replay-prevention challenge nonce")
    valid_until_timestamp: int = Field(..., description="Unix epoch timestamp when challenge expires")
    message: str = Field(..., description="Human and machine readable payment prompt")
    rejection_reason: Optional[str] = Field(default=None, description="Reason if previous signature was rejected")
    supported_networks: List[str] = Field(
        default_factory=lambda: ["polygon", "solana", "base", "arbitrum", "ethereum"],
        description="List of supported multi-chain settlement networks",
    )
    multi_chain_options: Optional[Dict[str, Dict[str, Any]]] = Field(
        default=None,
        description="Available multi-chain configurations (Solana, Base, Arbitrum, Ethereum, Polygon)",
    )


class X402PaymentPayload(BaseModel):
    """Payload contained inside the `X-402-Signature` header."""
    payer_address: str = Field(..., description="Signer wallet address (0x EVM or Base58 Solana)")
    signature: str = Field(..., description="EIP-712/EIP-191 hex signature or Solana Base58 Ed25519 signature")
    nonce: str = Field(..., description="Nonce that was signed")
    timestamp: int = Field(..., description="Signing unix epoch timestamp")
    amount_usdc: str = Field(default="0.005", description="Amount authorized")
    type: str = Field(default="eip712", description="Signature standard (eip712, personal_sign, or ed25519)")
    network: Optional[str] = Field(default=None, description="Settlement network (polygon, solana, base, arbitrum, ethereum)")

