# Controlled execution runbook — restart release

**Canonical target:** Google Cloud project `driiiportfolio`; isolated dataset `starbucks_rewards_lab_restart`; location `US`.

**Safety principle:** The prior dataset `starbucks_rewards_lab` is preserved and is not a target for this restart. Do not delete, overwrite, or alter it. The new dataset is a clean-room target. Before running any DDL, verify the selected project, dataset, and location in the BigQuery UI.

## Phase 0 — repository and environment lock
1. Start from the repository root and record the Git commit hash.
2. Use Python 3.10+ (CI currently tests Python 3.11); install `requirements.txt`.
3. Confirm `.gitignore` excludes credentials, local environments, and temporary files. Never place secrets in notebook, repository, or prompt.
4. Run `python -m compileall -q src tests` and `python -m pytest -q`. Stop on any failure.
5. Do not edit generated CSVs or inferential outputs manually.

## Phase 1 — deterministic local data build
Run in order:
```bash
python src/generate_data.py --members 20000 --seed 20261022 --out data/generated
python src/validate_data.py --data-dir data/generated
python -m pytest -q
python src/analyze_experiment.py --data-dir data/generated --out-dir outputs
python src/build_executive_artifacts.py --results outputs/experiment_results.json --out-dir outputs/executive_artifacts
```
Then inspect all generated file names, row counts, column headers, provenance metadata, run ID, arm sizes, primary estimate, CI, p-value, and synthetic disclaimer. Regeneration may update the run ID if any input or code hash changes; do not hard-code the prior run ID as expected truth.

### Local expected structural counts
- `raw_members.csv`: 20,000 rows.
- `raw_member_month.csv`: 120,000 rows (20,000 × six months).
- `raw_benefit_events.csv`: 60,000 rows.
- `raw_market_context.csv`: six rows.
- `outputs/looker_studio_results.csv`: six rows and 19 columns for the documented current result schema; verify dynamically, do not assume without checking.
- Every inference row must have `synthetic_data_only=True`; all rows in one output must share one `analysis_run_id`.

## Phase 2 — warehouse bootstrap and load (new dataset only)
1. Verify project `driiiportfolio`, dataset `starbucks_rewards_lab_restart`, location `US`.
2. Run `sql/01_create_dataset.sql`. It is scoped to the restart dataset.
3. Run `sql/02_create_tables.sql`. This is destructive within the restart dataset: it drops and recreates its four raw tables. Confirm the dataset name in the editor before execution.
4. Load each generated CSV to its matching table with header row skipped and **replace/overwrite**, not append. Target names: `raw_members`, `raw_member_month`, `raw_benefit_events`, `raw_market_context`. Use explicit destination schemas from the DDL.
5. Immediately run row-count checks; expected counts are in Phase 1. Stop on any mismatch.
6. Inspect table metadata: project, dataset, location, expiration, partitioning, and clustering. The canonical schema avoids time partitioning for member-month and benefit-event tables and clusters them by `month_start, member_id`. Clustering is not a retention guarantee. Record the observed expiration settings.

## Phase 3 — modeled tables and warehouse QA
1. Run `sql/03_build_analytics.sql`. This drops/rebuilds `fact_member_month` and `fact_benefit_events` in the restart dataset and recreates governed views. It is not a harmless read-only script.
2. Run `sql/04_quality_checks.sql`. All `ASSERT` gates must pass. Review every result set, including the diagnostic assignment query and all zero-issue queries. Save a QA evidence record with timestamp, project/dataset, query version/commit, expected/observed row counts, and result.
3. Run `sql/05_experiment_analysis.sql` for descriptive SQL reconciliation only. Python inference remains the source of exact Welch CI/p-value and HC3 sensitivity.
4. Reconcile Python arm counts and outcome means to `vw_experiment_member_outcomes`. If they disagree, stop. Do not proceed to dashboarding or manually adjust numbers.
5. Run `sql/06_financial_scenarios.sql` only after all QA gates pass. Treat scaling as a hypothetical scenario, not a forecast.

## Phase 4 — dashboard-source contract
1. Run `sql/07_create_dashboard_views.sql` only after Phases 1–3 pass. This script is additive to the modeled pipeline and creates dashboard views; it does not create the Python inference table.
2. Load `outputs/looker_studio_results.csv` as `driiiportfolio.starbucks_rewards_lab_restart.looker_studio_results` using `dashboard/looker_studio_results_schema.json`; skip the header, use explicit schema, and overwrite/replace. Never append a second run to this single-run table.
3. Validate the table schema and contents before running SQL: six rows; 19 headers in exact schema order; one run ID; all synthetic flags true; `n_treatment`/`n_control` are integer-compatible; required fields are non-null. Verify current run ID against `outputs/experiment_results.json`.
4. Run `sql/08_dashboard_validation.sql` and inspect all seven result sets. A validation script can only validate what its queries cover; also verify row counts, schema, one run ID, and reconciliation separately. The final duplicate-key query should return zero rows.
5. If the results table is missing, stop and load it; do not interpret a table-not-found error as a failed experiment or rerun destructive base-table scripts.

## Phase 5 — Looker Studio build and release
1. Build only after the data contracts and reconciliation pass. Follow `dashboard/dashboard_specification.md` and `dashboard/looker_studio_build_guide.md`.
2. Use the governed views at their documented grain. Do not blend event-grain benefit records with member-month records.
3. Use `looker_studio_results` for exact Python inference values. Filter primary scorecards to `result_type='ITT_OUTCOME' AND outcome='post_contribution'`; use `ADJUSTED_SENSITIVITY` only for the sensitivity panel. Never manually type an effect estimate into a visual.
4. Each dashboard page must prominently display `SYNTHETIC PORTFOLIO DATA — NOT STARBUCKS ACTUALS`.
5. Verify every scorecard and chart against source SQL, filter state, date window, denominator, and run ID. Capture screenshots and a reconciliation log.
6. The report is not “complete” until a real Looker Studio report exists in the user's account and the final QA is recorded.

## Retention / 60-day policy guardrail
The previous workflow encountered a reported 60-day partition-expiration problem. The canonical design avoids time partitioning on the member-month and benefit-event tables, but whole BigQuery Sandbox tables/views may still expire. Before work and before publication, inspect live object existence and expiration metadata. Never assume saved notebook output proves current cloud state. Keep the generated local data and repository outputs as reproducible sources of truth.

## Stop conditions
Stop immediately for any unexpected project/dataset, row-count mismatch, schema mismatch, missing provenance, non-synthetic flag, run-ID mismatch, failed SQL assertion, Python/BigQuery discrepancy, unexpected object expiry, or dashboard metric discrepancy. Record the failure and evidence; fix upstream and rerun from the earliest affected gate. Never disable a check merely to proceed.
