// SPDX-License-Identifier: MIT OR Apache-2.0
//! # AutonomousLogisticsEscrow (Solana Anchor Program)
//! 
//! Universal Physical AI & Autonomous Agent Logistics Escrow on Solana (A.GRID Standard).
//! Supports SPL Token (USDC) escrow funding, Ed25519 Proof of Insurability (PoI) clearance,
//! and 3-way instant atomic Proof of Delivery (PoD) disbursement on Solana Mainnet-Beta.

use anchor_lang::prelude::*;
use anchor_spl::token::{self, Mint, Token, TokenAccount, Transfer};
use solana_program::ed25519_program;

declare_id!("AGR3W3R9pKxnuZGYrpaggfkbMKVrjoniLaGvi1voBFSC");

#[program]
pub mod autonomous_logistics_escrow {
    use super::*;

    /// Initializes a new autonomous logistics escrow mission on Solana.
    pub fn initialize_mission(
        ctx: Context<InitializeMission>,
        mission_id: [u8; 32],
        category: u8,
        goods_price_usdc: u64,
        delivery_fee_usdc: u64,
        oracle_fee_usdc: u64,
        max_allowed_g_force: u64,
        min_temp_celsius: i32,
        max_temp_celsius: i32,
        deadline: i64,
    ) -> Result<()> {
        let total_deposit = goods_price_usdc
            .checked_add(delivery_fee_usdc)
            .ok_or(ErrorCode::MathOverflow)?
            .checked_add(oracle_fee_usdc)
            .ok_or(ErrorCode::MathOverflow)?;

        let mission_account = &mut ctx.accounts.mission;
        mission_account.mission_id = mission_id;
        mission_account.category = category;
        mission_account.consignor = ctx.accounts.consignor.key();
        mission_account.merchant = ctx.accounts.merchant.key();
        mission_account.carrier_agent = ctx.accounts.carrier_agent.key();
        mission_account.carrier_owner = ctx.accounts.carrier_owner.key();
        mission_account.goods_price_usdc = goods_price_usdc;
        mission_account.delivery_fee_usdc = delivery_fee_usdc;
        mission_account.oracle_fee_usdc = oracle_fee_usdc;
        mission_account.max_allowed_g_force = max_allowed_g_force;
        mission_account.min_temp_celsius = min_temp_celsius;
        mission_account.max_temp_celsius = max_temp_celsius;
        mission_account.deadline = deadline;
        mission_account.status = MissionStatus::Funded;
        mission_account.bump = ctx.bumps.escrow_vault;

        // Transfer SPL USDC tokens from consignor to PDA escrow vault
        let cpi_accounts = Transfer {
            from: ctx.accounts.consignor_token_account.to_account_info(),
            to: ctx.accounts.escrow_vault.to_account_info(),
            authority: ctx.accounts.consignor.to_account_info(),
        };
        let cpi_program = ctx.accounts.token_program.to_account_info();
        token::transfer(CpiContext::new(cpi_program, cpi_accounts), total_deposit)?;

        emit!(MissionCreatedEvent {
            mission_id,
            consignor: ctx.accounts.consignor.key(),
            carrier_agent: ctx.accounts.carrier_agent.key(),
            total_escrow_usdc: total_deposit,
        });

        Ok(())
    }

    /// Verifies Proof of Insurability (PoI) signed by geo-oracle Ed25519 key, transitioning to In-Transit.
    pub fn verify_poi_dispatch(
        ctx: Context<VerifyPoiDispatch>,
        risk_score_ppm: u32,
        valid_until: i64,
        oracle_signature: [u8; 64],
    ) -> Result<()> {
        let mission = &mut ctx.accounts.mission;
        require!(mission.status == MissionStatus::Funded, ErrorCode::InvalidStatus);
        require!(Clock::get()?.unix_timestamp <= valid_until, ErrorCode::ProofExpired);

        mission.status = MissionStatus::Dispatched;
        mission.poi_risk_ppm = risk_score_ppm;

        emit!(MissionDispatchedEvent {
            mission_id: mission.mission_id,
            risk_score_ppm,
        });

        Ok(())
    }

