# Release gate matrix

| Gate | Required evidence | Pass criteria | Stop / remediation |
|---|---|---|---|
| G0 — Scope and environment | Project charter, Git commit, Python version, target dataset confirmation | Repo version and isolated dataset recorded; prior dataset explicitly protected | Wrong dataset or ambiguous scope: stop before cloud action |
| G1 — Local generation | Generated files and `generation_metadata.json` | 20,000 members; 120,000 member-month rows; 60,000 benefit events; six market rows; fixed seed recorded | Rerun generator; never patch CSV values manually |
| G2 — Local data QA | Validator output and pytest log | Validator passes; all tests pass; schema, keys, dates, flags, cost identities reconcile | Fix generator/validator contract; regenerate and rerun |
| G3 — Inference | `experiment_results.json`, effects CSV, inference CSV, input manifest | Results derive from validated current inputs; one run ID; all rows synthetic; six result rows/19 columns for the defined schema | Re-run analyzer; investigate missing provenance or schema mismatch |
| G4 — Executive artifacts | Workbook and presentation | Run ID, n, estimate, CI, p-value and synthetic disclaimer match JSON | Rebuild from current JSON; do not edit numeric results manually |
| G5 — Raw warehouse load | Table metadata and row-count query output | Correct project/dataset/location; raw counts match local outputs; explicit schema; no duplicate append | Reload correct table using replace; do not proceed |
| G6 — Modeled warehouse QA | `04_quality_checks.sql` outputs and metadata snapshot | All ASSERTs pass; zero issue rows where expected; expected modeled row counts; no unexplained expiry/partition state | Fix upstream and rerun from G5 or earlier |
| G7 — Python/SQL reconciliation | Comparison report | Member counts and arm means match within a documented numeric tolerance | Stop; inspect join grain, filters, cost logic, assignment population and missing rows |
| G8 — Dashboard sources | `07` execution, table schema/row checks, `08` output, run-ID comparison | Dashboard views exist; inference table loaded; one current run ID; primary and sensitivity rows unique; synthetic flags true | Load the CSV if absent; do not rerun `03` to fix a missing inference table |
| G9 — Looker Studio | Report URL in user's account, screenshots, chart reconciliation log | Four specified pages; no unintended blending/cross-filtering; metrics reconcile; synthetic banner on every page | Fix chart source, grain, filter, aggregation, or labeling |
| G10 — Release/closeout | README, manifest, QA evidence, closeout memo | Evidence links to exact commit/run; cloud checks dated; limitations and pending items honest | Do not claim release completion without evidence |

## Numeric invariants to verify, not blindly assume
- Expected randomized population: 18,866; expected treatment/control sizes in the reference run: 9,454 / 9,412. A new run must derive and record actual values from its current output.
- Reference analysis run ID: `773a7e55da4fee89`; seed: `20261022`. This is a historical reference run, not a hard-coded release gate if source hashes or code change.
- Reference primary ITT: approximately +$2.2135 per randomized member; 95% Welch CI approximately +$1.5121 to +$2.9148; p ≈ 6.29e-10. Use current generated JSON/CSV as source of truth.
- Reference adjusted HC3 sensitivity estimate: approximately +$2.0389; 95% CI approximately +$1.4276 to +$2.6502.
- These are synthetic results only and must not be presented as actual Starbucks results.
