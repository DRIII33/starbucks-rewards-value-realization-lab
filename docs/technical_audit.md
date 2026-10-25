# Technical audit — stronger final version

## Changes made from the earlier starter specification

1. Replaced independent monthly transaction draws with persistent member-level frequency/ticket propensities, tier/channel heterogeneity, overdispersed counts, shared monthly demand shocks, and absorbing attrition.
2. Defined the experiment population at the April 1, 2026 assignment date: members active at March month-end are eligible; assignment is Bernoulli 0.5 within tier; later inactivity does not remove members from the ITT denominator.
3. Aligned intervention assignment, campaign exposure, benefit use, and transaction outcomes. The synthetic 15% transaction-intensity uplift applies only to actively exposed treatment member-months; 80% is the exposure probability. These are planted simulation parameters, not Starbucks facts.
4. Made the six-month member panel explicit, with inactive member-months retained and zero transactions/sales, and month-end activity state carried forward consistently.
5. Added an explicit contribution ledger: net sales less variable costs, ordinary reward costs, used-benefit costs, and intervention costs. Benefit-event costs reconcile to the member-month ledger; downstream scenario math does not subtract these costs again.
6. Fixed funnel semantics by separating all used events, exposed-and-used events, and unexposed organic use. `use_per_exposed_event` uses only exposed-and-used events in the numerator.
7. Added fail-fast checks for schema, keys, referential integrity, row counts, phase/date alignment, activity transitions, assignment eligibility, exposure logic, nonnegative values, finite numerics, cost reconciliation, and event coverage.
8. Added a Welch confidence interval/test for the primary randomized ITT estimate, an adjusted OLS/HC3 sensitivity model, p-value underflow protection, and explicit missing-event failures rather than silently converting missing event records to zero.
9. Made BigQuery Sandbox compatibility explicit: raw and modeled facts use clustering rather than time partitioning; scripts warn about the destructive reset and the Sandbox's separate table/view expiry.
10. Added fail-fast row-count `ASSERT` gates and corrected the financial-scenario SQL's reserved CTE name and `UNNEST` alias.
11. Made the analyzer validate all source CSVs before inference and emit a deterministic run ID plus SHA-256 input manifest.
12. Hardened the artifact builder to reject stale/mock JSON payloads and require the primary outcome, schema version, run ID, and four-file manifest to reconcile.
13. Replaced the uploaded notebook's duplicated historical workflows and mock-results cell with one clean notebook that calls the canonical scripts and includes optional read-only BigQuery/SQL reconciliation checks.
14. Aligned README, data dictionary, metric dictionary, methodology, runbook, dashboard spec, executive summary, disclaimer, source list, and validation record to the same schema and estimand.

## Validation evidence

- Local generation: passed for 20,000 members.
- Local data validator: passed, including contribution, benefit-cost, and intervention-cost reconciliation.
- Automated tests: **7 passed**.
- Python compilation: passed.
- Notebook structure and Python code-cell syntax validation: passed (11 cells; no stale mock-results cell).
- Excel workbook: generated from the versioned analyzer JSON and reopened successfully; six worksheets.
- PowerPoint deck: generated from the versioned analyzer JSON and reopened successfully; seven slides.
- Deterministic analysis run ID: `773a7e55da4fee89`.

## Cloud execution record and remaining gates

The uploaded notebook's saved outputs record successful BigQuery raw loads (20,000 / 120,000 / 60,000 / 6 rows), successful modeled table/view creation, and all 18 warehouse QA checks passing in `driiiportfolio.starbucks_rewards_lab` on October 23, 2026. This release pass did not independently connect to the live cloud project. The updated repository SQL adds fail-fast row-count `ASSERT` statements and expands the existing intervention-cost check; rerun that latest SQL before claiming those specific additions passed in the cloud. Python-vs-BigQuery arm-mean reconciliation and actual Looker Studio dashboard build/QA remain open gates.
