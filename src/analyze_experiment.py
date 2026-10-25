#!/usr/bin/env python3
"""Estimate synthetic randomized-experiment ITT effects and write auditable outputs."""
from __future__ import annotations
import argparse, json, hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.formula.api as smf

try:  # supports both `python src/analyze_experiment.py` and `import src.analyze_experiment`
    from .validate_data import load_frames, validate_frames
except ImportError:  # pragma: no cover - exercised by script entry point
    from validate_data import load_frames, validate_frames

OUTCOMES = {
    "post_contribution": "Cumulative Apr-Jun contribution per randomized member ($)",
    "post_transactions": "Cumulative Apr-Jun transactions per randomized member",
    "post_net_sales": "Cumulative Apr-Jun net sales per randomized member ($)",
    "post_purchaser": "Share of randomized members with >=1 Apr-Jun transaction",
    "post_benefit_cost": "Cumulative Apr-Jun benefit cost per randomized member ($)",
}


def welch_difference(x: np.ndarray, y: np.ndarray, alpha: float = 0.05) -> dict:
    """Treatment minus control mean difference with Welch-Satterthwaite CI/test."""
    x = np.asarray(x, dtype=float); y = np.asarray(y, dtype=float)
    x = x[np.isfinite(x)]; y = y[np.isfinite(y)]
    if len(x) < 2 or len(y) < 2: raise ValueError("Each experiment arm needs at least two observations")
    mx, my = x.mean(), y.mean()
    vx, vy = x.var(ddof=1), y.var(ddof=1)
    se2 = vx / len(x) + vy / len(y)
    se = float(np.sqrt(se2))
    df = (se2 ** 2) / (((vx / len(x)) ** 2) / (len(x) - 1) + ((vy / len(y)) ** 2) / (len(y) - 1)) if se2 > 0 else float("inf")
    crit = float(stats.t.ppf(1 - alpha / 2, df)) if np.isfinite(df) else 1.959963984540054
    t_stat = (mx - my) / se if se > 0 else 0.0
    p_raw = float(2 * stats.t.sf(abs(t_stat), df)) if se > 0 else (1.0 if mx == my else 0.0)
    # Floating-point survival probabilities can underflow to exactly zero for very large statistics.
    # Preserve a positive numeric floor and flag it rather than presenting p=0 as a literal probability.
    p_underflow_floor_applied = p_raw == 0.0
    p = max(p_raw, 1e-300)
    return {"n_treatment": int(len(x)), "n_control": int(len(y)), "mean_treatment": float(mx), "mean_control": float(my), "difference_treatment_minus_control": float(mx-my), "standard_error_welch": se, "ci95_low": float(mx-my-crit*se), "ci95_high": float(mx-my+crit*se), "p_value_two_sided": p, "p_value_underflow_floor_applied": p_underflow_floor_applied, "degrees_freedom_welch": float(df)}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_analysis(data_dir: Path, out_dir: Path) -> dict:
    # Do not estimate effects from an invalid or partially loaded panel. The local
    # validator is the analysis precondition, not an optional follow-up step.
    raw_frames = load_frames(data_dir)
    validation_errors = validate_frames(raw_frames)
    if validation_errors:
        raise ValueError("Input data validation failed; analysis stopped:\n- " + "\n- ".join(validation_errors))

    input_manifest = {}
    for name in sorted(raw_frames):
        csv_path = data_dir / f"{name}.csv"
        input_manifest[csv_path.name] = {
            "rows": int(len(raw_frames[name])),
            "sha256": _sha256(csv_path),
        }
    metadata_path = data_dir / "generation_metadata.json"
    if not metadata_path.exists():
        raise FileNotFoundError(
            f"Required provenance file missing: {metadata_path}. Run src/generate_data.py before analysis."
        )
    generation_metadata = json.loads(metadata_path.read_text())
    if generation_metadata.get("metadata_schema_version") != 1:
        raise ValueError("Unsupported or missing generation_metadata.json schema version; regenerate the data.")
    if int(generation_metadata.get("n_members", -1)) != len(raw_frames["raw_members"]):
        raise ValueError("generation_metadata.json member count does not match raw_members.csv.")
    expected_months = ["2026-01-01", "2026-02-01", "2026-03-01", "2026-04-01", "2026-05-01", "2026-06-01"]
    if generation_metadata.get("months") != expected_months:
        raise ValueError("generation_metadata.json month list does not match the project analysis window.")
    run_identity = {
        "input_manifest": input_manifest,
        "generation_metadata": generation_metadata,
        "analysis_code_version": "1.1.0",
    }
    manifest_blob = json.dumps(run_identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    analysis_run_id = hashlib.sha256(manifest_blob).hexdigest()[:16]

    members = pd.read_csv(data_dir / "raw_members.csv", parse_dates=["enrollment_date", "assignment_date"])
    mm = pd.read_csv(data_dir / "raw_member_month.csv", parse_dates=["month_start"])
    events = pd.read_csv(data_dir / "raw_benefit_events.csv", parse_dates=["month_start"])
    members["eligible_for_experiment"] = members.eligible_for_experiment.astype(str).str.lower().isin(["true", "1"])
    mm["active_at_start"] = mm.active_at_start.astype(str).str.lower().isin(["true", "1"])
    events["benefit_used_flag"] = events.benefit_used_flag.astype(str).str.lower().isin(["true", "1"])
    events["eligible_flag"] = events.eligible_flag.astype(str).str.lower().isin(["true", "1"])
    events["campaign_exposed_flag"] = events.campaign_exposed_flag.astype(str).str.lower().isin(["true", "1"])
    assigned = members[members.eligible_for_experiment & members.assignment_group.isin(["TREATMENT", "CONTROL"])].copy()
    if assigned.member_id.nunique() != len(assigned): raise ValueError("Duplicate members in randomized analysis population")
    pre = mm[mm.month_start < pd.Timestamp("2026-04-01")].groupby("member_id", as_index=False).agg(pre_contribution=("contribution", "sum"), pre_transactions=("transaction_count", "sum"), pre_net_sales=("net_sales", "sum"))
    post = mm[mm.month_start >= pd.Timestamp("2026-04-01")].groupby("member_id", as_index=False).agg(post_contribution=("contribution", "sum"), post_transactions=("transaction_count", "sum"), post_net_sales=("net_sales", "sum"), post_active_months=("active_at_start", "sum"))
    post["post_purchaser"] = (post.post_transactions > 0).astype(int)
    ev = events[events.month_start >= pd.Timestamp("2026-04-01")].groupby("member_id", as_index=False).agg(post_benefit_cost=("benefit_cost", "sum"), post_eligible_events=("eligible_flag", "sum"), post_exposed_events=("campaign_exposed_flag", "sum"), post_used_events=("benefit_used_flag", "sum"))
    assigned_event_ids = set(ev.member_id)
    missing_event_members = set(assigned.member_id) - assigned_event_ids
    if missing_event_members: raise ValueError(f"Benefit-event rows missing for {len(missing_event_members)} randomized members; do not convert missing events to zero")
    event_counts = events[events.month_start >= pd.Timestamp("2026-04-01")].groupby("member_id").size()
    if not event_counts.reindex(assigned.member_id).eq(3).all(): raise ValueError("Every randomized member must have exactly three post-period benefit-event rows")
    analysis = assigned.merge(pre, on="member_id", how="left", validate="one_to_one").merge(post, on="member_id", how="left", validate="one_to_one").merge(ev, on="member_id", how="left", validate="one_to_one")
    required_analysis = list(OUTCOMES) + ["pre_contribution", "pre_transactions", "pre_net_sales", "post_eligible_events", "post_exposed_events", "post_used_events"]
    if analysis[required_analysis].isna().any().any(): raise ValueError("Outcome/covariate data missing for randomized members; do not silently drop or zero-fill randomized members")
    if len(analysis) != len(assigned): raise ValueError("Analysis population changed after joins")
    results = {}
    for outcome, description in OUTCOMES.items():
        t = analysis.loc[analysis.assignment_group == "TREATMENT", outcome].to_numpy()
        c = analysis.loc[analysis.assignment_group == "CONTROL", outcome].to_numpy()
        results[outcome] = {"description": description, **welch_difference(t, c)}
    # Covariate-adjusted sensitivity model; randomization remains the primary design.
    # HC3 adjusts standard errors for heteroskedasticity, not unmeasured confounding.
    model = smf.ols("post_contribution ~ C(assignment_group, Treatment(reference='CONTROL')) + pre_contribution + C(tier_at_launch) + C(acquisition_channel)", data=analysis).fit(cov_type="HC3")
    term = "C(assignment_group, Treatment(reference='CONTROL'))[T.TREATMENT]"
    adjusted = {"formula": "post_contribution ~ treatment + pre_contribution + tier + acquisition_channel", "covariance": "HC3 robust", "n": int(model.nobs), "r_squared": float(model.rsquared), "treatment_coefficient": float(model.params[term]), "standard_error": float(model.bse[term]), "ci95_low": float(model.conf_int().loc[term, 0]), "ci95_high": float(model.conf_int().loc[term, 1]), "p_value": float(model.pvalues[term]), "interpretation": "Adjusted sensitivity analysis; primary estimate is unadjusted randomized ITT difference."}
    # Funnel rates use event grain and are descriptive, not causal estimates of redemption impact.
    post_events = events[events.month_start >= pd.Timestamp("2026-04-01")].copy()
    post_events["exposed_and_used"] = post_events["campaign_exposed_flag"] & post_events["benefit_used_flag"]
    post_events["unexposed_used"] = (~post_events["campaign_exposed_flag"]) & post_events["benefit_used_flag"]
    funnel = post_events.groupby("member_id").agg(eligible=("eligible_flag", "sum"), exposed=("campaign_exposed_flag", "sum"), used=("benefit_used_flag", "sum"), exposed_and_used=("exposed_and_used", "sum"), unexposed_used=("unexposed_used", "sum"), cost=("benefit_cost", "sum")).reset_index().merge(assigned[["member_id", "assignment_group"]], on="member_id", how="inner", validate="one_to_one")
    funnel_summary = {}
    for group, frame in funnel.groupby("assignment_group"):
        eligible_count = int(frame.eligible.sum()); exposed_count = int(frame.exposed.sum()); used_count = int(frame.used.sum()); exposed_used_count = int(frame.exposed_and_used.sum())
        funnel_summary[group] = {"members": int(len(frame)), "eligible_events": eligible_count, "exposed_events": exposed_count, "used_events_total_including_unexposed_organic_use": used_count, "exposed_and_used_events": exposed_used_count, "unexposed_used_events": int(frame.unexposed_used.sum()), "exposure_per_eligible_event": exposed_count / eligible_count if eligible_count else None, "use_per_exposed_event": exposed_used_count / exposed_count if exposed_count else None, "use_per_eligible_event": used_count / eligible_count if eligible_count else None, "benefit_cost_total": round(float(frame.cost.sum()), 2)}
    results_doc = {
        "results_schema_version": 1,
        "analysis_run_id": analysis_run_id,
        "analysis_code_version": "1.1.0",
        "project": "Rewards Value Realization & Incrementality Lab",
        "synthetic_data_only": True,
        "generation_seed": generation_metadata.get("seed"),
        "requested_member_count": generation_metadata.get("n_members"),
        "synthetic_dgp_parameters": {
            "planted_exposed_member_transaction_intensity_multiplier": generation_metadata.get("synthetic_planted_exposed_member_transaction_intensity_multiplier"),
            "campaign_exposure_probability_among_eligible_treatment_member_months": generation_metadata.get("synthetic_campaign_exposure_probability_among_eligible_treatment_member_months"),
        },
        "input_manifest": input_manifest,
        "analysis_population_n": int(len(analysis)),
        "secondary_outcomes_are_exploratory": True,
        "analysis_population": "Members eligible and randomized on 2026-04-01; members remain in ITT regardless of subsequent inactivity/attrition.",
        "primary_estimand": "Treatment minus control mean cumulative contribution per randomized member during Apr-Jun 2026, including zero-transaction months and all modeled costs.",
        "primary_result": results["post_contribution"],
        "outcomes": results,
        "adjusted_sensitivity_model": adjusted,
        "benefit_funnel_descriptive_only": funnel_summary,
        "causal_guardrails": [
            "Use assignment group (ITT), not actual exposure or redemption, for the primary causal comparison.",
            "Do not interpret synthetic estimates as Starbucks actual performance.",
            "A non-significant estimate is not proof of no effect.",
            "Benefit funnel metrics are descriptive and do not establish incrementality.",
            "Secondary outcomes are exploratory; the primary estimand is cumulative post-period contribution per randomized member.",
        ],
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    analysis.to_csv(out_dir / "member_level_analysis.csv", index=False)
    (out_dir / "experiment_results.json").write_text(json.dumps(results_doc, indent=2, allow_nan=False) + "\n")
    pd.DataFrame([{"outcome": k, **v} for k, v in results.items()]).to_csv(out_dir / "experiment_effects.csv", index=False)

    # Looker Studio uses a small, versioned result table for Python-derived inferential
    # statistics. BigQuery supplies the member/month trends; this file supplies exact
    # Welch intervals and the separately labeled adjusted HC3 sensitivity estimate.
    dashboard_rows = []
    for outcome, result in results.items():
        dashboard_rows.append({
            "analysis_run_id": analysis_run_id,
            "analysis_code_version": "1.1.0",
            "synthetic_data_only": True,
            "result_type": "ITT_OUTCOME",
            "outcome": outcome,
            "description": result["description"],
            "is_primary": outcome == "post_contribution",
            "n_treatment": result["n_treatment"],
            "n_control": result["n_control"],
            "mean_treatment": result["mean_treatment"],
            "mean_control": result["mean_control"],
            "effect_estimate": result["difference_treatment_minus_control"],
            "standard_error": result["standard_error_welch"],
            "ci95_low": result["ci95_low"],
            "ci95_high": result["ci95_high"],
            "p_value_two_sided": result["p_value_two_sided"],
            "p_value_underflow_floor_applied": result["p_value_underflow_floor_applied"],
            "degrees_freedom": result["degrees_freedom_welch"],
            "r_squared": None,
        })
    dashboard_rows.append({
        "analysis_run_id": analysis_run_id,
        "analysis_code_version": "1.1.0",
        "synthetic_data_only": True,
        "result_type": "ADJUSTED_SENSITIVITY",
        "outcome": "adjusted_post_contribution",
        "description": "Adjusted contribution effect; HC3 robust OLS sensitivity model",
        "is_primary": False,
        "n_treatment": None,
        "n_control": None,
        "mean_treatment": None,
        "mean_control": None,
        "effect_estimate": adjusted["treatment_coefficient"],
        "standard_error": adjusted["standard_error"],
        "ci95_low": adjusted["ci95_low"],
        "ci95_high": adjusted["ci95_high"],
        "p_value_two_sided": adjusted["p_value"],
        "p_value_underflow_floor_applied": False,
        "degrees_freedom": None,
        "r_squared": adjusted["r_squared"],
    })
    dashboard_df = pd.DataFrame(dashboard_rows)
    # Preserve sample sizes as integer literals in CSV despite NULLs in the
    # adjusted-sensitivity row; BigQuery schema declares these columns INT64.
    for count_col in ("n_treatment", "n_control"):
        dashboard_df[count_col] = pd.array(dashboard_df[count_col], dtype="Int64")
    dashboard_df.to_csv(out_dir / "looker_studio_results.csv", index=False)
    print("PRIMARY ITT RESULT: cumulative post-period contribution per randomized member")
    print(json.dumps(results["post_contribution"], indent=2))
    print(f"Wrote {out_dir / 'experiment_results.json'}")
    return results_doc


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", type=Path, default=Path("data/generated"))
    p.add_argument("--out-dir", type=Path, default=Path("outputs"))
    args = p.parse_args()
    run_analysis(args.data_dir, args.out_dir)

if __name__ == "__main__": main()
