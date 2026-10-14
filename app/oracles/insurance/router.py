"""
FastAPI Router for Risk Underwriting & Parametric Insurance Oracle with x402 Monetization.
"""

from fastapi import APIRouter, Header, status
from fastapi.responses import JSONResponse
from app.core.x402_verifier import X402Verifier
from app.core.base_schemas import X402PaymentRequirement
from app.oracles.insurance.schemas import (
    InsuranceUnderwriteInput,
    InsuranceUnderwriteOutput,
    ClaimVerificationInput,
    ClaimAdjudicationOutput,
)
from app.oracles.insurance.engine import InsuranceEngine

router = APIRouter(prefix="/v1/insurance", tags=["6. Autonomous AI Insurance & Risk Oracle"])
UNDERWRITE_PRICE_USDC = "0.025"
CLAIM_PRICE_USDC = "0.050"
ORACLE_NAME = "Physical AI Risk Underwriting & Parametric Insurance Oracle"


@router.get("/challenge", response_model=X402PaymentRequirement)
async def get_underwrite_challenge(
    network: str = None,
    x_402_preferred_network: str = Header(default=None, alias="X-402-Preferred-Network"),
):
    """Request a fresh x402 payment challenge for Mission Risk Underwriting (0.025 USDC)."""
    pref_net = network or x_402_preferred_network
    return X402Verifier.generate_challenge(
        price_usdc=UNDERWRITE_PRICE_USDC,
        oracle_name="Risk Underwriting & Proof of Insurability Oracle",
        preferred_network=pref_net,
    )


@router.get("/claim-challenge", response_model=X402PaymentRequirement)
async def get_claim_challenge(
    network: str = None,
    x_402_preferred_network: str = Header(default=None, alias="X-402-Preferred-Network"),
):
    """Request a fresh x402 payment challenge for Claim Adjudication (0.050 USDC)."""
    pref_net = network or x_402_preferred_network
    return X402Verifier.generate_challenge(
        price_usdc=CLAIM_PRICE_USDC,
        oracle_name="Smart Contract Parametric Claim Adjudication Oracle",
        preferred_network=pref_net,
    )


@router.post(
    "/underwrite",
    response_model=InsuranceUnderwriteOutput,
    responses={
        200: {"description": "Deterministic Proof of Insurability Certificate and Risk Breakdown"},
        402: {"description": "Payment Required via x402 on Polygon/Solana/Base (0.025 USDC)", "model": X402PaymentRequirement},
    },
)
async def underwrite_mission(
    body: InsuranceUnderwriteInput,
    x_402_signature: str = Header(default=None, alias="X-402-Signature"),
    authorization: str = Header(default=None),
    x_402_preferred_network: str = Header(default=None, alias="X-402-Preferred-Network"),
    x_402_network: str = Header(default=None, alias="X-402-Network"),
):
    auth_header = x_402_signature or authorization
    preferred_net = x_402_preferred_network or x_402_network

    if not auth_header:
        challenge = X402Verifier.generate_challenge(
            price_usdc=UNDERWRITE_PRICE_USDC,
            oracle_name="Risk Underwriting & Proof of Insurability Oracle",
            preferred_network=preferred_net,
        )
        return JSONResponse(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            content=challenge.model_dump(),
            headers={"X-402-Payment-Required": challenge.model_dump_json()},
        )

    is_valid, msg, settlement = X402Verifier.verify_payment_header(
        auth_header, expected_price_usdc=UNDERWRITE_PRICE_USDC
    )

    if not is_valid:
        challenge = X402Verifier.generate_challenge(
            price_usdc=UNDERWRITE_PRICE_USDC,
            oracle_name="Risk Underwriting & Proof of Insurability Oracle",
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

    output = InsuranceEngine.underwrite_mission(
        body,
        fee_paid=float(UNDERWRITE_PRICE_USDC),
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
            "X-Insurance-Policy-ID": output.policy.policy_id,
            "X-Flight-Clearance": output.flight_clearance,
        },
    )


@router.post(
    "/claim-verify",
    response_model=ClaimAdjudicationOutput,
    responses={
        200: {"description": "Automated Parametric Claim Adjudication Verdict & Onchain Payout Authorization"},
        402: {"description": "Payment Required via x402 on Polygon/Solana/Base (0.050 USDC)", "model": X402PaymentRequirement},
    },
)
async def verify_claim(
    body: ClaimVerificationInput,
    x_402_signature: str = Header(default=None, alias="X-402-Signature"),
    authorization: str = Header(default=None),
    x_402_preferred_network: str = Header(default=None, alias="X-402-Preferred-Network"),
    x_402_network: str = Header(default=None, alias="X-402-Network"),
):
    auth_header = x_402_signature or authorization
    preferred_net = x_402_preferred_network or x_402_network

    if not auth_header:
        challenge = X402Verifier.generate_challenge(
            price_usdc=CLAIM_PRICE_USDC,
            oracle_name="Smart Contract Parametric Claim Adjudication Oracle",
            preferred_network=preferred_net,
        )
        return JSONResponse(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            content=challenge.model_dump(),
            headers={"X-402-Payment-Required": challenge.model_dump_json()},
        )

    is_valid, msg, settlement = X402Verifier.verify_payment_header(
        auth_header, expected_price_usdc=CLAIM_PRICE_USDC
    )

    if not is_valid:
        challenge = X402Verifier.generate_challenge(
            price_usdc=CLAIM_PRICE_USDC,
            oracle_name="Smart Contract Parametric Claim Adjudication Oracle",
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

    output = InsuranceEngine.adjudicate_claim(
        body,
        fee_paid=float(CLAIM_PRICE_USDC),
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
            "X-Claim-Verdict": output.adjudication_verdict,
        },
    )
