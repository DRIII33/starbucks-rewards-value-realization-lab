# Methodology and statistical guardrails

## Synthetic data-generating process
The generator uses a fixed random seed, persistent member-level frequency and ticket propensities, tier/channel multipliers, shared month-level seasonality/demand shocks, overdispersed monthly counts, cost variability, and absorbing attrition. All parameters are artificial and disclosed in code. The generator plants a 15% transaction-intensity multiplier for actively exposed treatment member-months in April-June; exposure is sampled with an 80% probability among eligible active treatment member-months. Assignment-level ITT is therefore diluted by non-exposure and attrition. These are known DGP parameters, not the analysis answer and not Starbucks facts.

## Assignment and estimand
Members active at the end of March form the eligible experiment population. Assignment is randomized with a 0.5 treatment probability within tier on April 1; arm counts may differ slightly by chance. Primary analysis follows intention-to-treat: members remain in their assigned arm even if they are not exposed, do not use the benefit, or later become inactive. Post-assignment inactivity results in zero subsequent transactions and sales, while fixed costs actually incurred remain in the ledger.

## Primary analysis
For each randomized member, sum contribution across April, May and June. Estimate the treatment-minus-control difference in means, Welch standard error, 95% confidence interval, and two-sided p-value. Report arm sample sizes and the exact population definition. Keep the full randomized population in the denominator.

## Sensitivity analysis
OLS adjusts post-period cumulative contribution for pre-period contribution, tier, and acquisition channel, with HC3 heteroskedasticity-robust standard errors. HC3 is not a cure for confounding; its role here is variance robustness. Randomization, not regression adjustment, is the identification strategy.

## Benefit funnel
Exposure and use rates are descriptive process measures. Comparing actual redeemers with non-redeemers is not randomized and must not be presented as a causal effect. Exposure is a post-assignment variable; conditioning the primary estimate on exposure would break the ITT estimand.

## Missingness and attrition
The panel retains one row per member-month, including inactive members. Zero outcomes are explicit outcomes for this synthetic design, not missing data. The experiment denominator is fixed at assignment. If a real dataset has missing records rather than verified zero activity, do not convert missingness to zero without a documented source rule.

## Multiple outcomes and decision-making
Contribution is primary; transactions, sales, purchaser rate, and benefit costs are secondary. Avoid selecting whichever outcome is significant. Treat secondary p-values as exploratory unless a multiple-testing plan is pre-specified. A non-significant result is not proof of no effect. A positive point estimate alone is not sufficient to recommend scale-up; consider the CI, economics, operational feasibility, customer guardrails, and a prospective replication.
