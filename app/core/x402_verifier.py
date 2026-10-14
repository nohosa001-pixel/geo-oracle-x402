"""
x402 Multi-Chain & Solana Payment Protocol Verifier.
Supports Polygon, Solana, Base, Arbitrum, and Ethereum USDC micropayments.
Implements HTTP 402 Multi-Chain Challenge Generation, EIP-712/EIP-191 EVM verification,
and Solana Ed25519 cryptographic authorization with anti-replay protection.
"""

import os
import time
import json
import secrets
from typing import Optional, Dict, Any, Tuple
from dotenv import load_dotenv
from eth_account import Account
from eth_account.messages import encode_defunct, encode_typed_data

from app.core.base_schemas import X402PaymentRequirement
from app.core.multi_chain_config import (
    SUPPORTED_NETWORKS,
    DEFAULT_NETWORK,
    EVM_RECIPIENT_WALLET,
    SOLANA_ORACLE_VAULT,
    get_network_config,
)
from app.core.solana_utils import (
    SolanaVerifier,
    is_valid_solana_address,
)

load_dotenv()

# Backwards compatible exports
POLYGON_CHAIN_ID = int(os.getenv("POLYGON_CHAIN_ID", "137"))
USDC_POLYGON_ADDRESS = os.getenv("USDC_POLYGON_ADDRESS", "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359")
ORACLE_RECIPIENT_WALLET = EVM_RECIPIENT_WALLET
DEFAULT_MICRO_PRICE_USDC = os.getenv("MICRO_PRICE_USDC", "0.005")
CHALLENGE_EXPIRY_SECONDS = int(os.getenv("CHALLENGE_EXPIRY_SECONDS", "300"))
SOLANA_USDC_MINT = os.getenv("SOLANA_USDC_MINT", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")

# In-memory storage for active nonces and consumed nonces
_ACTIVE_NONCES: Dict[str, Dict[str, Any]] = {}
_CONSUMED_NONCES: set = set()


class X402Verifier:
    """
    Multi-Chain x402 Payment Protocol Verifier.
    Handles cryptographic micro-settlements across Polygon, Solana, Base, Arbitrum, and Ethereum.
    """

    @classmethod
    def generate_challenge(
        cls,
        price_usdc: str = DEFAULT_MICRO_PRICE_USDC,
        oracle_name: str = "Physical AI Oracle",
        preferred_network: Optional[str] = None,
    ) -> X402PaymentRequirement:
        """
        Creates a fresh, cryptographically secure payment challenge nonce
        tailored to the requested network (e.g. 'solana', 'polygon', 'base', 'arbitrum', 'ethereum').
        """
        net_cfg = get_network_config(preferred_network)
        nonce = f"x402_{secrets.token_hex(16)}"
        expiry = int(time.time()) + CHALLENGE_EXPIRY_SECONDS

        # Clean expired nonces
        now = int(time.time())
        expired_keys = [k for k, meta in _ACTIVE_NONCES.items() if meta.get("expiry", 0) < now]
        for k in expired_keys:
            _ACTIVE_NONCES.pop(k, None)

        price_float = float(price_usdc)
        price_units = str(int(price_float * (10 ** net_cfg.get("decimals", 6))))

        _ACTIVE_NONCES[nonce] = {
            "expiry": expiry,
            "price_usdc": price_usdc,
            "oracle_name": oracle_name,
            "network": net_cfg["network"],
        }

        network_name = net_cfg["network"]
        display_net = net_cfg["display_name"]
        msg = f"Payment of {price_usdc} USDC on {display_net} is required to unlock {oracle_name} output."

        return X402PaymentRequirement(
            protocol="x402",
            version="1.0",
            network=network_name,
            chain_id=net_cfg.get("chain_id"),
            cluster=net_cfg.get("cluster"),
            token_symbol="USDC",
            token_address=net_cfg["token_address"],
            price_usdc=price_usdc,
            price_units=price_units,
            recipient_address=net_cfg["recipient_address"],
            facilitator_url=net_cfg.get("facilitator_url", "https://facilitator.x402.org/v1/verify"),
            nonce=nonce,
            valid_until_timestamp=expiry,
            message=msg,
            supported_networks=list(SUPPORTED_NETWORKS.keys()),
            multi_chain_options={
                k: {
                    "network": v["network"],
                    "chain_id": v["chain_id"],
                    "cluster": v["cluster"],
                    "token_symbol": v["token_symbol"],
                    "token_address": v["token_address"],
                    "recipient_address": v["recipient_address"],
                    "signature_standard": v["signature_standard"],
                }
                for k, v in SUPPORTED_NETWORKS.items()
            },
        )

    @classmethod
    def build_eip712_structure(
        cls,
        nonce: str,
        timestamp: int,
        amount: str = DEFAULT_MICRO_PRICE_USDC,
        oracle_name: str = "Physical AI Oracle",
        network: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Constructs the EIP-712 structured data schema for EVM x402 micropayment authorization.
        Supports Polygon, Base, Arbitrum, and Ethereum.
        """
        net_cfg = get_network_config(network)
        chain_id = net_cfg.get("chain_id") or POLYGON_CHAIN_ID
        token_address = net_cfg.get("token_address") or USDC_POLYGON_ADDRESS
        recipient = net_cfg.get("recipient_address") or ORACLE_RECIPIENT_WALLET

        return {
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "verifyingContract", "type": "address"},
                ],
                "MicroOraclePayment": [
                    {"name": "recipient", "type": "address"},
                    {"name": "token", "type": "address"},
                    {"name": "amount", "type": "string"},
                    {"name": "nonce", "type": "string"},
                    {"name": "timestamp", "type": "uint256"},
                ],
            },
            "primaryType": "MicroOraclePayment",
            "domain": {
                "name": "Global Autonomous Physical AI Oracle Suite",
                "version": "1",
                "chainId": chain_id,
                "verifyingContract": token_address,
            },
            "message": {
                "recipient": recipient,
                "token": token_address,
                "amount": amount,
                "nonce": nonce,
                "timestamp": timestamp,
            },
        }

    @classmethod
    def format_plain_message(
        cls,
        nonce: str,
        timestamp: int,
        amount: str = DEFAULT_MICRO_PRICE_USDC,
        network: Optional[str] = None,
    ) -> str:
        """
        Standard plain-text format for EIP-191 personal_sign fallback.
        """
        net_cfg = get_network_config(network)
        chain_id = net_cfg.get("chain_id") or POLYGON_CHAIN_ID
        token_addr = net_cfg.get("token_address") or USDC_POLYGON_ADDRESS
        recipient = net_cfg.get("recipient_address") or ORACLE_RECIPIENT_WALLET
        net_name = net_cfg.get("display_name", "Polygon")

        return (
            f"x402-payment-auth\n"
            f"Network: {net_name} ({chain_id})\n"
            f"Recipient: {recipient}\n"
            f"Token: USDC ({token_addr})\n"
            f"Amount: {amount} USDC\n"
            f"Nonce: {nonce}\n"
            f"Timestamp: {timestamp}"
        )

    @classmethod
    def format_solana_message(
        cls,
        nonce: str,
        timestamp: int,
        amount: str = DEFAULT_MICRO_PRICE_USDC,
    ) -> str:
        """
        Standard format for Solana Ed25519 micropayment authorization.
        """
        sol_cfg = SUPPORTED_NETWORKS["solana"]
        return SolanaVerifier.format_auth_message(
            nonce=nonce,
            timestamp=timestamp,
            amount_usdc=amount,
            recipient_vault=sol_cfg["recipient_address"],
            token_mint=sol_cfg["token_address"],
            cluster=sol_cfg.get("cluster", "mainnet-beta"),
        )

    @classmethod
    def verify_payment_header(
        cls,
        x402_header: Optional[str],
        expected_price_usdc: str = DEFAULT_MICRO_PRICE_USDC,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Parses and cryptographically verifies the `X-402-Signature` or `Authorization` header.
        Dynamically routes between EVM (Polygon, Base, Arbitrum, Ethereum) EIP-712/EIP-191
        and Solana Ed25519 verification.
        """
        if not x402_header:
            return False, "Missing X-402-Signature header or payment authorization", None

        raw_content = x402_header.strip()
        if raw_content.startswith("Bearer "):
            raw_content = raw_content[7:].strip()
        if raw_content.startswith("x402:"):
            raw_content = raw_content[5:].strip()

        try:
            payload_data = json.loads(raw_content)
        except Exception:
            return False, "Invalid JSON in X-402-Signature header", None

        payer_address = payload_data.get("payer_address")
        signature = payload_data.get("signature")
        nonce = payload_data.get("nonce")
        timestamp = payload_data.get("timestamp")
        amount = payload_data.get("amount_usdc", expected_price_usdc)
        sig_type = payload_data.get("type", "eip712").lower()
        network = payload_data.get("network")

        if not all([payer_address, signature, nonce, timestamp]):
            return False, "Incomplete payment payload: payer_address, signature, nonce, and timestamp are required", None

        # Check replay prevention
        if nonce in _CONSUMED_NONCES:
            return False, f"Nonce {nonce} has already been consumed (replay prevention)", None

        if nonce not in _ACTIVE_NONCES:
            if not nonce.startswith("x402_"):
                return False, f"Invalid or unrecognized challenge nonce: {nonce}", None
        else:
            meta = _ACTIVE_NONCES[nonce]
            if time.time() > meta["expiry"]:
                return False, "Payment challenge nonce has expired", None

        # Verify timestamp freshness (300s TTL window, 60s future clock skew allowance)
        try:
            ts_int = int(timestamp)
            current_time = int(time.time())
            if current_time - ts_int > 300:
                return False, f"Signature timestamp expired (age: {current_time - ts_int}s > 300s limit)", None
            if ts_int - current_time > 60:
                return False, "Signature timestamp is too far in the future (clock skew > 60s)", None
        except (ValueError, TypeError):
            return False, "Invalid timestamp format", None

        # Verify amount sufficiency
        try:
            if float(amount) < float(expected_price_usdc):
                return False, f"Insufficient payment amount: required {expected_price_usdc} USDC, provided {amount} USDC", None
        except ValueError:
            return False, "Invalid numeric format for amount_usdc", None

        # Determine target network & execution environment
        is_solana = False
        if network and network.lower() in ["solana", "sol"]:
            is_solana = True
        elif sig_type == "ed25519":
            is_solana = True
        elif not payer_address.startswith("0x") and is_valid_solana_address(payer_address):
            is_solana = True

        # =========================================================================
        # 1. SOLANA ED25519 VERIFICATION BRANCH
        # =========================================================================
        if is_solana:
            sol_cfg = SUPPORTED_NETWORKS["solana"]
            # Generate deterministic canonical Solana message
            canonical_msg = cls.format_solana_message(nonce=nonce, timestamp=ts_int, amount=str(amount))
            is_valid, err_msg = SolanaVerifier.verify_signature(
                public_key_b58=payer_address,
                signature_b58=signature,
                message=canonical_msg.encode("utf-8"),
            )

            # Fallback to plain message if canonical check failed
            if not is_valid:
                plain_msg = cls.format_plain_message(nonce=nonce, timestamp=ts_int, amount=str(amount), network="solana")
                is_valid2, _ = SolanaVerifier.verify_signature(
                    public_key_b58=payer_address,
                    signature_b58=signature,
                    message=plain_msg.encode("utf-8"),
                )
                if is_valid2:
                    is_valid = True

            if not is_valid:
                return False, f"Solana authorization rejected: {err_msg}", None

            # Mark nonce consumed
            _CONSUMED_NONCES.add(nonce)
            _ACTIVE_NONCES.pop(nonce, None)

            settlement_metadata = {
                "payer": payer_address,
                "recipient": sol_cfg["recipient_address"],
                "amount_usdc": amount,
                "network": "Solana",
                "cluster": sol_cfg["cluster"],
                "token_mint": sol_cfg["token_address"],
                "signature_type": "Ed25519",
                "nonce": nonce,
                "settled_at": int(time.time()),
            }
            return True, "Payment verified successfully on Solana", settlement_metadata

        # =========================================================================
        # 2. EVM MULTI-CHAIN VERIFICATION BRANCH (Polygon, Base, Arbitrum, Ethereum)
        # =========================================================================
        target_network = (network or "polygon").lower()
        net_cfg = get_network_config(target_network)
        recovered_address = None

        # 2-A. EIP-712 typed structured data recovery
        if sig_type == "eip712":
            try:
                typed_data = cls.build_eip712_structure(
                    nonce=nonce,
                    timestamp=ts_int,
                    amount=amount,
                    network=target_network,
                )
                recovered_address = Account.recover_message(
                    encode_typed_data(full_message=typed_data),
                    signature=signature,
                )
            except Exception:
                pass

        # 2-B. Fallback to EIP-191 personal_sign recovery
        if not recovered_address:
            try:
                plain_msg = cls.format_plain_message(
                    nonce=nonce,
                    timestamp=ts_int,
                    amount=amount,
                    network=target_network,
                )
                recovered_address = Account.recover_message(
                    encode_defunct(text=plain_msg),
                    signature=signature,
                )
            except Exception as e:
                return False, f"EVM signature recovery failed: {str(e)}", None

        if not recovered_address or recovered_address.lower() != payer_address.lower():
            return (
                False,
                f"Signature mismatch: recovered signer {recovered_address} does not match declared payer {payer_address}",
                None,
            )

        # Mark nonce as consumed
        _CONSUMED_NONCES.add(nonce)
        _ACTIVE_NONCES.pop(nonce, None)

        settlement_metadata = {
            "payer": payer_address,
            "recipient": net_cfg["recipient_address"],
            "amount_usdc": amount,
            "network": net_cfg["display_name"],
            "chain_id": net_cfg["chain_id"],
            "token_address": net_cfg["token_address"],
            "signature_type": "EIP-712" if sig_type == "eip712" else "EIP-191",
            "nonce": nonce,
            "settled_at": int(time.time()),
        }

        return True, f"Payment verified successfully on {net_cfg['display_name']}", settlement_metadata
