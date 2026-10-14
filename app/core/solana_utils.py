"""
Solana Cryptographic Utilities for x402 Micropayment Protocol.
Provides pure Python Base58 encoding/decoding and Ed25519 keypair generation,
message formatting, and cryptographic signature verification.
Zero external C-extension dependencies beyond Python standard libraries and `cryptography`.
"""

import os
from typing import Tuple, Optional
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature

# Standard Bitcoin / Solana Base58 Alphabet
B58_ALPHABET = b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58encode(raw_bytes: bytes) -> str:
    """Encodes arbitrary bytes into a Base58 string (Solana standard)."""
    n = int.from_bytes(raw_bytes, "big")
    chars = []
    while n > 0:
        n, r = divmod(n, 58)
        chars.append(B58_ALPHABET[r : r + 1])
    # Preserve leading zeros
    pad = 0
    for byte in raw_bytes:
        if byte == 0:
            pad += 1
        else:
            break
    return (b"1" * pad + b"".join(reversed(chars))).decode("ascii")


def b58decode(base58_str: str) -> bytes:
    """Decodes a Base58 string back to raw bytes."""
    n = 0
    for char in base58_str.encode("ascii"):
        digit = B58_ALPHABET.index(char)
        n = n * 58 + digit
    res = n.to_bytes((n.bit_length() + 7) // 8, "big") if n > 0 else b""
    pad = 0
    for char in base58_str:
        if char == "1":
            pad += 1
        else:
            break
    return b"\x00" * pad + res


def is_valid_solana_address(address: str) -> bool:
    """Checks whether a string is a valid Solana public key (Base58, 32 bytes)."""
    if not (32 <= len(address) <= 44):
        return False
    try:
        decoded = b58decode(address)
        return len(decoded) == 32
    except Exception:
        return False


class SolanaKeypair:
    """Encapsulates a Solana Ed25519 Keypair for autonomous agents and testing."""

    def __init__(self, private_key: Optional[ed25519.Ed25519PrivateKey] = None):
        self._private_key = private_key or ed25519.Ed25519PrivateKey.generate()
        self._public_key = self._private_key.public_key()
        self.public_bytes = self._public_key.public_bytes_raw()
        self.public_key_b58 = b58encode(self.public_bytes)

    @classmethod
    def generate(cls) -> "SolanaKeypair":
        """Generates a new fresh random Solana keypair."""
        return cls()

    @classmethod
    def from_seed(cls, seed_bytes: bytes) -> "SolanaKeypair":
        """Generates a deterministic Solana keypair from a 32-byte seed."""
        if len(seed_bytes) != 32:
            raise ValueError("Seed must be exactly 32 bytes")
        priv = ed25519.Ed25519PrivateKey.from_private_bytes(seed_bytes)
        return cls(priv)

    def sign_message(self, message: bytes) -> str:
        """Signs raw message bytes and returns a Base58 encoded Ed25519 signature."""
        sig_bytes = self._private_key.sign(message)
        return b58encode(sig_bytes)


class SolanaVerifier:
    """Verifies Solana Ed25519 signatures for x402 micropayments."""

    @staticmethod
    def format_auth_message(
        nonce: str,
        timestamp: int,
        amount_usdc: str,
        recipient_vault: str,
        token_mint: str,
        cluster: str = "mainnet-beta",
    ) -> str:
        """
        Deterministic, human-readable and machine-verifiable Solana authorization message.
        Follows standard Solana off-chain message conventions.
        """
        return (
            f"x402-solana-micropayment-auth\n"
            f"Cluster: {cluster}\n"
            f"Recipient: {recipient_vault}\n"
            f"Token: USDC ({token_mint})\n"
            f"Amount: {amount_usdc} USDC\n"
            f"Nonce: {nonce}\n"
            f"Timestamp: {timestamp}"
        )

    @staticmethod
    def verify_signature(
        public_key_b58: str,
        signature_b58: str,
        message: bytes,
    ) -> Tuple[bool, str]:
        """
        Cryptographically verifies an Ed25519 signature using the signer's Base58 public key.
        """
        try:
            pub_bytes = b58decode(public_key_b58)
            if len(pub_bytes) != 32:
                return False, f"Invalid Solana public key length: {len(pub_bytes)} bytes (expected 32)"
            pub_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
        except Exception as e:
            return False, f"Failed to parse Solana public key: {str(e)}"

        try:
            sig_bytes = b58decode(signature_b58)
            # Fallback if signature was provided in hex
            if len(sig_bytes) != 64 and len(signature_b58) == 128:
                try:
                    sig_bytes = bytes.fromhex(signature_b58)
                except Exception:
                    pass
            if len(sig_bytes) != 64:
                return False, f"Invalid Ed25519 signature length: {len(sig_bytes)} bytes (expected 64)"
        except Exception as e:
            return False, f"Failed to decode Solana signature: {str(e)}"

        try:
            pub_key.verify(sig_bytes, message)
            return True, "Valid Solana Ed25519 signature"
        except InvalidSignature:
            return False, "Solana Ed25519 signature verification failed (invalid signature)"
        except Exception as e:
            return False, f"Solana verification error: {str(e)}"
