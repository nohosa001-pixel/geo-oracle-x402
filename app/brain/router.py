"""
FastAPI Router for A.GRID Geo-Oracle elizaOS Brain.
Exposes /v1/brain/status, /v1/brain/character, /v1/brain/memory, and Cloud Scheduler
triggered /v1/brain/cycle (protected by optional BRAIN_CYCLE_SECRET).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

from app.brain.geo_brain_engine import brain_engine
from app.core.sister_federation import get_federation_mesh_status

router = APIRouter(prefix="/v1/brain", tags=["5. Geo-Oracle elizaOS Brain"])

CHARACTER_PATH = Path(__file__).resolve().parent / "character.json"


class BrainCycleRequest(BaseModel):
    asset_ids: Optional[List[str]] = Field(default=None, description="Optional subset of registry asset IDs to evaluate")
    use_live_feed: bool = Field(default=True, description="Fetch live Tier-1 feeds during this learning cycle")


@router.get("/status")
async def get_brain_status():
    """Returns real-time elizaOS Brain heartbeat, live ground-truth learning metrics, and GCS sync status."""
    await brain_engine.initialize()
    return brain_engine.get_status()


@router.get("/character")
async def get_brain_character():
    """Returns the standard elizaOS character.json manifest for geo-oracle-x402."""
    if CHARACTER_PATH.exists():
        return json.loads(CHARACTER_PATH.read_text(encoding="utf-8"))
    raise HTTPException(status_code=404, detail="character.json not found")


@router.get("/federation")
async def get_brain_federation():
    """Returns live A.GRID sister systems mesh health and cross-domain routing directory."""
    return await get_federation_mesh_status()


@router.get("/memory")
async def get_brain_memory(
    limit: int = Query(default=20, ge=1, le=100),
    asset_id: Optional[str] = Query(default=None),
):
    """Returns recent episodic memory blocks and time-series anomaly records."""
    await brain_engine.initialize()
    return {
        "brain_id": "geo-oracle-elizaos-brain",
        "total_episodic_records": len(brain_engine.episodic_memory),
        "records": brain_engine.get_memory(limit=limit, asset_id=asset_id),
    }


@router.post("/cycle")
async def trigger_brain_learning_cycle(
    body: Optional[BrainCycleRequest] = None,
    x_brain_cycle_secret: Optional[str] = Header(default=None, alias="X-Brain-Cycle-Secret"),
):
    """
    Executes one live Tier-1 ground-truth learning cycle.
    Designed to be called periodically by Google Cloud Scheduler (every 15-60m) with X-Brain-Cycle-Secret.
    """
    expected_secret = os.getenv("BRAIN_CYCLE_SECRET", "").strip()
    if expected_secret and x_brain_cycle_secret != expected_secret:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Brain-Cycle-Secret header")

    req = body or BrainCycleRequest()
    return await brain_engine.run_learning_cycle(
        asset_ids=req.asset_ids,
        use_live_feed=req.use_live_feed,
    )
