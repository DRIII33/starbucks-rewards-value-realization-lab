# Risk register and controls

| ID | Risk / failure mode | Impact | Control / prevention | Detection / recovery |
|---|---|---|---|---|
| R1 | Wrong Google Cloud project or dataset selected | Existing data could be overwritten; results split across datasets | Isolated target `starbucks_rewards_lab_restart`; project/dataset preflight before every DDL | Inspect query editor and table metadata; stop if any mismatch |
| R2 | Destructive SQL executed casually | Raw or modeled tables dropped | Label DDL destructive; separate create/load/model steps; never run reset for dashboard-only work | Confirm current dataset; restore by reloading generated CSVs and rerunning QA |
| R3 | 60-day partition expiration purges historical slices | Incomplete facts, invalid time series, failed dashboard | Avoid time partitioning for affected synthetic facts; inspect object expiration; keep local source data | Read-only existence/count/metadata checks before each phase and publication |
| R4 | Whole Sandbox objects expire | Views/tables disappear despite no time partitioning | Treat Sandbox as ephemeral; document expiry and rerun from versioned local inputs | `Not found`/metadata check; recreate only in isolated dataset and rerun QA |
| R5 | Project-ID typo (`driiportfolio` vs `driiiportfolio`) | Loads/queries target wrong project or fail | Single canonical project ID `driiiportfolio`; explicit preflight | Compare query references and UI project; stop before DDL |
| R6 | Dashboard views are mistaken for inference table | `looker_studio_results` not found | Explicit phase order: create views, separately load inference CSV, then validate | Table existence/schema/count check; load CSV; do not rebuild facts to solve it |
| R7 | CSV/schema mismatch | Load fails or fields shift silently | Explicit schema JSON; validate exact 19 header names/order and six rows before load | Inspect load-job errors and table schema; regenerate from analyzer |
| R8 | Appending CSV on rerun duplicates result rows | Duplicated KPIs or wrong aggregation | Overwrite/replace the single-run inference table | Unique `(result_type,outcome)` and run-ID checks |
| R9 | Old inference output combined with new warehouse facts | Inconsistent estimates/dashboard | Carry run ID and input manifest; compare CSV to current JSON before upload | Stop if run IDs differ; rerun analyzer/export and reload |
| R10 | Event-grain benefit data joined to member-month data | Double counting costs or outcomes | Keep views at documented grain; no event/member-month blending in dashboard | Reconcile counts/costs and chart aggregations |
| R11 | Attrition removes randomized members from denominator | Survivorship bias in ITT | Keep randomized eligible population denominator; inactive post-period outcomes remain represented | Compare randomized count to analysis frame and view counts |
| R12 | Redemption/exposure interpreted causally | False business conclusion | ITT is primary; funnel/segment views descriptive | Audit language in executive readout/dashboard |
| R13 | Synthetic data mistaken for real Starbucks data | Misrepresentation/reputational risk | Prominent disclaimer in README, outputs, and every dashboard page | Release checklist and visual screenshot review |
| R14 | Local tests mistaken for live-cloud validation | False claim of end-to-end completion | Separate local, warehouse, and dashboard statuses | Record dated evidence for each gate |
| R15 | SQL changes not reflected in docs/notebook/schema | Phase drift and reproducibility failure | Update all contracts together; single canonical runbook and gate matrix | CI + schema checks + release review |

## Issue response rule
Capture the exact error, query/script version, run ID, project/dataset, affected table/view, and query job details. Identify the earliest failing gate. Fix the cause upstream and rerun from that gate; do not skip checks or manually alter output values to make results look consistent.
