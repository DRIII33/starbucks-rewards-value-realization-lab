# Looker Studio Build & Configuration Guide

This guide is the exact build companion to [`dashboard_specification.md`](dashboard_specification.md). It configures the intended report; it does not claim a live Looker Studio report has already been created. Report creation and final visual QA must occur in the user's Google account.

## A. Prerequisites

1. Run the local pipeline successfully from the repository root:
   ```bash
   python src/validate_data.py --data-dir data/generated
   python -m pytest -q
   python src/analyze_experiment.py --data-dir data/generated --out-dir outputs
   ```
2. Confirm `outputs/looker_studio_results.csv` exists and its primary row matches `outputs/experiment_results.json`.
3. If your raw/modelled warehouse already exists and has passed its checks, run only `sql/07_create_dashboard_views.sql` to add the dashboard views. Do not rerun `sql/03_build_analytics.sql` just to add the dashboard views; it rebuilds modeled fact tables. Run `sql/03_build_analytics.sql` only during an intentional full warehouse rebuild from validated raw tables.
4. Upload `outputs/looker_studio_results.csv` to BigQuery as `driiiportfolio.starbucks_rewards_lab_restart.looker_studio_results`. The most deterministic option is the CLI command below, run from the repository root after `bq` is authenticated and the project is selected:
   ```bash
   bq load --replace --source_format=CSV --skip_leading_rows=1 \
     --schema=dashboard/looker_studio_results_schema.json \
     driiiportfolio:starbucks_rewards_lab_restart.looker_studio_results \
     outputs/looker_studio_results.csv
   ```
   `--replace` is intentional: the table represents one analysis run and must not accumulate duplicate rows. If using the BigQuery UI instead, choose Upload → CSV, skip one header row, use the provided schema, and overwrite the table on reruns.
5. Run `sql/08_dashboard_validation.sql`. Inspect the primary-result row and confirm its `analysis_run_id` matches the local JSON.

## B. Connect data sources

In Looker Studio, create a new report and add each source using **Add data → BigQuery**. Select project `driiiportfolio`, dataset `starbucks_rewards_lab_restart`, then select the exact view/table below. If your project ID differs, change it consistently in SQL, upload destinations, and this guide.

| Looker Studio source label | BigQuery object | Grain | Primary use |
|---|---|---|---|
| `DS — Monthly Arm Performance` | `vw_dashboard_monthly_arm_performance` | Month × assignment arm | Page 1 and 2 trends |
| `DS — Experiment Arm Summary` | `vw_dashboard_experiment_arm_summary` | Assignment arm | Overall arm comparisons |
| `DS — Tier Arm Summary` | `vw_dashboard_tier_arm_summary` | Tier × assignment arm | Tier comparisons |
| `DS — Channel Arm Summary` | `vw_dashboard_channel_arm_summary` | Acquisition channel × assignment arm | Channel comparison |
| `DS — Benefit Arm Summary` | `vw_dashboard_benefit_arm_summary` | Tier × assignment arm | Event funnel and benefit costs |
| `DS — Monthly Benefit Funnel` | `vw_benefit_funnel` | Month × tier × assignment arm | Monthly benefit detail |
| `DS — Python Inference Results` | `looker_studio_results` | One row per outcome plus one adjusted sensitivity row | Exact ITT estimates and intervals |

Use the fields as exposed by BigQuery. Do not create Looker Studio blends between member-month and event-grain data.

## C. Set field types and default aggregations

In each data source's field editor, verify these types and default aggregations:

- `month_start`: Date; default aggregation None.
- `assignment_group`, `tier_at_launch`, `acquisition_channel`, `period_phase`, `outcome`, `result_type`, `description`, `analysis_run_id`: Text; default aggregation None.
- Counts such as `randomized_members`, `eligible_events`, `exposed_events`, `transactions`, `purchasing_members`: Number, 0 decimal places; default aggregation Sum for pre-aggregated counts.
- Money fields such as `contribution`, `net_sales`, `benefit_cost`, `mean_post_contribution_per_member`, `effect_estimate`, `ci95_low`, `ci95_high`, `mean_treatment`, `mean_control`: Currency (USD), 2 decimal places. For fields whose values are already aggregated means/effects, use Average at the chart layer when multiple source rows can roll up; use the field as a displayed value only when the chart dimensions preserve its source grain.
- Rate fields such as `purchasing_member_rate`, `active_at_start_rate`, `post_purchaser_rate`, `exposure_per_eligible_event`, `use_per_exposed_event`, `use_per_eligible_event`: Percent, 1 decimal place. These are ratios, not counts. At multi-row grains, recompute from summed numerator/denominator where possible rather than averaging rates unweighted.
- `p_value_two_sided`, `degrees_freedom`, `r_squared`, `standard_error`: Number. Show p-values with scientific notation only if available; otherwise use 4–6 significant digits and a tooltip/note for very small values.
- Boolean fields: Boolean. Do not sum Boolean fields.

