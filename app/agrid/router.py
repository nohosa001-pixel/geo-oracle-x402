"""
FastAPI Router for A.GRID Autonomous Logistics, Escrow Arbiter, and Machine Finance Services.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from typing import Dict, Any

from app.agrid.agent_card import get_agrid_agent_card
from app.agrid.escrow_service import (
    LogisticsEscrowService,
    DispatchVerificationRequest,
    DeliveryVerificationRequest,
    SolanaDispatchVerificationRequest,
    SolanaDeliveryVerificationRequest,
)
from app.agrid.regulatory_compliance import (
    RegulatoryComplianceEngine,
    BvlosAuditRequest,
    ColdChainAuditRequest,
)
from app.agrid.machine_credit_service import (
    MachineCreditService,
    AgentCreditEvaluationRequest,
)
from app.agrid.telemetry_stream import stream_manager, TelemetryStreamManager

router = APIRouter(prefix="/v1/agrid", tags=["A.GRID Autonomous Logistics & Machine Finance"])


@router.get("/agent-card", summary="A.GRID Semantic Agent Card Manifest")
async def get_agent_card_endpoint() -> Dict[str, Any]:
    """Returns machine-readable A.GRID agent card declaring capabilities, fees, and smart contracts."""
    return get_agrid_agent_card()


@router.post("/escrow/dispatch-verify", summary="Verify PoI & Authorize Escrow Dispatch (EVM EIP-712)")
@router.post("/escrow/verify-poi", summary="Alias for dispatch-verify (PoI Clearance)")
async def verify_dispatch(request: DispatchVerificationRequest) -> Dict[str, Any]:
    """
    Evaluates origin/destination terrain, 3D boundary layer weather, and regulatory airspace geofences.
    Issues EIP-712 Proof of Insurability (PoI) certificate to unlock escrow dispatch on Polygon.
    """
    try:
        return LogisticsEscrowService.verify_and_sign_dispatch(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dispatch verification error: {str(e)}")


@router.post("/escrow/delivery-verify", summary="Verify PoD & Authorize Instant Escrow Disbursement (EVM EIP-712)")
@router.post("/escrow/verify-pod", summary="Alias for delivery-verify (PoD Release)")
async def verify_delivery(request: DeliveryVerificationRequest) -> Dict[str, Any]:
    """
    Verifies arrival at delivery coordinates (within 25m), acceleration G-force tolerance,
    and cold-chain temperature SLA. Issues EIP-712 Proof of Delivery (PoD) releasing escrow funds onchain.
    """
    try:
        return LogisticsEscrowService.verify_and_sign_delivery(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delivery verification error: {str(e)}")


@router.post("/escrow/solana/dispatch-verify", summary="Verify PoI & Authorize Escrow Dispatch (Solana Ed25519)")
async def verify_dispatch_solana(request: SolanaDispatchVerificationRequest) -> Dict[str, Any]:
    """
    Evaluates physical constraints and signs 64-byte Ed25519 PoI proof compatible with
    Solana Anchor program (autonomous_logistics_escrow).
    """
    try:
        return LogisticsEscrowService.verify_and_sign_dispatch_solana(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Solana dispatch verification error: {str(e)}")


@router.post("/escrow/solana/delivery-verify", summary="Verify PoD & Authorize Instant Escrow Disbursement (Solana Ed25519)")
async def verify_delivery_solana(request: SolanaDeliveryVerificationRequest) -> Dict[str, Any]:
    """
    Validates physical arrival, impact shock, and cold-chain envelope, then generates
    64-byte Ed25519 PoD signature for Solana SPL USDC instant release.
    """
    try:
        return LogisticsEscrowService.verify_and_sign_delivery_solana(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Solana delivery verification error: {str(e)}")


@router.post("/compliance/bvlos-audit", summary="FAA Part 108 BVLOS & EASA SORA 2.5 Airspace Audit")
async def audit_bvlos_flight(request: BvlosAuditRequest) -> Dict[str, Any]:
    """
    Performs quantitative compliance audit against FAA Part 108 BVLOS rulemaking
    and EASA U-space SORA 2.5 ground/air risk frameworks.
    """
    try:
        faa_audit = RegulatoryComplianceEngine.evaluate_faa_part108(request)
        easa_audit = RegulatoryComplianceEngine.evaluate_easa_sora25(
            drone_wingspan_m=2.2,
            impact_kinetic_energy_kj=12.5,
            ground_population_density=request.ground_population_density_per_sq_km,
            airspace_class=request.airspace_class,
        )
        return {
            "faa_part_108": faa_audit,
            "easa_sora_2_5": easa_audit,
            "overall_status": "APPROVED" if faa_audit["compliant"] else "REQUIRES_MITIGATION",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"BVLOS audit error: {str(e)}")


@router.post("/compliance/coldchain-audit", summary="WHO PQS & FDA 21 CFR Cold-Chain Bio SLA Audit")
async def audit_coldchain_consignment(request: ColdChainAuditRequest) -> Dict[str, Any]:
    """
    Audits monitored sensor temperatures across in-transit mission profile,
    computes Mean Kinetic Temperature (MKT), and determines FDA/WHO SLA compliance.
    """
    try:
        return RegulatoryComplianceEngine.evaluate_coldchain_sla(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cold-chain audit error: {str(e)}")


@router.post("/credit/evaluate", summary="Evaluate Autonomous Agent Machine Credit Rating")
async def evaluate_machine_credit(request: AgentCreditEvaluationRequest) -> Dict[str, Any]:
    """
    Computes deterministic machine FICO score (300-850), default risk probability,
    and collateral-free lending / bond issuance capacity for physical AI robots.
    """
    try:
        return MachineCreditService.evaluate_credit(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Credit evaluation error: {str(e)}")


@router.post("/telemetry/frame", summary="Process Single In-Transit Telemetry Frame")
async def process_single_frame(frame: Dict[str, Any]) -> Dict[str, Any]:
    """REST endpoint to evaluate physical sensor bounds (G-force shock, temperature violation, SoC)."""
    return TelemetryStreamManager.process_telemetry_frame(frame)


@router.websocket("/stream/telemetry/{mission_id}")
async def websocket_telemetry_stream(websocket: WebSocket, mission_id: str):
    """
    1Hz Bidirectional WebSocket stream for autonomous carriers in flight.
    Receives raw sensor telemetry, returns instantaneous anomaly warnings and reroute triggers.
    """
    await stream_manager.connect(mission_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            data["mission_id"] = mission_id
            response = stream_manager.process_telemetry_frame(data)
            await websocket.send_json(response)
    except WebSocketDisconnect:
        stream_manager.disconnect(mission_id)
    except Exception:
        stream_manager.disconnect(mission_id)
