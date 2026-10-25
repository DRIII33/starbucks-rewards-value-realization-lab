# Metric dictionary

| Metric | Grain / definition | Use and guardrail |
|---|---|---|
| Eligible randomized member | One unique member with `eligible_for_experiment = TRUE` and assignment `TREATMENT` or `CONTROL` | Fixed ITT denominator; do not exclude post-assignment inactive members. |
| Experiment post purchaser rate | Randomized members with at least one transaction during Apr-Jun / all randomized members | Member-level binary outcome used in the ITT analysis. |
| Monthly tier purchasing-member rate | Panel members with at least one transaction in that month / all panel members in that tier-month | The tier-month view uses all synthetic panel members; do not confuse this with the fixed randomized experiment denominator. |
| Transactions per randomized member | Sum of Apr-Jun transactions / number randomized in arm | Includes zero transactions after attrition. |
| Net sales per randomized member | Sum Apr-Jun net sales / number randomized in arm | Synthetic sales, not company reported sales. |
| Contribution | Net sales - variable cost - ordinary reward cost - used-benefit cost - intervention cost | Each modeled cost included once. |
| Primary ITT effect | Mean cumulative Apr-Jun contribution in treatment minus control | Randomized assignment defines arms; report 95% CI and p-value, not only point estimate. |
| Benefit eligibility | `eligible_flag = TRUE` at benefit-event grain | Opportunity/event count, not unique members. |
| Campaign exposure rate | Exposed eligible events / eligible events | Descriptive implementation metric. |
| Benefit use per exposed event | Events both exposed and used / exposed events | Excludes organic use on unexposed events; may be undefined when no events were exposed. Still descriptive, not the causal ITT estimate. |
| Benefit use per eligible event | All used events / eligible events | Includes organic use among unexposed members; denominator is eligible event count. |
| Retention / attrition | `active_at_start` and `active_at_end` in monthly panel; attrition is absorbing in the generator | Distinguish customer activity from panel presence. Inactive members remain represented with zero outcomes. |
| Adjusted sensitivity effect | OLS treatment coefficient adjusted for pre-period contribution, tier and channel; HC3 standard errors | Sensitivity analysis; randomization-based unadjusted ITT remains primary. |

All metrics refer to synthetic data. Currency values are illustrative USD-like values only.