If Looker Studio cannot format different outcomes in a single table correctly (currency vs count vs percent), split the chart into separate outcome-specific tables rather than mixing units.

## D. Create the four report pages

Create these pages in order:

1. `Executive Overview`
2. `Member Activity & Retention`
3. `Benefit Operations & Economics`
4. `Experiment Results & Decision`

At the top of every page, add a fixed text box with `SYNTHETIC PORTFOLIO DATA — NOT STARBUCKS ACTUALS`. Keep this visible without scrolling. Use consistent treatment/control colors across all pages. Use the exact chart settings in [`dashboard_specification.md`](dashboard_specification.md).

### Chart-specific setup checklist

For every chart, configure the Setup panel as follows:

- **Line charts:** Dimension `month_start`; sort ascending by `month_start`; metric aggregation `AVG` for per-member means and rates; breakdown dimension `assignment_group`; date range dimension `month_start`; default range Jan 1–Jun 30, 2026. Do not use `SUM` on a per-member average or rate.
- **Grouped bar charts:** Dimension as specified (tier/channel/arm); breakdown dimension `assignment_group` when comparing arms; metric as specified; sort by category or metric exactly as specified. Keep zero baseline.
- **Tables:** Use dimensions at the view's grain. Counts use `SUM`; pre-aggregated means/effects use `AVG` only when multiple rows can be combined and the chart's grouping makes that interpretation valid. Disable totals for rates and per-member means unless the total is mathematically meaningful.
- **Scorecards sourced from `looker_studio_results`:** Add chart-level filters exactly as written in the dashboard specification. Use `AVG` for numeric fields, since the filter should leave one row. Confirm the filter leaves exactly one row.
- **Date controls:** Apply only to views with `month_start`. The experiment result table is a fixed April–June analysis and should not respond to a monthly date control.
- **Drill-down:** Not required for release 1. Avoid drill-downs that make the chart's population or denominator unclear.
- **Blending:** Not required and should not be used for release 1.

## E. Exact filters for inference scorecards

Primary ITT scorecards must use source `DS — Python Inference Results` and both chart filters:

- Include `result_type` Equal to `ITT_OUTCOME`.
- Include `outcome` Equal to `post_contribution`.

Then create separate scorecards with metric fields:

- `effect_estimate` — label `ITT effect ($/randomized member)`.
- `ci95_low` — label `95% CI lower ($)`.
- `ci95_high` — label `95% CI upper ($)`.
- `n_treatment` and `n_control` — label as arm sample sizes, not as a sum of monthly counts.
- `p_value_two_sided` — label `Welch two-sided p-value`.

For the adjusted sensitivity cards, filter `result_type` Equal to `ADJUSTED_SENSITIVITY`; label the result as adjusted HC3 sensitivity, not the primary ITT.

## F. Upload/reload the Python inference result table

When the local analysis is rerun:

1. Regenerate `outputs/looker_studio_results.csv` with `src/analyze_experiment.py`.
2. Upload it to the existing BigQuery table using overwrite/replace mode, never append.
3. Run `sql/08_dashboard_validation.sql`.
4. Refresh the Looker Studio data source fields if needed.
5. Verify the run ID on the dashboard and compare the primary result and interval to `outputs/experiment_results.json`.

The CSV has one row for each ITT outcome in the analysis plus one row for the adjusted sensitivity model. It is not a member-level table. Do not use it to calculate monthly trends.

## G. Style settings

- Report layout: widescreen; align cards and chart edges; consistent margins.
- Titles: short, descriptive, and include units where useful.
- Line charts: markers on, legend visible, no smoothing, ascending month order.
- Bar charts: zero baseline, data labels if legible, no 3D, treatment/control grouping consistent.
- Tables: descriptive labels, numeric units explicit, sensible decimal precision, totals disabled for rates and means.
- Keep cross-filtering off for release 1. If later enabled, test whether clicking a tier or arm unintentionally filters the headline KPI.
- Do not use a static screenshot or mockup as evidence that the live report is built.

## H. Final QA checklist

- [ ] Four pages exist in the required order.
- [ ] Synthetic banner appears on every page.
- [ ] All sources use the intended project and dataset.
- [ ] Dashboard inference table has one analysis run ID and all rows are marked synthetic.
- [ ] Primary ITT scorecards show the same estimate and interval as Python.
- [ ] Treatment/control counts reconcile to 9,454 and 9,412 for the current fixed-seed run.
- [ ] Monthly chart views contain 12 rows (six months × two arms).
- [ ] Rates are calculated using correct denominators and formatted as percentages.
- [ ] Control `use_per_exposed_event` is blank/NULL, not zero.
- [ ] No raw event/member-month blend exists.
- [ ] Dashboard data refreshes successfully after a test reload.
- [ ] Actual report screenshots are captured only after QA passes.
