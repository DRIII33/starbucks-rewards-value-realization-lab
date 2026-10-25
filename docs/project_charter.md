# Project charter — Rewards Value Realization & Incrementality Lab

## Purpose
Build an auditable, reproducible synthetic analytics case study that demonstrates how a loyalty-strategy analyst would distinguish incremental contribution from surface engagement and benefit use. It is a portfolio simulation, not a Starbucks internal analysis.

## Business scenario
A hypothetical loyalty team is considering a targeted engagement intervention for eligible members. More impressions, offer exposure, and benefit redemptions may not translate into incremental economic value: members may have purchased anyway, rewards have a cost, inactive members may disappear from observed data, and segment averages can obscure the randomized assignment effect. The team needs a governed experiment framework to estimate the effect of assignment on contribution after modeled costs and to make uncertainty and limitations visible to decision-makers.

## Problem statement
How does assignment to a hypothetical targeted engagement intervention affect cumulative April–June contribution per eligible randomized member, compared with control, when all randomized members remain in the denominator and modeled costs are included?

## Scope
- Six synthetic months: January–June 2026.
- January–March: pre-period/baseline context.
- April–June: post-period for hypothetical intervention.
- Unit of randomization and primary analysis: eligible member.
- Assignment date: April 1, 2026; assignment stratified by tier.
- Primary outcome: cumulative post-period contribution per randomized member.
- Primary estimator: treatment-minus-control intention-to-treat difference, Welch 95% confidence interval and two-sided p-value.
- Sensitivity: adjusted OLS with HC3 robust standard errors.
- Descriptive operational lens: eligibility → exposure → use funnel and segment performance.
- Outputs: validated synthetic data, governed BigQuery tables/views, statistical artifacts, Excel review, PowerPoint readout, four-page Looker Studio dashboard, documentation and reproducibility evidence.

## Out of scope
- Any claim about actual Starbucks customer behavior, actual program economics, or the causal impact of Starbucks' real Rewards redesign.
- Actual Starbucks internal, personal, or customer data.
- A production campaign deployment, live targeting, or rollout recommendation based solely on synthetic evidence.
- Treating redemption, exposure, or observational segment differences as causal effects.

## Data design (synthetic)
- 20,000 members; 120,000 member-month rows; 60,000 benefit-event rows; six market-context rows. These are expected generator outputs, not actual company records.
- A planted 15% transaction-intensity multiplier among actively exposed treatment member-months and 80% exposure probability among eligible active treatment member-months are simulation parameters, not empirical findings.
- Inactive members remain represented with zero subsequent activity outcomes so attrition does not silently remove them from the ITT denominator.

## Decision framing
A positive synthetic estimate is not a rollout recommendation. The simulated result can illustrate what evidence would support a larger preregistered test. A real business decision would require validated internal data, costs, customer-experience guardrails, operational constraints, and a powered test.

## Stakeholders and quality responsibilities
- Project owner / analyst: scope, reproducibility, interpretation and decision memo.
- Data engineering role (simulated): ingestion, schema, table lifecycle, SQL transformations, cost/retention controls.
- QA/audit role (simulated): lineage, data contracts, row counts, reconciliation, provenance and evidence.
- Loyalty strategy / executive audience (simulated): decision question, trade-offs, action threshold, caveats.

## Definition of done
All phase gates in `release_gate_matrix.md` pass; local tests pass; warehouse QA and Python–BigQuery reconciliation pass on the isolated restart dataset; dashboard source data matches the same analysis run; the Looker Studio report is built and checked; all pages show the synthetic-data banner; and a closeout memo documents results, caveats, and evidence.
