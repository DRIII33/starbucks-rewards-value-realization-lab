> **Historical record for the previous dataset/run.** Do not treat this file as evidence that `starbucks_rewards_lab_restart` has been validated. Use `docs/runbook.md` and `docs/restart_closeout_template.md` for restart execution and evidence.

# Cloud validation status — October 23, 2026

## Recorded in the uploaded notebook

The notebook's executed cells record the following in project `driiiportfolio`, dataset `starbucks_rewards_lab`, location `US`:

- Raw table load counts: `raw_members` 20,000; `raw_member_month` 120,000; `raw_benefit_events` 60,000; `raw_market_context` 6.
- Standardized dimensions/facts and four analytical views built successfully.
- All 18 warehouse quality checks reported PASS.
- The corrected raw and modeled fact tables use clustering instead of time partitioning.

This is based on the saved notebook output and the user's report that the BigQuery queries have been executed. This release pass did not authenticate to BigQuery or independently query live cloud state. The current repository SQL additionally includes fail-fast row-count `ASSERT` statements and an expanded check for intervention-cost reconciliation; those exact latest SQL edits are **not** covered by the saved earlier execution output until rerun in BigQuery.

## Remaining work

1. Run the read-only checks in `notebooks/01_run_pipeline.ipynb` to verify the current objects still exist and have expected row counts. Sandbox tables/views may expire approximately 60 days after creation.
2. Rerun the latest `sql/04_quality_checks.sql` after confirming all current tables exist; verify the `ASSERT` statements pass and the expanded intervention-cost check returns zero rows.
3. Compare Python arm means with `vw_experiment_member_outcomes` using the notebook's read-only reconciliation query.
4. Run `sql/07_create_dashboard_views.sql` to add dashboard-specific views; this script does not drop or reload fact tables.
5. Upload the current `outputs/looker_studio_results.csv` as `looker_studio_results` using `dashboard/looker_studio_results_schema.json` and overwrite mode.
6. Run `sql/08_dashboard_validation.sql`, then build the actual Looker Studio report using `dashboard/looker_studio_build_guide.md` and reconcile its visuals to governed views.
7. Update this file only when a later validation run is recorded; include date, project/dataset, expected/observed counts, and any failures.
