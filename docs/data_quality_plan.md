# Data quality and acceptance plan

## Local acceptance gate
1. Run deterministic generation.
2. Confirm exactly four expected CSVs plus generation metadata.
3. Validate required columns and allowed labels.
4. Validate member, event, and member-month key uniqueness.
5. Validate foreign keys and the six-month panel (`members × 6`).
6. Validate nonnegative integer transaction counts and finite numeric fields.
7. Reconcile contribution to sales less all modeled costs within $0.011.
8. Reconcile benefit-event cost to the member-month cost ledger and intervention cost to $0.10 per exposed event/member-month within $0.011.
9. Validate no exposure/use when ineligible and no negative benefit costs.
10. Inspect assignment counts overall and within tier.
11. Run tests and the experiment analysis.

## BigQuery acceptance gate
Run `sql/04_quality_checks.sql` as a multi-statement script. Its opening `ASSERT` statements fail if any of the four raw tables or four modeled tables has the wrong row count, preventing empty tables from passing vacuously. Queries 1-7 and 10-18 should return zero rows. Query 8 is a balance/assignment diagnostic; query 9 must show `passed = TRUE` and a positive panel count. Confirm all source tables loaded with the expected schemas before building views.

## Data-quality issue protocol
Do not silently deduplicate, coerce invalid labels, drop randomized members, or replace missing outcomes with zero. Stop the pipeline, identify the offending key/field, document the root cause in `docs/decision_log.md`, correct upstream generation or loading, and rerun all gates.

## Dashboard release gate
Dashboard totals must reconcile to governed BigQuery views; event counts and unique member counts must be labeled separately. Display a synthetic-data disclaimer on every page. Do not sum monthly distinct-member counts to create a period unique-member total.
