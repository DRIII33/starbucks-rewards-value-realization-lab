#!/usr/bin/env python3
"""Generate a deterministic, explicitly synthetic Starbucks Rewards experiment dataset.

This is a portfolio simulation, not Starbucks internal data. The data-generating
process (DGP) intentionally plants a defined assignment effect on transaction
intensity for treatment members during Apr-Jun 2026. The analysis must estimate
that effect from generated outcomes; it must not hard-code the planted value.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import json
import numpy as np
import pandas as pd

SEED_DEFAULT = 20261022
MONTHS = pd.date_range("2026-01-01", "2026-06-01", freq="MS")
TIERS = ["GREEN", "GOLD", "RESERVE"]
TIER_PROBS = [0.65, 0.28, 0.07]
CHANNELS = ["APP", "IN_STORE", "WEB", "REFERRAL"]
CHANNEL_PROBS = [0.45, 0.30, 0.15, 0.10]
REGIONS = ["WEST", "CENTRAL", "EAST", "SOUTH"]
REGION_PROBS = [0.25, 0.25, 0.25, 0.25]


def gamma_poisson(rng: np.random.Generator, mean: float, dispersion: float = 2.5) -> int:
    """Negative-binomial-like count draw via Gamma-Poisson mixture."""
    if mean <= 0:
        return 0
    lam = rng.gamma(shape=dispersion, scale=mean / dispersion)
    return int(rng.poisson(lam))


def generate_dataset(n_members: int = 20_000, seed: int = SEED_DEFAULT) -> dict[str, pd.DataFrame]:
    if n_members < 200:
        raise ValueError("n_members must be >= 200 to support meaningful experiment diagnostics")
    rng = np.random.default_rng(seed)
    member_ids = np.array([f"M{i:06d}" for i in range(1, n_members + 1)])
    tiers = rng.choice(TIERS, n_members, p=TIER_PROBS)
    channels = rng.choice(CHANNELS, n_members, p=CHANNEL_PROBS)
    regions = rng.choice(REGIONS, n_members, p=REGION_PROBS)
    enrollment_days = rng.integers(30, 1500, n_members)
    enrollment_dates = pd.Timestamp("2026-01-01") - pd.to_timedelta(enrollment_days, unit="D")

    # Persistent customer-level heterogeneity: each member has a latent frequency
    # propensity and ticket-size tendency that persist across all six months.
    latent_frequency = rng.lognormal(mean=0.0, sigma=0.48, size=n_members)
    tier_frequency = np.select([tiers == "GOLD", tiers == "RESERVE"], [1.12, 1.25], default=1.0)
    channel_frequency = np.select([channels == "APP", channels == "REFERRAL", channels == "WEB"], [1.08, 1.04, 0.98], default=1.0)
    base_daily_rate = np.clip(0.075 * latent_frequency * tier_frequency * channel_frequency, 0.010, 0.30)
    ticket_propensity = rng.lognormal(mean=0.0, sigma=0.16, size=n_members)

    # Correlated latent engagement influences both churn risk and purchase frequency.
    engagement_score = np.log(latent_frequency) + rng.normal(0, 0.35, n_members)
    active = np.ones(n_members, dtype=bool)
    member_records = []
    monthly_records = []
    benefit_records = []
    # Seasonality and a shared monthly demand shock are explicit synthetic assumptions.
    seasonality = np.array([0.95, 1.00, 1.06, 1.02, 1.09, 1.11])
    market_index = np.array([100.0, 101.0, 103.0, 102.0, 104.0, 106.0])
    market_noise = rng.normal(0, 0.012, len(MONTHS))
    month_shock = seasonality * (1 + market_noise)
    # Pass 1: generate pre-period outcomes and churn transitions, Jan-Mar.
    for mi, month in enumerate(MONTHS[:3]):
        for i, mid in enumerate(member_ids):
            is_active = bool(active[i])
            tx = gamma_poisson(rng, base_daily_rate[i] * 30.4375 * month_shock[mi]) if is_active else 0
            avg_ticket = float(np.clip(9.25 * ticket_propensity[i] * rng.lognormal(0, 0.12), 3.5, 35.0))
            sales = round(tx * avg_ticket, 2)
            variable_cost = round(sales * float(rng.uniform(0.56, 0.68)), 2)
            reward_cost = round(sales * float(rng.uniform(0.018, 0.032)), 2)
            contribution = round(sales - variable_cost - reward_cost, 2)
            # Attrition occurs after this month's purchase opportunity; active_at_end
            # records the resulting state used to determine next month's activity.
            if active[i]:
                churn_p = float(np.clip(0.018 * np.exp(-0.22 * engagement_score[i]), 0.006, 0.035))
                if rng.random() < churn_p:
                    active[i] = False
            monthly_records.append({
                "member_id": mid, "month_start": month, "period_phase": "PRE",
                "active_at_start": is_active, "active_at_end": bool(active[i]),
                "transaction_count": tx, "net_sales": sales, "variable_cost": variable_cost,
                "reward_cost": reward_cost, "benefit_cost": 0.0, "intervention_cost": 0.0,
                "contribution": contribution,
            })
        # The updated `active` state carries forward into the next month.

    eligible = active.copy()  # active at the end of March / experiment assignment date
    assignment = np.full(n_members, "NOT_ELIGIBLE", dtype=object)
    assignment_prob = np.full(n_members, np.nan)
    # Stratified random assignment by tier among eligible members; reproducible order.
    for tier in TIERS:
        idx = np.flatnonzero(eligible & (tiers == tier))
        # Independent Bernoulli assignment within tier gives each eligible member
        # a known 0.5 treatment probability while preserving stratification.
        treatment_mask = rng.random(len(idx)) < 0.5
        treatment_idx = idx[treatment_mask]
        control_idx = idx[~treatment_mask]
        assignment[treatment_idx] = "TREATMENT"
        assignment[control_idx] = "CONTROL"
        assignment_prob[idx] = 0.5
    assignment_date = pd.Timestamp("2026-04-01")

    # Pass 2: post-period outcomes. ITT is defined by randomized assignment, not exposure/redemption.
    for post_offset, month in enumerate(MONTHS[3:], start=3):
        for i, mid in enumerate(member_ids):
            is_active = bool(active[i])
            group = assignment[i]
            is_treatment = group == "TREATMENT"
            # Exposure is sampled before outcomes so the DGP is internally aligned:
            # assignment -> campaign delivery -> transaction intensity. The 15% uplift
            # applies only to actively exposed treatment members; the ITT effect is diluted
            # by the 80% delivery probability. This is a synthetic DGP parameter, not a result.
            event_eligible = bool(eligible[i] and is_active)
            exposed = bool(event_eligible and is_treatment and (rng.random() < 0.80))
            effect_multiplier = 1.15 if exposed else 1.0
            mean_tx = base_daily_rate[i] * 30.4375 * month_shock[post_offset] * effect_multiplier
            tx = gamma_poisson(rng, mean_tx) if is_active else 0
            avg_ticket = float(np.clip(9.25 * ticket_propensity[i] * rng.lognormal(0, 0.12), 3.5, 35.0))
            sales = round(tx * avg_ticket, 2)
            variable_cost = round(sales * float(rng.uniform(0.56, 0.68)), 2)
            reward_cost = round(sales * float(rng.uniform(0.018, 0.032)), 2)

            # One synthetic benefit opportunity per randomized member-month, even when inactive;
            # eligibility/exposure flags explain why an inactive member cannot be exposed.
            event_id = f"B{(post_offset - 3) * n_members + i + 1:08d}"
            organic_use_p = 0.045 if event_eligible else 0.0
            use_p = (0.30 if exposed else organic_use_p) if event_eligible else 0.0
            used = bool(event_eligible and (rng.random() < use_p))
            benefit_cost = round(float(rng.uniform(0.50, 1.50)), 2) if used else 0.0
            intervention_cost = round(0.10, 2) if exposed else 0.0
            benefit_records.append({
                "event_id": event_id, "member_id": mid, "month_start": month,
                "benefit_id": "TARGETED_REWARD_V1", "eligible_flag": event_eligible,
                "campaign_exposed_flag": exposed, "benefit_used_flag": used,
                "benefit_cost": benefit_cost,
            })
            contribution = round(sales - variable_cost - reward_cost - benefit_cost - intervention_cost, 2)
            # As above, churn is a month-end transition after this month's outcome.
            if active[i]:
                churn_p = float(np.clip(0.018 * np.exp(-0.22 * engagement_score[i]), 0.006, 0.035))
                if rng.random() < churn_p:
                    active[i] = False
            monthly_records.append({
                "member_id": mid, "month_start": month, "period_phase": "POST",
                "active_at_start": is_active, "active_at_end": bool(active[i]),
                "transaction_count": tx, "net_sales": sales, "variable_cost": variable_cost,
                "reward_cost": reward_cost, "benefit_cost": benefit_cost,
                "intervention_cost": intervention_cost, "contribution": contribution,
            })

    # Build member records after assignment so every documented field is present.
    for i, mid in enumerate(member_ids):
        member_records.append({
            "member_id": mid, "enrollment_date": pd.Timestamp(enrollment_dates[i]),
            "tier_at_launch": tiers[i], "acquisition_channel": channels[i],
            "region_group": regions[i], "prior_90d_transactions": int(round(base_daily_rate[i] * 90)),
            "prior_90d_net_sales": round(float(base_daily_rate[i] * 90 * 9.25 * ticket_propensity[i]), 2),
            "eligible_for_experiment": bool(eligible[i]),
            "assignment_group": assignment[i], "assignment_date": assignment_date if eligible[i] else pd.NaT,
            "assignment_probability": assignment_prob[i],
        })

    members = pd.DataFrame(member_records)
    member_month = pd.DataFrame(monthly_records)
    benefit_events = pd.DataFrame(benefit_records)
    market_context = pd.DataFrame({
        "month_start": MONTHS,
        "market_index": market_index,
        "seasonality_index": seasonality,
        "source_type": ["SYNTHETIC_ASSUMPTION"] * len(MONTHS),
    })
    # Explicit, stable types for CSV round-tripping and BigQuery ingestion.
    members["enrollment_date"] = pd.to_datetime(members["enrollment_date"]).dt.strftime("%Y-%m-%d")
    members["assignment_date"] = pd.to_datetime(members["assignment_date"]).dt.strftime("%Y-%m-%d")
    member_month["month_start"] = pd.to_datetime(member_month["month_start"]).dt.strftime("%Y-%m-%d")
    benefit_events["month_start"] = pd.to_datetime(benefit_events["month_start"]).dt.strftime("%Y-%m-%d")
    market_context["month_start"] = pd.to_datetime(market_context["month_start"]).dt.strftime("%Y-%m-%d")
    return {
        "raw_members": members,
        "raw_member_month": member_month,
        "raw_benefit_events": benefit_events,
        "raw_market_context": market_context,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--members", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=SEED_DEFAULT)
    parser.add_argument("--out", type=Path, default=Path("data/generated"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    frames = generate_dataset(args.members, args.seed)
    for name, frame in frames.items():
        frame.to_csv(args.out / f"{name}.csv", index=False)
        print(f"Wrote {name}.csv: {len(frame):,} rows, {len(frame.columns)} columns")
    metadata = {
        "metadata_schema_version": 1,
        "generator_version": "1.1.0",
        "seed": args.seed, "n_members": args.members,
        "months": [m.strftime("%Y-%m-%d") for m in MONTHS],
        "synthetic_planted_exposed_member_transaction_intensity_multiplier": 1.15,
        "synthetic_campaign_exposure_probability_among_eligible_treatment_member_months": 0.80,
        "warning": "Synthetic data only. Planted parameter is not a result or Starbucks fact; ITT estimate is diluted by exposure and attrition.",
    }
    (args.out / "generation_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Metadata: {args.out / 'generation_metadata.json'}")

if __name__ == "__main__":
    main()