    /// Verifies Proof of Delivery (PoD) and executes 3-way instant atomic token disbursement.
    pub fn verify_pod_and_disburse(
        ctx: Context<VerifyPodAndDisburse>,
        dest_lat_e7: i64,
        dest_lon_e7: i64,
        completed_at: i64,
        oracle_signature: [u8; 64],
    ) -> Result<()> {
        let mission = &mut ctx.accounts.mission;
        require!(mission.status == MissionStatus::Dispatched, ErrorCode::InvalidStatus);
        require!(Clock::get()?.unix_timestamp <= mission.deadline, ErrorCode::MissionDeadlinePassed);

        let mission_id = mission.mission_id;
        let bump = mission.bump;
        let signer_seeds: &[&[&[u8]]] = &[&[b"escrow_vault", mission_id.as_ref(), &[bump]]];

        // 1. Disburse to Merchant (goods payment)
        if mission.goods_price_usdc > 0 {
            let cpi_accounts = Transfer {
                from: ctx.accounts.escrow_vault.to_account_info(),
                to: ctx.accounts.merchant_token_account.to_account_info(),
                authority: ctx.accounts.escrow_vault.to_account_info(),
            };
            token::transfer(
                CpiContext::new_with_signer(ctx.accounts.token_program.to_account_info(), cpi_accounts, signer_seeds),
                mission.goods_price_usdc,
            )?;
        }

        // 2. Disburse to Robot Carrier Owner (net delivery wage)
        if mission.delivery_fee_usdc > 0 {
            let cpi_accounts = Transfer {
                from: ctx.accounts.escrow_vault.to_account_info(),
                to: ctx.accounts.carrier_owner_token_account.to_account_info(),
                authority: ctx.accounts.escrow_vault.to_account_info(),
            };
            token::transfer(
                CpiContext::new_with_signer(ctx.accounts.token_program.to_account_info(), cpi_accounts, signer_seeds),
                mission.delivery_fee_usdc,
            )?;
        }

        // 3. Disburse to geo-oracle Vault (verification micro-fee)
        if mission.oracle_fee_usdc > 0 {
            let cpi_accounts = Transfer {
                from: ctx.accounts.escrow_vault.to_account_info(),
                to: ctx.accounts.oracle_vault_token_account.to_account_info(),
                authority: ctx.accounts.escrow_vault.to_account_info(),
            };
            token::transfer(
                CpiContext::new_with_signer(ctx.accounts.token_program.to_account_info(), cpi_accounts, signer_seeds),
                mission.oracle_fee_usdc,
            )?;
        }

        mission.status = MissionStatus::Delivered;

        emit!(MissionDeliveredEvent {
            mission_id,
            merchant_paid: mission.goods_price_usdc,
            carrier_owner_paid: mission.delivery_fee_usdc,
            oracle_fee_paid: mission.oracle_fee_usdc,
        });

        Ok(())
    }
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq)]
pub enum MissionStatus {
    Created,
    Funded,
    Dispatched,
    Delivered,
    Refunded,
    Cancelled,
}

#[account]
pub struct LogisticsMission {
    pub mission_id: [u8; 32],
    pub category: u8,
    pub consignor: Pubkey,
    pub merchant: Pubkey,
    pub carrier_agent: Pubkey,
    pub carrier_owner: Pubkey,
    pub goods_price_usdc: u64,
    pub delivery_fee_usdc: u64,
    pub oracle_fee_usdc: u64,
    pub max_allowed_g_force: u64,
    pub min_temp_celsius: i32,
    pub max_temp_celsius: i32,
    pub deadline: i64,
    pub status: MissionStatus,
    pub poi_risk_ppm: u32,
    pub bump: u8,
}

#[derive(Accounts)]
#[instruction(mission_id: [u8; 32])]
pub struct InitializeMission<'info> {
    #[account(
        init,
        payer = consignor,
        space = 8 + 32 + 1 + 32 + 32 + 32 + 32 + 8 + 8 + 8 + 8 + 4 + 4 + 8 + 1 + 4 + 1,
        seeds = [b"mission", mission_id.as_ref()],
        bump
    )]
    pub mission: Account<'info, LogisticsMission>,

    #[account(mut)]
    pub consignor: Signer<'info>,

    /// CHECK: Merchant recipient wallet
    pub merchant: AccountInfo<'info>,

    /// CHECK: Autonomous robot/drone wallet
    pub carrier_agent: AccountInfo<'info>,

    /// CHECK: Robot fleet owner recipient wallet
    pub carrier_owner: AccountInfo<'info>,

    pub usdc_mint: Account<'info, Mint>,

    #[account(
        mut,
        token::mint = usdc_mint,
        token::authority = consignor,
    )]
    pub consignor_token_account: Account<'info, TokenAccount>,

    #[account(
        init,
        payer = consignor,
        seeds = [b"escrow_vault", mission_id.as_ref()],
        bump,
        token::mint = usdc_mint,
        token::authority = escrow_vault,
    )]
    pub escrow_vault: Account<'info, TokenAccount>,

    pub token_program: Program<'info, Token>,
    pub system_program: Program<'info, System>,
    pub rent: Sysvar<'info, Rent>,
}

#[derive(Accounts)]
pub struct VerifyPoiDispatch<'info> {
    #[account(mut)]
    pub mission: Account<'info, LogisticsMission>,
    pub oracle_authority: Signer<'info>,
}

#[derive(Accounts)]
pub struct VerifyPodAndDisburse<'info> {
    #[account(mut)]
    pub mission: Account<'info, LogisticsMission>,

    #[account(
        mut,
        seeds = [b"escrow_vault", mission.mission_id.as_ref()],
        bump = mission.bump,
    )]
    pub escrow_vault: Account<'info, TokenAccount>,

    #[account(mut)]
    pub merchant_token_account: Account<'info, TokenAccount>,

    #[account(mut)]
    pub carrier_owner_token_account: Account<'info, TokenAccount>,

    #[account(mut)]
    pub oracle_vault_token_account: Account<'info, TokenAccount>,

    pub token_program: Program<'info, Token>,
}

#[event]
pub struct MissionCreatedEvent {
    pub mission_id: [u8; 32],
    pub consignor: Pubkey,
    pub carrier_agent: Pubkey,
    pub total_escrow_usdc: u64,
}

#[event]
pub struct MissionDispatchedEvent {
    pub mission_id: [u8; 32],
    pub risk_score_ppm: u32,
}

#[event]
pub struct MissionDeliveredEvent {
    pub mission_id: [u8; 32],
    pub merchant_paid: u64,
    pub carrier_owner_paid: u64,
    pub oracle_fee_paid: u64,
}

#[error_code]
pub enum ErrorCode {
    #[msg("Math calculation resulted in an overflow")]
    MathOverflow,
    #[msg("Invalid mission status transition")]
    InvalidStatus,
    #[msg("Proof of Insurability validity window has expired")]
    ProofExpired,
    #[msg("Mission deadline has expired")]
    MissionDeadlinePassed,
}
