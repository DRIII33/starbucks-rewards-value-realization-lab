# Generated outputs

Run `src/analyze_experiment.py` to regenerate:

- `member_level_analysis.csv` — one row per randomized member with pre/post outcomes and event summaries.
- `experiment_results.json` — authoritative run metadata, primary ITT result, secondary outcomes, adjusted HC3 sensitivity, and descriptive benefit funnel.
- `experiment_effects.csv` — tabular Welch results by outcome.
- `looker_studio_results.csv` — one row per ITT outcome plus one adjusted sensitivity row, intended for upload/replace into BigQuery table `looker_studio_results` for Looker Studio inference cards/tables.

The result table is tied to `analysis_run_id`; never append old runs. After upload, run `sql/08_dashboard_validation.sql`.

Run `src/build_executive_artifacts.py` after analysis to generate the Excel workbook and PowerPoint in `outputs/executive_artifacts/`. All values are synthetic and must not be described as actual Starbucks performance.
