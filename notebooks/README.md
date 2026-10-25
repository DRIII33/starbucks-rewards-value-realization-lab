# Notebooks

- `01_run_pipeline.ipynb` is the canonical notebook. It runs the repository's generator, validator, tests, analysis, and executive-artifact builder, then offers optional read-only BigQuery row-count/partitioning checks and Python-vs-SQL reconciliation.
- The notebook intentionally contains no hard-coded mock analytics results and no duplicate implementation of the source scripts.
- The BigQuery verification cells do not mutate cloud objects. Destructive rebuild commands remain in `sql/02_create_tables.sql` and are documented in the runbook.
