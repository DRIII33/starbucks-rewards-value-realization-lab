#!/usr/bin/env python3
"""Fail-fast structural, relational, and financial validation for generated CSVs."""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

REQUIRED = {
    "raw_members": {"member_id", "enrollment_date", "tier_at_launch", "acquisition_channel", "region_group", "prior_90d_transactions", "prior_90d_net_sales", "eligible_for_experiment", "assignment_group", "assignment_date", "assignment_probability"},
    "raw_member_month": {"member_id", "month_start", "period_phase", "active_at_start", "active_at_end", "transaction_count", "net_sales", "variable_cost", "reward_cost", "benefit_cost", "intervention_cost", "contribution"},
    "raw_benefit_events": {"event_id", "member_id", "month_start", "benefit_id", "eligible_flag", "campaign_exposed_flag", "benefit_used_flag", "benefit_cost"},
    "raw_market_context": {"month_start", "market_index", "seasonality_index", "source_type"},
}


def load_frames(data_dir: Path) -> dict[str, pd.DataFrame]:
    frames = {}
    for name in REQUIRED:
        path = data_dir / f"{name}.csv"
        if not path.exists():
            raise FileNotFoundError(f"Required file missing: {path}")
        frames[name] = pd.read_csv(path)
    return frames


def validate_frames(frames: dict[str, pd.DataFrame], tolerance: float = 0.011) -> list[str]:
    errors: list[str] = []
    for name, required in REQUIRED.items():
        missing = required - set(frames[name].columns)
        if missing:
            errors.append(f"{name}: missing columns {sorted(missing)}")
    if errors:
        return errors
    m = frames["raw_members"]
    mm = frames["raw_member_month"]
    be = frames["raw_benefit_events"]
    mc = frames["raw_market_context"]
    if m.member_id.isna().any() or m.member_id.duplicated().any(): errors.append("raw_members.member_id must be non-null and unique")
    if mm[["member_id", "month_start"]].isna().any().any() or mm.duplicated(["member_id", "month_start"]).any(): errors.append("raw_member_month key (member_id, month_start) must be non-null and unique")
    if be.event_id.isna().any() or be.event_id.duplicated().any(): errors.append("raw_benefit_events.event_id must be non-null and unique")
    if mc.month_start.isna().any() or mc.month_start.duplicated().any(): errors.append("raw_market_context.month_start must be non-null and unique")
    member_ids = set(m.member_id)
    if not set(mm.member_id).issubset(member_ids): errors.append("raw_member_month contains orphan member IDs")
    if not set(be.member_id).issubset(member_ids): errors.append("raw_benefit_events contains orphan member IDs")
    if set(mm.month_start) != set(mc.month_start): errors.append("member-month dates and market-context dates differ")
    for col in ["market_index", "seasonality_index"]:
        values = pd.to_numeric(mc[col], errors="coerce")
        if values.isna().any() or (~np.isfinite(values)).any(): errors.append(f"raw_market_context.{col} must be finite numeric")
    if set(mc.source_type) != {"SYNTHETIC_ASSUMPTION"}: errors.append("market context must be labeled SYNTHETIC_ASSUMPTION")
    expected_months = {"2026-01-01", "2026-02-01", "2026-03-01", "2026-04-01", "2026-05-01", "2026-06-01"}
    if set(mm.month_start) != expected_months: errors.append("member-month panel must cover exactly Jan-Jun 2026")
    if len(mm) != len(m) * 6: errors.append(f"member-month panel expected {len(m)*6:,} rows, found {len(mm):,}")
    per_member_months = mm.groupby("member_id").month_start.nunique()
    if len(per_member_months) != len(m) or (per_member_months != 6).any(): errors.append("every member must have exactly six distinct member-month rows")
    if len(be) != len(m) * 3: errors.append(f"benefit-event table expected {len(m)*3:,} rows, found {len(be):,}")
    if be.duplicated(["member_id", "month_start"]).any(): errors.append("benefit events must have one row per member per post-period month")
    if set(be.month_start.astype(str)) != {"2026-04-01", "2026-05-01", "2026-06-01"}: errors.append("benefit events must cover exactly Apr-Jun 2026")
    event_counts = be.groupby("member_id").month_start.nunique()
    if len(event_counts) != len(m) or (event_counts != 3).any(): errors.append("every member must have exactly three post-period benefit-event rows")
    if not set(m.tier_at_launch).issubset({"GREEN", "GOLD", "RESERVE"}): errors.append("invalid tier_at_launch values")
    if not set(m.acquisition_channel).issubset({"APP", "IN_STORE", "WEB", "REFERRAL"}): errors.append("invalid acquisition_channel values")
    if not set(m.region_group).issubset({"WEST", "CENTRAL", "EAST", "SOUTH"}): errors.append("invalid region_group values")
    if not set(m.assignment_group).issubset({"TREATMENT", "CONTROL", "NOT_ELIGIBLE"}): errors.append("invalid assignment_group values")
    elig = m.eligible_for_experiment.astype(str).str.lower().isin(["true", "1"])
    if (m.loc[elig, "assignment_group"] == "NOT_ELIGIBLE").any(): errors.append("eligible members must be randomized")
    if (m.loc[~elig, "assignment_group"] != "NOT_ELIGIBLE").any(): errors.append("ineligible members must not be randomized")
    if m.loc[elig, "assignment_group"].isna().any(): errors.append("eligible member assignment cannot be null")
    assigned_dates = pd.to_datetime(m.loc[elig, "assignment_date"], errors="coerce")
    if assigned_dates.isna().any() or (assigned_dates != pd.Timestamp("2026-04-01")).any(): errors.append("eligible members must have assignment_date 2026-04-01")
    if m.loc[~elig, "assignment_date"].notna().any(): errors.append("ineligible members must have null assignment_date")
    assigned_prob = pd.to_numeric(m.loc[elig, "assignment_probability"], errors="coerce")
    if assigned_prob.isna().any() or not np.allclose(assigned_prob, 0.5): errors.append("eligible members must have assignment_probability = 0.5")
    ineligible_prob = pd.to_numeric(m.loc[~elig, "assignment_probability"], errors="coerce")
    if ineligible_prob.notna().any(): errors.append("ineligible members must have null assignment_probability")
    if not set(mm.period_phase).issubset({"PRE", "POST"}): errors.append("period_phase must be PRE or POST")
    expected_phase = mm.month_start.astype(str).map(lambda x: "PRE" if x < "2026-04-01" else "POST")
    if (expected_phase != mm.period_phase).any(): errors.append("period_phase does not match month_start boundary")
    march = mm[mm.month_start.astype(str) == "2026-03-01"].set_index("member_id")
    member_eligibility = m.set_index("member_id").eligible_for_experiment.astype(str).str.lower().isin(["true", "1"])
    march_end_active = march.active_at_end.astype(str).str.lower().isin(["true", "1"])
    if not march_end_active.sort_index().equals(member_eligibility.sort_index()): errors.append("eligible_for_experiment must equal March active_at_end")
    # Activity is absorbing: once inactive at month start, a member cannot reactivate.
    activity = mm.assign(month_sort=pd.to_datetime(mm.month_start)).sort_values(["member_id", "month_sort"])
    activity_bool = activity.active_at_start.astype(str).str.lower().isin(["true", "1"])
    if (activity.loc[~activity_bool, "transaction_count"].astype(float) != 0).any(): errors.append("inactive-at-start members must have zero transactions")
    starts = activity.groupby("member_id").active_at_start.apply(lambda s: s.astype(str).str.lower().isin(["true", "1"]).tolist())
    if any(any((not seq[i-1]) and seq[i] for i in range(1, len(seq))) for seq in starts): errors.append("activity must be absorbing; member reactivated after attrition")
    end_flags = activity.groupby("member_id").active_at_end.apply(lambda s: s.astype(str).str.lower().isin(["true", "1"]).tolist())
    for mid in starts.index:
        if starts[mid][1:] != end_flags[mid][:-1]:
            errors.append(f"active_at_end must match next month's active_at_start for member {mid}")
            break
    member_assignment = m.set_index("member_id")["assignment_group"]
    assigned_group_by_month = mm.member_id.map(member_assignment)
    post_mask = mm.month_start.astype(str) >= "2026-04-01"
    if (post_mask & assigned_group_by_month.eq("NOT_ELIGIBLE") & mm.transaction_count.astype(float).gt(0)).any(): errors.append("non-randomized/ineligible members cannot have post-period transactions in this design")
    numeric_cols = ["transaction_count", "net_sales", "variable_cost", "reward_cost", "benefit_cost", "intervention_cost", "contribution"]
    for col in numeric_cols:
        values = pd.to_numeric(mm[col], errors="coerce")
        if values.isna().any() or (~np.isfinite(values)).any(): errors.append(f"raw_member_month.{col} must be finite numeric")
    if (pd.to_numeric(mm.transaction_count, errors="coerce") < 0).any(): errors.append("transaction_count cannot be negative")
    for col in ["net_sales", "variable_cost", "reward_cost", "benefit_cost", "intervention_cost"]:
        if (pd.to_numeric(mm[col], errors="coerce") < 0).any(): errors.append(f"{col} cannot be negative")
    if not np.allclose(pd.to_numeric(mm.transaction_count), np.round(pd.to_numeric(mm.transaction_count))): errors.append("transaction_count must be integer-valued")
    expected_contribution = (pd.to_numeric(mm.net_sales) - pd.to_numeric(mm.variable_cost) - pd.to_numeric(mm.reward_cost) - pd.to_numeric(mm.benefit_cost) - pd.to_numeric(mm.intervention_cost)).round(2)
    diff = (pd.to_numeric(mm.contribution).round(2) - expected_contribution).abs()
    if (diff > tolerance).any(): errors.append(f"contribution reconciliation failed; max absolute difference={diff.max():.4f}")
    bool_cols = [(m, "eligible_for_experiment"), (be, "eligible_flag"), (be, "campaign_exposed_flag"), (be, "benefit_used_flag")]
    for frame, col in bool_cols:
        vals = frame[col].astype(str).str.lower()
        if not vals.isin({"true", "false", "1", "0"}).all(): errors.append(f"{col} must contain only boolean-like values")
    eligible_events = be.eligible_flag.astype(str).str.lower().isin(["true", "1"])
    exposed = be.campaign_exposed_flag.astype(str).str.lower().isin(["true", "1"])
    used = be.benefit_used_flag.astype(str).str.lower().isin(["true", "1"])
    if (exposed & ~eligible_events).any(): errors.append("benefit event cannot be exposed when ineligible")
    if (used & ~eligible_events).any(): errors.append("benefit event cannot be used when ineligible")
    if (exposed & ~used & (pd.to_numeric(be.benefit_cost) < 0)).any(): errors.append("benefit_cost cannot be negative")
    if (pd.to_numeric(be.benefit_cost) < 0).any(): errors.append("benefit_cost cannot be negative")
    if pd.to_numeric(be.benefit_cost, errors="coerce").isna().any() or (~np.isfinite(pd.to_numeric(be.benefit_cost, errors="coerce"))).any(): errors.append("benefit_cost must be finite numeric")
    used_cost = used & (pd.to_numeric(be.benefit_cost) <= 0)
    unused_cost = (~used) & (pd.to_numeric(be.benefit_cost) != 0)
    if used_cost.any(): errors.append("used benefit events must have positive benefit_cost")
    if unused_cost.any(): errors.append("unused benefit events must have zero benefit_cost")
    member_assignment_map = m.set_index("member_id").assignment_group
    event_assignment = be.member_id.map(member_assignment_map)
    if (exposed & event_assignment.ne("TREATMENT")).any(): errors.append("only treatment-assigned members can be campaign-exposed")
    # Reconcile event-level benefit costs to member-month ledger costs.
    event_cost = be.groupby(["member_id", "month_start"], as_index=False).benefit_cost.sum()
    joined = mm.merge(event_cost, on=["member_id", "month_start"], how="left", validate="one_to_one", suffixes=("_ledger", "_events"))
    delta = (joined.benefit_cost_ledger.fillna(0).round(2) - joined.benefit_cost_events.fillna(0).round(2)).abs()
    if (delta > tolerance).any(): errors.append(f"benefit cost event-to-ledger reconciliation failed; max={delta.max():.4f}")
    exposure_by_member_month = be.assign(
        _exposed=be.campaign_exposed_flag.astype(str).str.lower().isin({"true", "1"}).astype(int)
    ).groupby(["member_id", "month_start"], as_index=False)._exposed.sum()
    exposure_join = mm.merge(exposure_by_member_month, on=["member_id", "month_start"], how="left", validate="one_to_one")
    expected_intervention_cost = (exposure_join["_exposed"].fillna(0) * 0.10).round(2)
    actual_intervention_cost = pd.to_numeric(exposure_join["intervention_cost"], errors="coerce").round(2)
    if ((expected_intervention_cost - actual_intervention_cost).abs() > tolerance).any():
        errors.append("intervention_cost must equal $0.10 per exposed event/member-month")
    # Randomization should be close to 50/50 overall and within tier; this is a diagnostic, not an error bound on every tiny stratum.
    em = m.loc[elig].copy()
    if len(em) < 100: errors.append("fewer than 100 eligible randomized members; experiment diagnostics unreliable")
    else:
        counts = em.assignment_group.value_counts()
        if set(counts.index) != {"TREATMENT", "CONTROL"}: errors.append("randomized population must include treatment and control")
        else:
            overall_tolerance = max(0.02, 3 * np.sqrt(0.25 / len(em)))
            if abs(counts["TREATMENT"] / len(em) - 0.5) > overall_tolerance:
                errors.append(f"overall randomized allocation is outside a 3-SD binomial diagnostic band (tolerance={overall_tolerance:.3f})")
            for tier, tier_frame in em.groupby("tier_at_launch"):
                tier_n = len(tier_frame)
                tier_treatment_share = (tier_frame.assignment_group == "TREATMENT").mean()
                tier_tolerance = max(0.05, 3 * np.sqrt(0.25 / tier_n))
                if abs(tier_treatment_share - 0.5) > tier_tolerance:
                    errors.append(f"tier {tier} assignment imbalance outside diagnostic band (n={tier_n}, tolerance={tier_tolerance:.3f})")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data/generated"))
    args = parser.parse_args()
    frames = load_frames(args.data_dir)
    errors = validate_frames(frames)
    if errors:
        print("VALIDATION FAILED")
        for err in errors: print(f" - {err}")
        raise SystemExit(1)
    print("VALIDATION PASSED")
    for name, frame in frames.items(): print(f" - {name}: {len(frame):,} rows")
    members = frames["raw_members"]
    eligible = members[members.eligible_for_experiment.astype(str).str.lower().isin(["true", "1"])]
    print(f" - eligible randomized population: {len(eligible):,}")
    print(eligible.assignment_group.value_counts().to_string())

if __name__ == "__main__": main()
