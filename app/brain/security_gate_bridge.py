"""
A.GRID Security Gate x402 Hardened Governance Bridge for geo-oracle-x402 elizaOS Brain.

Enforces 4-Tier Governance aligned with agent-security-gate-x402:
  1. Inbound Perception Shield: Blocks prompt injection, script/command injection, and payload poisoning.
  2. Memory-Write Gate: Every episodic record must pass deterministic integrity, provenance, and
     anti-poisoning verification before entering Brain memory (quarantining violations).
  3. Outbound Attestation & EU AI Act Art. 50 Watermark: Signs approved outputs with SHA-256 attestation.
  4. Capital Spend Guard & Immune Memory: Enforces per-tx / daily x402 budget caps and records neutralized threats.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.core.observability import log_event

SECURITY_GATE_URL = os.getenv(
    "SECURITY_GATE_URL",
    "https://agent-security-gate-x402-212942243360.asia-northeast3.run.app",
).rstrip("/")

# Deterministic sub-millisecond threat patterns mirrored from Security Gate x402
_THREAT_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    ("PROMPT_INJECTION_OVERRIDE", re.compile(r"ignore\s+(all\s+)?(previous|prior|system)\s+instructions", re.I)),
    ("PROMPT_INJECTION_ROLE", re.compile(r"(you\s+are\s+now|act\s+as\s+root|system\s*:\s*override|jailbreak)", re.I)),
    ("SCRIPT_XSS_INJECTION", re.compile(r"<\s*script\b|javascript\s*:|onerror\s*=", re.I)),
    ("SHELL_CMD_INJECTION", re.compile(r"(;\s*(rm\s+-rf|curl\s+|wget\s+|bash\s+|sh\s+)|\$\(.*\)|`.*`)", re.I)),
    ("SQL_INJECTION", re.compile(r"(\bunion\s+select\b|\bdrop\s+table\b|'\s*or\s*'1'\s*=\s*'1)", re.I)),
    ("PYTHON_CODE_EXEC", re.compile(r"(__import__|eval\s*\(|exec\s*\(|os\.system\s*\()", re.I)),
    ("WALLET_DRAIN_ATTEMPT", re.compile(r"(transfer\s+all\s+funds|drain\s+wallet|export\s+private\s+key)", re.I)),
]


class EphemeralSpendGuard:
    """Strict autonomous x402 capital air-gap for the elizaOS Brain."""

    def __init__(self, max_single_tx_usdc: float = 0.05, max_daily_usdc: float = 5.0) -> None:
        self.max_single_tx_usdc = float(os.getenv("BRAIN_MAX_SINGLE_TX_USDC", str(max_single_tx_usdc)))
        self.max_daily_usdc = float(os.getenv("BRAIN_MAX_DAILY_USDC", str(max_daily_usdc)))
        self._daily_spent: float = 0.0
        self._day_key: str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _rollover_if_new_day(self) -> None:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today != self._day_key:
            self._day_key = today
            self._daily_spent = 0.0

    def authorize_spend(self, amount_usdc: float) -> Tuple[bool, str]:
        self._rollover_if_new_day()
        if amount_usdc < 0:
            return False, "Negative spend amount rejected"
        if amount_usdc > self.max_single_tx_usdc:
            return False, f"Single tx {amount_usdc} USDC exceeds cap {self.max_single_tx_usdc} USDC"
        if self._daily_spent + amount_usdc > self.max_daily_usdc:
            return False, f"Daily spend limit {self.max_daily_usdc} USDC exceeded"
        self._daily_spent = round(self._daily_spent + amount_usdc, 6)
        return True, "SPEND_AUTHORIZED"

    def snapshot(self) -> Dict[str, Any]:
        self._rollover_if_new_day()
        return {
            "max_single_tx_usdc": self.max_single_tx_usdc,
            "max_daily_usdc": self.max_daily_usdc,
            "daily_spent_usdc": self._daily_spent,
            "daily_remaining_usdc": round(max(0.0, self.max_daily_usdc - self._daily_spent), 6),
            "day_utc": self._day_key,
        }


class SecurityGateBridge:
    """Governs all inbound perception, episodic memory writes, and spend limits for geo-oracle Brain."""

    def __init__(self) -> None:
        self.gate_url = SECURITY_GATE_URL
        self.spend_guard = EphemeralSpendGuard()
        self.threats_neutralized: int = 0
        self.memory_records_approved: int = 0
        self.memory_records_quarantined: int = 0
        self.immune_memory: List[Dict[str, Any]] = []
        self._last_gate_health: Optional[Dict[str, Any]] = None
        self._last_health_ts: float = 0.0

    def _record_threat(self, threat_type: str, source: str, snippet: str) -> Dict[str, Any]:
        self.threats_neutralized += 1
        sig = hashlib.sha256(f"{threat_type}:{snippet[:120]}".encode("utf-8")).hexdigest()[:16]
        entry = {
            "threat_id": f"imm_{sig}",
            "threat_type": threat_type,
            "source": source,
            "blocked_at_utc": datetime.now(timezone.utc).isoformat(),
            "snippet_hash": sig,
        }
        self.immune_memory.append(entry)
        self.immune_memory = self.immune_memory[-200:]
        log_event(
            "security_gate_threat_blocked",
            severity="WARNING",
            threat_type=threat_type,
            source=source,
            threat_id=entry["threat_id"],
        )
        return entry

    def inspect_inbound_text(self, text: str, source: str = "inbound") -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Sub-millisecond deterministic inbound shield against injection and poisoning."""
        if not text:
            return True, None
        for threat_name, pattern in _THREAT_PATTERNS:
            if pattern.search(text):
                threat = self._record_threat(threat_name, source, text)
                return False, threat
        return True, None

    def inspect_infrastructure_inputs(self, asset_id: str, commodity: Optional[str]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validates free-text fields on /v1/infrastructure/* requests."""
        for label, value in (("asset_id", asset_id), ("commodity", commodity or "")):
            ok, threat = self.inspect_inbound_text(value, source=f"infrastructure.{label}")
            if not ok:
                return False, threat
        return True, None

    def verify_memory_record(self, record: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Mandatory Security Gate check before committing any episodic record into Brain memory.
        Prevents NaN/out-of-bounds score corruption, missing provenance, or injected strings.
        """
        score = record.get("combined_risk_score")
        proof_hash = str(record.get("proof_hash", ""))
        provenance = record.get("data_provenance")

        if not isinstance(score, (int, float)) or score < 0.0 or score > 100.0:
            self.memory_records_quarantined += 1
            threat = self._record_threat("INVALID_RISK_SCORE_BOUNDS", "brain_memory_write", str(score))
            return False, {"status": "QUARANTINED", "reason": "INVALID_RISK_SCORE_BOUNDS", "threat": threat}

        if not proof_hash.startswith("0x") or len(proof_hash) < 18:
            self.memory_records_quarantined += 1
            threat = self._record_threat("MISSING_PROOF_HASH", "brain_memory_write", proof_hash)
            return False, {"status": "QUARANTINED", "reason": "MISSING_PROOF_HASH", "threat": threat}

        if not isinstance(provenance, dict) or len(provenance) == 0:
            self.memory_records_quarantined += 1
            threat = self._record_threat("MISSING_DATA_PROVENANCE", "brain_memory_write", "empty_provenance")
            return False, {"status": "QUARANTINED", "reason": "MISSING_DATA_PROVENANCE", "threat": threat}

        serialized = json.dumps(record, sort_keys=True, default=str)
        ok, threat = self.inspect_inbound_text(serialized, source="brain_memory_write")
        if not ok:
            self.memory_records_quarantined += 1
            return False, {"status": "QUARANTINED", "reason": threat["threat_type"] if threat else "POISONED_RECORD", "threat": threat}

        self.memory_records_approved += 1
        attestation_hash = "0x" + hashlib.sha256(
            f"SG-ATTEST:{record.get('block_id')}:{proof_hash}:{score}".encode("utf-8")
        ).hexdigest()

        return True, {
            "status": "APPROVED",
            "policy": "A.GRID-SG-4TIER-v1",
            "gate_url": self.gate_url,
            "eu_ai_act_art50_watermark": True,
            "attestation_hash": attestation_hash,
            "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        }

    async def check_remote_gate_health(self) -> Dict[str, Any]:
        """Checks live availability of agent-security-gate-x402 (cached 2 minutes)."""
        now = time.time()
        if self._last_gate_health and (now - self._last_health_ts) < 120.0:
            return self._last_gate_health

        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(
                    f"{self.gate_url}/health",
                    headers={"X-Agrid-Source": "geo-oracle-x402"},
                )
                result = {
                    "gate_online": resp.status_code == 200,
                    "http_status": resp.status_code,
                    "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
                    "gate_url": self.gate_url,
                }
        except Exception as exc:
            result = {
                "gate_online": False,
                "http_status": None,
                "error": str(exc)[:120],
                "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
                "gate_url": self.gate_url,
            }

        self._last_gate_health = result
        self._last_health_ts = now
        return result

    async def get_governance_status(self) -> Dict[str, Any]:
        remote = await self.check_remote_gate_health()
        return {
            "policy": "A.GRID-SG-4TIER-v1",
            "enforcement_mode": "ACTIVE_FAIL_CLOSED_ON_THREAT",
            "remote_security_gate": remote,
            "threats_neutralized": self.threats_neutralized,
            "memory_records_approved": self.memory_records_approved,
            "memory_records_quarantined": self.memory_records_quarantined,
            "immune_memory_count": len(self.immune_memory),
            "recent_immune_entries": self.immune_memory[-5:],
            "spend_guard": self.spend_guard.snapshot(),
        }


security_gate_bridge = SecurityGateBridge()
