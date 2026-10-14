"""
FastAPI Router for Kinematic & Energy-Optimal Routing Oracle with x402 Monetization.
"""

from fastapi import APIRouter, Header, status
from fastapi.responses import JSONResponse
from app.core.x402_verifier import X402Verifier
from app.core.base_schemas import X402PaymentRequirement
from app.oracles.energy_routing.schemas import EnergyRoutingInput, EnergyRoutingOutput
from app.oracles.energy_routing.engine import EnergyRoutingEngine

router = APIRouter(prefix="/v1/routing", tags=["5. Energy-Optimal Routing Oracle"])
ORACLE_PRICE_USDC = "0.010"
ORACLE_NAME = "Kinematic & Energy-Optimal 3D Routing Oracle"


@router.get("/challenge", response_model=X402PaymentRequirement)
async def get_routing_challenge(
    network: str = None,
    x_402_preferred_network: str = Header(default=None, alias="X-402-Preferred-Network"),
):
    """Request a fresh x402 payment challenge for Energy-Optimal Routing Oracle with multi-chain support."""
    pref_net = network or x_402_preferred_network
    return X402Verifier.generate_challenge(
        price_usdc=ORACLE_PRICE_USDC,
        oracle_name=ORACLE_NAME,
        preferred_network=pref_net,
    )


@router.post(
    "/energy-optimal",
    response_model=EnergyRoutingOutput,
    responses={
        200: {"description": "Deterministic 3D energy-optimal waypoint path and battery budget"},
        402: {"description": "Payment Required via x402 on Polygon/Solana/Base (0.010 USDC)", "model": X402PaymentRequirement},
    },
)
async def plan_energy_optimal_route(
    body: EnergyRoutingInput,
    x_402_signature: str = Header(default=None, alias="X-402-Signature"),
    authorization: str = Header(default=None),
    x_402_preferred_network: str = Header(default=None, alias="X-402-Preferred-Network"),
    x_402_network: str = Header(default=None, alias="X-402-Network"),
):
    auth_header = x_402_signature or authorization
    preferred_net = x_402_preferred_network or x_402_network

    if not auth_header:
        challenge = X402Verifier.generate_challenge(
            price_usdc=ORACLE_PRICE_USDC,
            oracle_name=ORACLE_NAME,
            preferred_network=preferred_net,
        )
        return JSONResponse(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            content=challenge.model_dump(),
            headers={"X-402-Payment-Required": challenge.model_dump_json()},
        )

    is_valid, msg, settlement = X402Verifier.verify_payment_header(auth_header, expected_price_usdc=ORACLE_PRICE_USDC)

    if not is_valid:
        challenge = X402Verifier.generate_challenge(
            price_usdc=ORACLE_PRICE_USDC,
            oracle_name=ORACLE_NAME,
            preferred_network=preferred_net,
        )
        challenge_dict = challenge.model_dump()
        challenge_dict["rejection_reason"] = msg
        return JSONResponse(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            content=challenge_dict,
            headers={
                "X-402-Payment-Required": challenge.model_dump_json(),
                "X-402-Rejection-Reason": msg,
            },
        )

    settlement_net_display = settlement.get("network", "Polygon") if settlement else "Polygon"
    if settlement and "Chain ID" not in settlement_net_display and settlement.get("chain_id"):
        settlement_net_display = f"{settlement_net_display} (Chain ID {settlement.get('chain_id')})"
    elif settlement and settlement.get("network") == "Solana":
        settlement_net_display = f"Solana (Cluster {settlement.get('cluster', 'mainnet-beta')})"

    output = EnergyRoutingEngine.generate_optimal_route(
        body,
        fee_paid=float(ORACLE_PRICE_USDC),
        settlement_network=settlement_net_display,
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=output.model_dump(),
        headers={
            "X-402-Settlement-Status": "VERIFIED_PAID",
            "X-402-Payer": settlement.get("payer", "unknown") if settlement else "unknown",
            "X-402-Network": settlement.get("network", "Polygon") if settlement else "Polygon",
            "X-402-Proof-Hash": output.deterministic_proof_hash,
        },
    )
