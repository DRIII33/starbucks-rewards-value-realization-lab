# Validation record — regenerated release

## Local reference run

Run from the repository root with seed `20261022` and 20,000 requested members. Re-run the commands in `README.md` to reproduce the outputs.

- Generated: 20,000 member rows, 120,000 member-month rows, 60,000 benefit-event rows, and 6 market-context rows.
- Local data validation: passed, including uniqueness, foreign keys, complete six-month panel, allowed labels, phase/date alignment, absorbing attrition, inactive-member zero transactions, assignment eligibility, treatment-only exposure, monetary reconciliation, event/ledger benefit-cost reconciliation, intervention-cost reconciliation, and allocation diagnostics.
- Analysis: primary ITT estimate computed from validated CSV inputs; result includes deterministic run ID and SHA-256 manifest.
- Dashboard inference export: `outputs/looker_studio_results.csv` contains five ITT outcome rows plus one adjusted HC3 sensitivity row; all rows share run ID `773a7e55da4fee89` and are marked synthetic. Its primary estimate/interval match the JSON result.
- Artifact generation: builder accepts only the current versioned analysis payload and rejects older mock/starter payloads.
- Automated tests: 7 passed. Source compilation and notebook code-cell syntax checks passed. The Excel workbook reopened successfully with six worksheets; the PowerPoint deck reopened successfully with seven slides.
- Deterministic analysis run ID: `773a7e55da4fee89`. The JSON result includes SHA-256 hashes for all four CSV inputs.

## Primary synthetic reference estimate

- Treatment-minus-control cumulative April-June contribution per randomized member: `+$2.2135`.
- 95% Welch confidence interval: `+$1.5121` to `+$2.9148`.
- Two-sided p-value: `6.29e-10`.
- Adjusted OLS/HC3 sensitivity estimate: `+$2.0389`, 95% CI `+$1.4276` to `+$2.6502`.

These results are from synthetic data only. The generator plants a 15% transaction-intensity multiplier among actively exposed treatment member-months and an 80% exposure probability. The assignment-level ITT is diluted by non-exposure and attrition. These are not Starbucks performance estimates.

## Cloud status and remaining gates

The uploaded notebook's saved output records successful raw data loads, successful creation of the standardized tables/views, and all 18 warehouse structural checks passing. This is a user-provided execution record, not a new live-cloud verification by this release process. The current repository's SQL adds fail-fast row-count assertions and expands the intervention-cost check; those exact edits need a fresh BigQuery run. Use the notebook's read-only checks to confirm current row counts and reconcile BigQuery arm means against the Python JSON output. The dashboard-specific SQL views (`sql/07_create_dashboard_views.sql`) and inference-table load/validation (`sql/08_dashboard_validation.sql`) have been added but have not been executed in live BigQuery by this release process. The actual Looker Studio dashboard still requires construction and QA using the new chart-by-chart build guide.
