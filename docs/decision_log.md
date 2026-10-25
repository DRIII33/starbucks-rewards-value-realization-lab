# Decision log

| Date | Decision | Rationale / status |
|---|---|---|
| 2026-10-23 | Use a distinct synthetic targeted-engagement experiment, not a claim to evaluate the actual Rewards redesign. | Avoids unsupported claims about Starbucks internal performance and separates this project from prior loyalty analytics work. |
| 2026-10-23 | Randomize eligible members with 0.5 assignment probability within tier on 2026-04-01. | Defines the causal comparison and stratifies randomization by tier; observed arm counts may differ slightly by chance. |
| 2026-10-23 | Use cumulative post-period contribution per randomized member as primary outcome. | Aligns business value to revenue and modeled costs; ITT includes non-exposure and attrition. |
| 2026-10-23 | Keep inactive members in the panel with zero subsequent activity outcomes. | Prevents survivorship bias in the synthetic experiment denominator. |
| 2026-10-23 | Treat exposure/use funnel metrics as descriptive. | Redemption is not a randomized treatment and cannot establish incrementality by itself. |
| 2026-10-23 | Treat all market indices and cost parameters as synthetic assumptions. | No actual syndicated data or internal cost data are available. |


## 2026-10-23 — Sandbox-safe warehouse design
- **Decision:** Use `CLUSTER BY month_start, member_id` rather than time partitioning for the synthetic member-month and benefit-event raw/modelled tables in the Sandbox workflow.
- **Reason:** The uploaded execution record documents a 60-day partition-expiration setting that purged historical synthetic partitions. Setting partition expiration to NULL did not override the Sandbox constraint.
- **Trade-off:** Clustering does not preserve objects indefinitely; Sandbox table/view objects can themselves expire after approximately 60 days.
- **Guardrail:** SQL QA begins with row-count assertions so empty tables cannot pass the checks vacuously.
