"""
Machine Credit Evaluation Engine for Autonomous Physical AI Agents (A.GRID Standard).
Computes deterministic machine FICO-style credit scores (300 - 850), default risk probability,
and maximum recommended collateral-free machine lending capacity.
"""

from typing import Dict, Any
from pydantic import BaseModel, Field


class AgentCreditEvaluationRequest(BaseModel):
    agent_address: str = Field(..., description="Ethereum wallet address of the autonomous carrier agent")
    owner_address: str = Field(..., description="Wallet address of the human/corporate robot owner")
    total_missions_completed: int = Field(0, ge=0)
    total_missions_failed: int = Field(0, ge=0)
    total_mileage_km: float = Field(0.0, ge=0.0)
    total_revenue_earned_usdc: float = Field(0.0, ge=0.0)
    accident_count: int = Field(0, ge=0)
    avg_stability_score: float = Field(0.85, ge=0.0, le=1.0)
    hardware_health_score: float = Field(1.00, ge=0.0, le=1.0)


class MachineCreditService:
    @staticmethod
    def evaluate_credit(req: AgentCreditEvaluationRequest) -> Dict[str, Any]:
        """
        Calculates machine credit rating using 4 weighted pillars:
        1. Mission Success & Reliability (35%)
        2. Safety & Accident-Free Record (30%)
        3. Physical Hardware Health & Flight Stability (20%)
        4. Cumulative Economic Revenue Generation (15%)
        """
        total_missions = req.total_missions_completed + req.total_missions_failed
        
        if total_missions == 0:
            score = 580
            rating_tier = "BBB (Provisional Baseline)"
            max_loan_usdc = 1000.0
            default_probability = 0.052
        else:
            # 1. Success pillar (max 192 pts)
            success_rate = req.total_missions_completed / total_missions
            pts_success = success_rate * 192.0

            # 2. Safety pillar (max 165 pts)
            pts_accident_penalty = req.accident_count * 50.0
            pts_safety = max(165.0 - pts_accident_penalty, 0.0)

            # 3. Hardware health & stability pillar (max 110 pts)
            pts_health = ((req.avg_stability_score + req.hardware_health_score) / 2.0) * 110.0

            # 4. Volume & Revenue track record (max 83 pts)
            volume_factor = min(req.total_missions_completed / 300.0, 1.0)
            pts_revenue = volume_factor * 83.0

            raw_score = 300.0 + pts_success + pts_safety + pts_health + pts_revenue
            score = int(min(max(raw_score, 300.0), 850.0))

            # Tier classification
            if score >= 800:
                rating_tier = "AAA (Prime Machine Sovereign)"
                max_loan_usdc = 50000.0
                default_probability = 0.003
            elif score >= 740:
                rating_tier = "AA (Prime Operational)"
                max_loan_usdc = 25000.0
                default_probability = 0.009
            elif score >= 680:
                rating_tier = "A (Investment Grade Standard)"
                max_loan_usdc = 12000.0
                default_probability = 0.021
            elif score >= 620:
                rating_tier = "BBB (Adequate Commercial)"
                max_loan_usdc = 5000.0
                default_probability = 0.045
            elif score >= 550:
                rating_tier = "BB (Subprime Restricted)"
                max_loan_usdc = 1500.0
                default_probability = 0.098
            else:
                rating_tier = "D (High Risk / Default Watch)"
                max_loan_usdc = 0.0
                default_probability = 0.285

        return {
            "agent_address": req.agent_address,
            "owner_address": req.owner_address,
            "machine_credit_score": score,
            "credit_tier": rating_tier,
            "annual_default_probability": round(default_probability, 4),
            "underwriting_recommendations": {
                "max_unsecured_loan_usdc": max_loan_usdc,
                "recommended_apr_percent": round(max(5.5, 18.0 - (score - 300) * 0.022), 2),
                "bond_issuance_eligible": score >= 700,
                "max_bond_tranche_usdc": round(max_loan_usdc * 3.5, 2) if score >= 700 else 0.0
            },
            "operational_factors": {
                "total_missions": total_missions,
                "success_rate_percent": round((req.total_missions_completed / max(total_missions, 1)) * 100, 2),
                "total_mileage_km": req.total_mileage_km,
                "total_revenue_earned_usdc": req.total_revenue_earned_usdc,
                "accident_count": req.accident_count,
                "hardware_health_score": req.hardware_health_score
            }
        }
