"""
A.GRID Earth Physical Infrastructure elizaOS Brain Engine.
Strictly separates live ground-truth telemetry learning from simulation metrics,
tracks time-series risk deltas across global critical infrastructure assets,
and persists checkpoints to GCS / local disk for 24/7 Cloud Run continuity.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.brain.checkpoint_store import BrainCheckpointStore
from app.core.observability import log_event
from app.oracles.infrastructure.registry import GLOBAL_INFRASTRUCTURE_ASSETS
from app.oracles.infrastructure.router import (
    InfrastructureAssessRequest,
    _run_infrastructure_assessment,
)

STATE_FILENAME = "geo_brain_learning_state.json"
HEARTBEAT_FILENAME = "geo_brain_heartbeat.json"
EPISODIC_FILENAME = "geo_brain_episodic_memory.json"

MAX_EPISODIC_RECORDS = 500
DEFAULT_BATCH_SIZE = int(os.getenv("BRAIN_CYCLE_BATCH_SIZE", "3"))


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _initial_state() -> Dict[str, Any]:
    now_iso = _utc_now_iso()
    return {
        "protocol": "A.GRID_GEO_ORACLE_ELIZAOS_BRAIN",
        "version": "1.0.0",
        "status": "READY_CLOUD_SCHEDULER",
        "started_at": now_iso,
        "last_cycle_at": None,
        "total_cycles_completed": 0,
        "asset_cursor": 0,
        "live_ground_truth_metrics": {
            "live_samples": 0,
            "verified_brier_pairs": 0,
            "brier_score": None,
            "high_confidence_ratio": None,
            "anomalies_detected": 0,
            "readiness_score": 0.0,
        },
        "working_memory": {},
    }


class GeoOracleBrainEngine:
    """Autonomous server-native elizaOS Brain for geo-oracle-x402."""

    def __init__(self, store: Optional[BrainCheckpointStore] = None) -> None:
        self.store = store or BrainCheckpointStore()
        self.state: Dict[str, Any] = _initial_state()
        self.episodic_memory: List[Dict[str, Any]] = []
        self.heartbeat: Dict[str, Any] = {
            "mode": "cloud_scheduler_native",
            "status": "INITIALIZED",
            "last_heartbeat_utc": _utc_now_iso(),
            "cycle": 0,
            "live_samples": 0,
            "brier_score": None,
            "readiness_score": 0.0,
            "block_id": None,
        }
        self._loaded = False

    async def initialize(self) -> None:
        """Restores persisted Brain state from GCS or local disk on startup."""
        if self._loaded:
            return
        saved_state = await self.store.load_json(STATE_FILENAME)
        if isinstance(saved_state, dict) and "live_ground_truth_metrics" in saved_state:
            self.state = saved_state

        saved_ep = await self.store.load_json(EPISODIC_FILENAME)
        if isinstance(saved_ep, dict) and isinstance(saved_ep.get("records"), list):
            self.episodic_memory = saved_ep["records"][-MAX_EPISODIC_RECORDS:]

        saved_hb = await self.store.load_json(HEARTBEAT_FILENAME)
        if isinstance(saved_hb, dict):
            self.heartbeat = saved_hb

        self._loaded = True

    def _compute_realized_hazard(self, assessment: Dict[str, Any]) -> float:
        """
        Derives an objective [0.0, 1.0] ground-truth hazard realization indicator
        from live Tier-1 observations (USGS, NASA EONET, GloFAS/Flood, Wet-Bulb, Sub-oracles).
        """
        summary = assessment.get("summary", {})
        layers = assessment.get("layers", {})
        usgs = layers.get("usgs_seismic_30d", {})
        eonet = layers.get("nasa_active_hazards", {})

        if (
            summary.get("risk_grade") == "CRITICAL"
            or usgs.get("max_magnitude_30d", 0.0) >= 6.0
            or eonet.get("wildfires_nearby", 0) > 0
            or eonet.get("storms_nearby", 0) > 0
        ):
            return 1.0
        if (
            summary.get("risk_grade") == "ELEVATED"
            or summary.get("flood_elevation_risk") == "HIGH"
            or summary.get("cooling_heat_stress") == "HIGH"
            or usgs.get("max_magnitude_30d", 0.0) >= 5.0
        ):
            return 0.5
        return 0.0

    def _select_batch_assets(self, asset_ids: Optional[List[str]] = None) -> List[str]:
        all_ids = list(GLOBAL_INFRASTRUCTURE_ASSETS.keys())
        if asset_ids:
            return [aid for aid in asset_ids if aid in GLOBAL_INFRASTRUCTURE_ASSETS] or all_ids[:DEFAULT_BATCH_SIZE]

        cursor = int(self.state.get("asset_cursor", 0)) % max(1, len(all_ids))
        batch: List[str] = []
        for i in range(min(DEFAULT_BATCH_SIZE, len(all_ids))):
            batch.append(all_ids[(cursor + i) % len(all_ids)])
        self.state["asset_cursor"] = (cursor + len(batch)) % max(1, len(all_ids))
        return batch

    async def run_learning_cycle(
        self,
        asset_ids: Optional[List[str]] = None,
        use_live_feed: bool = True,
    ) -> Dict[str, Any]:
        """
        Executes one real Tier-1 ground-truth learning cycle across a rotating batch of
        global infrastructure assets, computes time-series deltas & honest Brier Score,
        and persists checkpoints to local disk + GCS.
        """
        await self.initialize()
        t0 = time.perf_counter()
        batch_ids = self._select_batch_assets(asset_ids)

        cycle_num = int(self.state.get("total_cycles_completed", 0)) + 1
        metrics = self.state["live_ground_truth_metrics"]
        working = self.state["working_memory"]

        cycle_records: List[Dict[str, Any]] = []
        cycle_anomalies: List[Dict[str, Any]] = []
        high_conf_count = 0

        for aid in batch_ids:
            asset = GLOBAL_INFRASTRUCTURE_ASSETS[aid]
            req = InfrastructureAssessRequest(
                asset_id=aid,
                asset_type=asset["asset_type"],
                latitude=asset["latitude"],
                longitude=asset["longitude"],
                commodity=asset.get("commodity", "INFRASTRUCTURE"),
                use_live_feed=use_live_feed,
            )
            assessment = await _run_infrastructure_assessment(
                req=req,
                fee_paid=0.0,
                settlement_network="BRAIN_INTERNAL_CYCLE",
                preview=True,
            )

            summary = assessment["summary"]
            score = float(summary["combined_risk_score"])
            confidence = summary.get("assessment_confidence", "DEGRADED")
            if confidence == "HIGH":
                high_conf_count += 1

            realized = self._compute_realized_hazard(assessment)
            prev = working.get(aid)
            score_delta = round(score - float(prev["combined_risk_score"]), 2) if prev else 0.0

            # Honest sequential Brier Score update: compare previous cycle's predicted p vs current realized ground truth
            if prev is not None:
                prev_prob = max(0.0, min(1.0, float(prev["combined_risk_score"]) / 100.0))
                sq_err = (prev_prob - realized) ** 2
                prev_pairs = int(metrics.get("verified_brier_pairs", 0))
                prev_brier = float(metrics["brier_score"]) if metrics.get("brier_score") is not None else 0.0
                new_pairs = prev_pairs + 1
                metrics["brier_score"] = round(((prev_brier * prev_pairs) + sq_err) / new_pairs, 5)
                metrics["verified_brier_pairs"] = new_pairs

            # Detect meaningful time-series anomaly
            anomaly_reasons: List[str] = []
            if prev and abs(score_delta) >= 15.0:
                anomaly_reasons.append(f"RISK_SCORE_JUMP ({score_delta:+.2f})")
            if summary.get("risk_grade") in ("ELEVATED", "CRITICAL"):
                anomaly_reasons.append(f"HIGH_RISK_GRADE ({summary['risk_grade']})")
            if assessment["layers"].get("nasa_active_hazards", {}).get("wildfires_nearby", 0) > 0:
                anomaly_reasons.append("NASA_ACTIVE_WILDFIRE_NEARBY")

            if anomaly_reasons:
                metrics["anomalies_detected"] = int(metrics.get("anomalies_detected", 0)) + 1
                cycle_anomalies.append({
                    "asset_id": aid,
                    "reasons": anomaly_reasons,
                    "combined_risk_score": score,
                    "score_delta": score_delta,
                })

            block_seed = json.dumps(
                {"cycle": cycle_num, "asset_id": aid, "score": score, "ts": int(time.time())},
                sort_keys=True,
            )
            block_id = "blk_geo_" + hashlib.sha256(block_seed.encode("utf-8")).hexdigest()[:12]

            record = {
                "block_id": block_id,
                "cycle": cycle_num,
                "observed_at_utc": _utc_now_iso(),
                "asset_id": aid,
                "asset_type": asset["asset_type"],
                "combined_risk_score": score,
                "score_delta": score_delta,
                "risk_grade": summary["risk_grade"],
                "assessment_confidence": confidence,
                "realized_hazard": realized,
                "anomalies": anomaly_reasons,
                "proof_hash": assessment["settlement"]["deterministic_proof_hash"],
                "data_provenance": assessment.get("data_provenance", {}),
            }

            working[aid] = {
                "combined_risk_score": score,
                "risk_grade": summary["risk_grade"],
                "assessment_confidence": confidence,
                "last_observed_utc": record["observed_at_utc"],
                "block_id": block_id,
            }
            self.episodic_memory.append(record)
            cycle_records.append(record)

        self.episodic_memory = self.episodic_memory[-MAX_EPISODIC_RECORDS:]
        self.state["total_cycles_completed"] = cycle_num
        self.state["last_cycle_at"] = _utc_now_iso()
        self.state["status"] = "ACTIVE_LIVE_GROUND_TRUTH_LEARNING"

        # Update honest live_ground_truth_metrics
        total_samples = int(metrics.get("live_samples", 0)) + len(cycle_records)
        metrics["live_samples"] = total_samples
        batch_conf_ratio = high_conf_count / max(1, len(cycle_records))
        prev_ratio = metrics.get("high_confidence_ratio")
        metrics["high_confidence_ratio"] = round(
            batch_conf_ratio if prev_ratio is None else (0.8 * float(prev_ratio) + 0.2 * batch_conf_ratio),
            4,
        )

        # Honest readiness: scales smoothly with real live sample coverage (up to 0.95 cap, never fake 0.9999)
        coverage_factor = min(1.0, len(working) / max(1, len(GLOBAL_INFRASTRUCTURE_ASSETS)))
        sample_factor = min(1.0, total_samples / 60.0)
        brier_quality = 1.0 - min(0.5, float(metrics["brier_score"])) if metrics["brier_score"] is not None else 0.75
        metrics["readiness_score"] = round(
            min(0.95, 0.35 * coverage_factor + 0.35 * sample_factor + 0.30 * brier_quality),
            4,
        )

        last_block_id = cycle_records[-1]["block_id"] if cycle_records else None
        self.heartbeat = {
            "mode": "cloud_scheduler_native",
            "status": "RUNNING",
            "last_heartbeat_utc": _utc_now_iso(),
            "cycle": cycle_num,
            "live_samples": total_samples,
            "brier_score": metrics["brier_score"],
            "readiness_score": metrics["readiness_score"],
            "block_id": last_block_id,
            "persistence_mode": self.store.persistence_mode,
        }

        gcs_synced = await self.store.save_json(STATE_FILENAME, self.state)
        await self.store.save_json(HEARTBEAT_FILENAME, self.heartbeat)
        await self.store.save_json(EPISODIC_FILENAME, {"records": self.episodic_memory})

        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        log_event(
            "geo_brain_cycle_completed",
            severity="INFO",
            cycle=cycle_num,
            assets_evaluated=batch_ids,
            live_samples=total_samples,
            brier_score=metrics["brier_score"],
            anomalies=len(cycle_anomalies),
            gcs_synced=gcs_synced,
            latency_ms=latency_ms,
        )

        return {
            "cycle": cycle_num,
            "assets_evaluated": batch_ids,
            "records": cycle_records,
            "anomalies_detected": cycle_anomalies,
            "live_ground_truth_metrics": metrics,
            "persistence_mode": self.store.persistence_mode,
            "latency_ms": latency_ms,
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "brain_id": "geo-oracle-elizaos-brain",
            "persistence_mode": self.store.persistence_mode,
            "heartbeat": self.heartbeat,
            "learning_state": self.state,
            "episodic_memory_count": len(self.episodic_memory),
        }

    def get_memory(self, limit: int = 20, asset_id: Optional[str] = None) -> List[Dict[str, Any]]:
        records = self.episodic_memory
        if asset_id:
            records = [r for r in records if r.get("asset_id") == asset_id]
        return list(reversed(records[-max(1, min(100, limit)):]))


brain_engine = GeoOracleBrainEngine()
