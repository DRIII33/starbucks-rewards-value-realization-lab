# Business problem and decision framing

## Public context (not internal diagnosis)
Starbucks publicly announced a redesigned U.S. Starbucks Rewards program in January 2026 and launched it in March 2026. Public company reporting also describes comparable-sales and transaction performance. These facts establish relevant context only; they do **not** establish that the redesign caused subsequent results or that Starbucks has a specific internal loyalty-program problem.

## Decision question
How should a loyalty analytics team evaluate whether a hypothetical targeted engagement intervention produces incremental contribution among eligible Rewards members, rather than merely increasing exposure, benefit use, or reported engagement?

## Scope
- Six-month synthetic panel: January-June 2026.
- January-March: pre-period for baseline covariates and descriptive context.
- April-June: post-period for a hypothetical randomized campaign.
- Randomization unit: eligible member; treatment/control assignment occurs on April 1, 2026, stratified by tier.
- Primary estimand: treatment-minus-control difference in cumulative April-June contribution per randomized member (intention-to-treat, ITT).

## What this project does not claim
It does not estimate the causal effect of Starbucks' actual Rewards redesign. It has no Starbucks internal data, real customer records, actual syndicated market data, actual reward rules, or verified campaign economics. The tier labels and all rows are synthetic. Market context is a small set of illustrative indices, not syndicated data.

## Decision branches (conditional, not findings)
1. Positive contribution estimate with sufficiently precise confidence interval and guardrails met: propose a larger, pre-registered validation test; do not leap directly to company-wide rollout.
2. Engagement rises but contribution does not: inspect benefit cost, transaction substitution, average ticket, and retention; avoid using redemption as a proxy for incrementality.
3. Estimate is imprecise: assess minimum detectable effect, sample size, variance, and test duration before concluding.
4. Contribution is negative or guardrails fail: do not scale on engagement metrics alone; investigate cost and customer-experience trade-offs.
