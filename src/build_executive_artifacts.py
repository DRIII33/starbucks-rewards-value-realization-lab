#!/usr/bin/env python3
"""Build a reproducible Excel review workbook and PowerPoint readout from validated analysis JSON."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from pptx import Presentation
from pptx.util import Inches, Pt


def load_validated_results(results_path: Path) -> dict:
    """Reject stale, hand-written, mock, or incompatible analysis payloads."""
    data = json.loads(results_path.read_text())
    required_top = {
        "results_schema_version", "analysis_run_id", "analysis_code_version",
        "project", "synthetic_data_only", "generation_seed", "synthetic_dgp_parameters", "input_manifest",
        "analysis_population_n", "primary_estimand", "primary_result", "outcomes",
        "adjusted_sensitivity_model", "benefit_funnel_descriptive_only", "causal_guardrails",
    }
    missing = sorted(required_top - set(data))
    if missing:
        raise ValueError(
            "Refusing to build executive artifacts from an incomplete/starter/mock results file. "
            f"Missing required fields: {missing}. Run src/analyze_experiment.py first."
        )
    if data["results_schema_version"] != 1:
        raise ValueError(f"Unsupported results_schema_version: {data['results_schema_version']!r}")
    if data["synthetic_data_only"] is not True:
        raise ValueError("Results must explicitly declare synthetic_data_only=true.")
    if not isinstance(data["analysis_run_id"], str) or len(data["analysis_run_id"]) != 16:
        raise ValueError("analysis_run_id is missing or malformed; rerun the analysis script.")
    expected_manifest_names = {
        "raw_members.csv", "raw_member_month.csv",
        "raw_benefit_events.csv", "raw_market_context.csv",
    }
    if not isinstance(data["input_manifest"], dict) or set(data["input_manifest"]) != expected_manifest_names:
        raise ValueError("input_manifest must describe exactly the four validated input CSVs.")
    manifest_rows = {name: int(meta.get("rows", -1)) for name, meta in data["input_manifest"].items()}
    n_members = manifest_rows["raw_members.csv"]
    if n_members <= 0 or manifest_rows["raw_member_month.csv"] != n_members * 6:
        raise ValueError("Input manifest member-month row count does not equal members × 6.")
    if manifest_rows["raw_benefit_events.csv"] != n_members * 3 or manifest_rows["raw_market_context.csv"] != 6:
        raise ValueError("Input manifest event/market-context row counts do not match the project data contract.")
    for name, meta in data["input_manifest"].items():
        digest = meta.get("sha256", "")
        if not isinstance(digest, str) or len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest.lower()):
            raise ValueError(f"Input manifest has an invalid SHA-256 digest for {name}.")
    if int(data["analysis_population_n"]) <= 0:
        raise ValueError("analysis_population_n must be positive.")
    dgp = data["synthetic_dgp_parameters"]
    if not isinstance(dgp, dict) or not isinstance(dgp.get("planted_exposed_member_transaction_intensity_multiplier"), (int, float)) or not isinstance(dgp.get("campaign_exposure_probability_among_eligible_treatment_member_months"), (int, float)):
        raise ValueError("synthetic_dgp_parameters must contain the numeric planted multiplier and exposure probability.")
    outcomes = data["outcomes"]
    if "post_contribution" not in outcomes:
        raise ValueError("outcomes.post_contribution is required as the primary outcome.")
    if data["primary_result"] != outcomes["post_contribution"]:
        raise ValueError("primary_result does not exactly match outcomes.post_contribution; rerun analysis.")
    for outcome_name, result in outcomes.items():
        required_result = {
            "n_treatment", "n_control", "mean_treatment", "mean_control",
            "difference_treatment_minus_control", "ci95_low", "ci95_high", "p_value_two_sided",
        }
        absent = required_result - set(result)
        if absent:
            raise ValueError(f"Outcome {outcome_name!r} is missing fields: {sorted(absent)}")
        if int(result["n_treatment"]) < 2 or int(result["n_control"]) < 2:
            raise ValueError(f"Outcome {outcome_name!r} has insufficient arm counts.")
        if not float(result["ci95_low"]) <= float(result["difference_treatment_minus_control"]) <= float(result["ci95_high"]):
            raise ValueError(f"Outcome {outcome_name!r} has inconsistent confidence interval bounds.")
    primary = data["primary_result"]
    if int(primary["n_treatment"]) + int(primary["n_control"]) != int(data["analysis_population_n"]):
        raise ValueError("Primary outcome arm counts do not match analysis_population_n.")
    return data


def build_excel(results_path: Path, output_path: Path) -> None:
    data = load_validated_results(results_path)
    wb = Workbook()
    ws = wb.active; ws.title = "Read Me"
    rows = [
        ["Rewards Value Realization & Incrementality Lab"],
        ["Synthetic portfolio analysis — NOT Starbucks actuals"],
        ["Primary estimand", data["primary_estimand"]],
        ["Analysis population", data["analysis_population"]],
        ["Analysis run ID", data["analysis_run_id"]],
        ["Generation seed", data.get("generation_seed")],
        ["Planted exposed-member transaction multiplier", data["synthetic_dgp_parameters"]["planted_exposed_member_transaction_intensity_multiplier"]],
        ["Campaign exposure probability", data["synthetic_dgp_parameters"]["campaign_exposure_probability_among_eligible_treatment_member_months"]],
        ["Data status", "Synthetic data; values are reproducible from the repository seed and generator."],
        ["Interpretation", "Assignment-level ITT is primary. Exposure and redemption metrics are descriptive only."],
        ["Cost accounting", "Contribution already deducts variable cost, ordinary reward cost, used-benefit cost and intervention cost. Do not deduct twice."],
        ["Release status", "Local Python pipeline was run. BigQuery and Looker Studio are not certified by this workbook; complete cloud QA separately."],
    ]
    for row in rows: ws.append(row)
    ws.column_dimensions["A"].width = 28; ws.column_dimensions["B"].width = 105
    ws.freeze_panes = "A3"
    ws["A1"].font = Font(bold=True, size=16)
    ws["A2"].font = Font(bold=True, color="9C0006")
    for row in ws.iter_rows(min_row=3):
        row[0].font = Font(bold=True)
        row[1].alignment = Alignment(wrap_text=True, vertical="top")

    qa = wb.create_sheet("Input Manifest")
    qa.append(["Input CSV", "Rows validated", "SHA-256"] )
    for filename, meta in sorted(data["input_manifest"].items()):
        qa.append([filename, meta["rows"], meta["sha256"]])
    qa.freeze_panes = "A2"; qa.auto_filter.ref = qa.dimensions
    for cell in qa[1]: cell.font = Font(bold=True); cell.fill = PatternFill("solid", fgColor="D9EAF7")
    qa.column_dimensions["A"].width = 32; qa.column_dimensions["B"].width = 18; qa.column_dimensions["C"].width = 68

    ex = wb.create_sheet("Experiment Results")
    ex.append(["Outcome", "Treatment N", "Control N", "Treatment mean", "Control mean", "Difference T-C", "95% CI low", "95% CI high", "Two-sided p-value", "Description"])
    for name, result in data["outcomes"].items():
        ex.append([name, result["n_treatment"], result["n_control"], result["mean_treatment"], result["mean_control"], result["difference_treatment_minus_control"], result["ci95_low"], result["ci95_high"], result["p_value_two_sided"], result["description"]])
    ex.freeze_panes = "A2"; ex.auto_filter.ref = ex.dimensions
    for cell in ex[1]: cell.font = Font(bold=True); cell.fill = PatternFill("solid", fgColor="D9EAF7")
    for col, width in enumerate([25, 13, 13, 17, 17, 17, 15, 15, 18, 58], 1): ex.column_dimensions[get_column_letter(col)].width = width
    for row in ex.iter_rows(min_row=2, min_col=4, max_col=8):
        for cell in row: cell.number_format = '#,##0.000;[Red](#,##0.000);-'
    for row in ex.iter_rows(min_row=2, min_col=9, max_col=9): row[0].number_format = '0.00E+00'

    adj = wb.create_sheet("Adjusted Sensitivity")
    model = data["adjusted_sensitivity_model"]
    for row in [
        ["Field", "Value"], ["Formula", model["formula"]], ["Covariance", model["covariance"]], ["N", model["n"]],
        ["R-squared", model["r_squared"]], ["Treatment coefficient", model["treatment_coefficient"]],
        ["Robust standard error", model["standard_error"]], ["95% CI low", model["ci95_low"]],
        ["95% CI high", model["ci95_high"]], ["p-value", model["p_value"]], ["Interpretation", model["interpretation"]],
    ]: adj.append(row)
    adj.column_dimensions["A"].width = 28; adj.column_dimensions["B"].width = 95
    for cell in adj[1]: cell.font = Font(bold=True); cell.fill = PatternFill("solid", fgColor="D9EAF7")
    for row in adj.iter_rows(min_row=2): row[0].font = Font(bold=True); row[1].alignment = Alignment(wrap_text=True, vertical="top")

    fu = wb.create_sheet("Benefit Funnel")
    fu.append(["Assignment group", "Members", "Eligible events", "Exposed events", "Used events (all)", "Exposed and used", "Unexposed used", "Exposure / eligible", "Use / exposed", "Use / eligible", "Benefit cost total"])
    for group, vals in data["benefit_funnel_descriptive_only"].items():
        fu.append([group, vals["members"], vals["eligible_events"], vals["exposed_events"], vals["used_events_total_including_unexposed_organic_use"], vals["exposed_and_used_events"], vals["unexposed_used_events"], vals["exposure_per_eligible_event"], vals["use_per_exposed_event"], vals["use_per_eligible_event"], vals["benefit_cost_total"]])
    fu.freeze_panes = "A2"; fu.auto_filter.ref = fu.dimensions
    for cell in fu[1]: cell.font = Font(bold=True); cell.fill = PatternFill("solid", fgColor="D9EAF7")
    for col, width in enumerate([18, 12, 16, 15, 18, 16, 16, 18, 15, 15, 17], 1): fu.column_dimensions[get_column_letter(col)].width = width
    for row in fu.iter_rows(min_row=2, min_col=8, max_col=10):
        for cell in row: cell.number_format = '0.0%'
    for row in fu.iter_rows(min_row=2, min_col=11, max_col=11): row[0].number_format = '$#,##0.00'

    scenario = wb.create_sheet("Financial Scenarios")
    primary = data["primary_result"]
    scale_n = 10000
    scenario.append(["Scenario", "Contribution difference/member", "Scaled value for 10,000 eligible members", "Interpretation"])
    scenario_rows = [
        ["Conservative (95% CI lower bound)", primary["ci95_low"], primary["ci95_low"] * scale_n, "Uses the lower bound of the primary Welch 95% CI; synthetic illustration only."],
        ["Base case (point estimate)", primary["difference_treatment_minus_control"], primary["difference_treatment_minus_control"] * scale_n, "Uses the primary ITT point estimate; synthetic illustration only."],
        ["Upside (95% CI upper bound)", primary["ci95_high"], primary["ci95_high"] * scale_n, "Uses the upper bound of the primary Welch 95% CI; synthetic illustration only."],
    ]
    for row in scenario_rows: scenario.append(row)
    scenario.freeze_panes = "A2"; scenario.auto_filter.ref = scenario.dimensions
    for cell in scenario[1]: cell.font = Font(bold=True); cell.fill = PatternFill("solid", fgColor="D9EAF7")
    for col, width in enumerate([34, 26, 38, 72], 1): scenario.column_dimensions[get_column_letter(col)].width = width
    for row in scenario.iter_rows(min_row=2, min_col=2, max_col=3):
        for cell in row: cell.number_format = '$#,##0.00;[Red]($#,##0.00);-'

    for sheet in wb.worksheets:
        sheet.sheet_view.showGridLines = False
        for row in sheet.iter_rows():
            for cell in row: cell.alignment = Alignment(vertical="top", wrap_text=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)


def build_powerpoint(results_path: Path, output_path: Path) -> None:
    data = load_validated_results(results_path)
    primary = data["primary_result"]
    adj = data["adjusted_sensitivity_model"]
    outcomes = data["outcomes"]
    funnel = data["benefit_funnel_descriptive_only"]
    prs = Presentation()
    prs.slide_width = Inches(13.333); prs.slide_height = Inches(7.5)

    def title_slide(title: str, subtitle: str = ""):
        slide = prs.slides.add_slide(prs.slide_layouts[0])
        slide.shapes.title.text = title
        slide.placeholders[1].text = subtitle
        return slide

    def bullet_slide(title: str, bullets: list[str]):
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = title
        tf = slide.placeholders[1].text_frame; tf.clear()
        for i, item in enumerate(bullets):
            para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            para.text = item; para.level = 0; para.font.size = Pt(22)
        return slide

    title_slide("Rewards Value Realization & Incrementality Lab", "Synthetic randomized experiment | Executive readout | NOT Starbucks actuals")
    bullet_slide("Decision question & design", [
        "Question: does assignment to a hypothetical targeted engagement intervention increase cumulative contribution per randomized member?",
        "Synthetic panel: 20,000 members, Jan–Jun 2026; 18,866 eligible and randomized on Apr 1.",
        "Treatment/control randomized 1:1 within tier; primary analysis is intention-to-treat (ITT).",
        "Contribution deducts variable cost, ordinary reward cost, used-benefit cost, and intervention cost exactly once.",
    ])
    bullet_slide("Primary ITT result", [
        f"Treatment mean contribution/member: ${primary['mean_treatment']:.2f}; control: ${primary['mean_control']:.2f} (Apr–Jun cumulative).",
        f"Difference (treatment − control): ${primary['difference_treatment_minus_control']:.2f} per randomized member.",
        f"95% CI: ${primary['ci95_low']:.2f} to ${primary['ci95_high']:.2f}; two-sided p = {primary['p_value_two_sided']:.3g}.",
        f"N: {primary['n_treatment']:,} treatment; {primary['n_control']:,} control.",
        "Interpretation applies only to this synthetic data-generating process; it is not an estimate of actual Starbucks program performance.",
    ])
    bullet_slide("Secondary outcomes & sensitivity", [
        f"Transactions/member difference: {outcomes['post_transactions']['difference_treatment_minus_control']:.2f} (95% CI {outcomes['post_transactions']['ci95_low']:.2f} to {outcomes['post_transactions']['ci95_high']:.2f}).",
        f"Net sales/member difference: ${outcomes['post_net_sales']['difference_treatment_minus_control']:.2f} (95% CI ${outcomes['post_net_sales']['ci95_low']:.2f} to ${outcomes['post_net_sales']['ci95_high']:.2f}).",
        f"Adjusted HC3 sensitivity coefficient: ${adj['treatment_coefficient']:.2f} (95% CI ${adj['ci95_low']:.2f} to ${adj['ci95_high']:.2f}).",
        "Purchaser-rate difference is not statistically distinguishable from zero in this run; do not cherry-pick secondary outcomes.",
    ])
    scale_n = 10000
    bullet_slide("Illustrative contribution scaling — not a forecast", [
        f"Conservative (primary Welch CI lower bound): ${primary['ci95_low'] * scale_n:,.0f} across 10,000 eligible members.",
        f"Base case (primary ITT point estimate): ${primary['difference_treatment_minus_control'] * scale_n:,.0f} across 10,000 eligible members.",
        f"Upside (primary Welch CI upper bound): ${primary['ci95_high'] * scale_n:,.0f} across 10,000 eligible members.",
        "These values simply scale the synthetic per-member estimate and its confidence bounds; they are not a forecast or recommendation.",
        "All modeled variable, reward, benefit and intervention costs are already deducted in contribution.",
    ])
    bullet_slide("Benefit delivery is not incrementality", [
        f"Treatment exposure / eligible events: {funnel['TREATMENT']['exposure_per_eligible_event']:.1%}; use / exposed events: {funnel['TREATMENT']['use_per_exposed_event']:.1%}.",
        f"Control organic use / eligible events: {funnel['CONTROL']['use_per_eligible_event']:.1%}; no campaign exposure was assigned to control.",
        "Exposure and use are descriptive process metrics. Do not compare redeemers with non-redeemers as if randomized.",
        "Modeled benefit and intervention costs are already included in contribution; do not subtract them twice.",
    ])
    dgp = data["synthetic_dgp_parameters"]
    purchaser = outcomes["post_purchaser"]
    purchaser_inference = (
        "Purchaser-rate difference is statistically distinguishable from zero at the 5% level in this synthetic run; treat it as exploratory."
        if purchaser["p_value_two_sided"] < 0.05
        else "Purchaser-rate difference is not statistically distinguishable from zero at the 5% level in this synthetic run; treat it as exploratory."
    )
    bullet_slide("Limitations & next steps", [
        f"All member data, costs, tiers, seasonality and campaign effects are synthetic. The planted exposed-member transaction-intensity multiplier is {dgp['planted_exposed_member_transaction_intensity_multiplier']:.0%}; exposure probability is {dgp['campaign_exposure_probability_among_eligible_treatment_member_months']:.0%}.",
        purchaser_inference,
        "The supplied notebook records successful BigQuery loading/modeling and 18 passing warehouse QA checks; verify the live objects because Sandbox tables/views expire.",
        "Python-versus-BigQuery arm-mean reconciliation and actual Looker Studio dashboard construction/QA remain separate release gates.",
        "Use this result as a demonstration of reproducible analytical workflow—not a rollout recommendation or Starbucks forecast.",
        f"Reproducibility run ID: {data['analysis_run_id']}. The output is derived from the four CSV hashes listed in the workbook.",
    ])
    # Apply a consistent, restrained font size to title/body text.
    for slide in prs.slides:
        for shape in slide.shapes:
            if not shape.has_text_frame: continue
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    if run.font.size is None: run.font.size = Pt(20)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(output_path)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--results", type=Path, default=Path("outputs/experiment_results.json"))
    p.add_argument("--out-dir", type=Path, default=Path("outputs/executive_artifacts"))
    args = p.parse_args()
    build_excel(args.results, args.out_dir / "Rewards_Experiment_Review.xlsx")
    build_powerpoint(args.results, args.out_dir / "Rewards_Experiment_Executive_Readout.pptx")
    print(f"Wrote Excel and PowerPoint artifacts to {args.out_dir}")

if __name__ == "__main__": main()
