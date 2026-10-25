-- Illustrative scenario scaling only; not a Starbucks forecast.
-- The confidence interval here uses a normal critical value (1.96) as a large-sample
-- approximation. The Python Welch-Satterthwaite interval is authoritative for reporting.
-- Contribution already deducts variable, ordinary reward, used-benefit and intervention
-- costs, so do NOT subtract those costs again.
WITH arm AS (
 SELECT assignment_group, COUNT(*) AS n,
   AVG(post_contribution) AS mean_post_contribution,
   STDDEV_SAMP(post_contribution) AS sd_post_contribution
 FROM `driiiportfolio.starbucks_rewards_lab_restart.vw_experiment_member_outcomes`
 GROUP BY assignment_group
), delta AS (
 SELECT
   MAX(IF(assignment_group='TREATMENT', n, NULL)) AS n_treatment,
   MAX(IF(assignment_group='CONTROL', n, NULL)) AS n_control,
   MAX(IF(assignment_group='TREATMENT', mean_post_contribution, NULL))
     - MAX(IF(assignment_group='CONTROL', mean_post_contribution, NULL)) AS delta_per_member,
   SQRT(
     POW(MAX(IF(assignment_group='TREATMENT', sd_post_contribution, NULL)), 2)
       / MAX(IF(assignment_group='TREATMENT', n, NULL))
     + POW(MAX(IF(assignment_group='CONTROL', sd_post_contribution, NULL)), 2)
       / MAX(IF(assignment_group='CONTROL', n, NULL))
   ) AS standard_error
 FROM arm
), interval_bounds AS (
 SELECT *, delta_per_member - 1.96 * standard_error AS approximate_ci_low,
           delta_per_member + 1.96 * standard_error AS approximate_ci_high
 FROM delta
)
SELECT scenario_row.scenario, scenario_row.contribution_difference_per_eligible_member,
  scenario_row.contribution_difference_per_eligible_member * 10000 AS illustrative_value_for_10000_eligible_members,
  n_treatment, n_control,
  'Illustrative synthetic-data scaling only; not a forecast. Use Python Welch CI for formal inference.' AS caveat
FROM interval_bounds
CROSS JOIN UNNEST([
  STRUCT('Conservative (approx. 95% lower bound)' AS scenario, approximate_ci_low AS contribution_difference_per_eligible_member),
  STRUCT('Base case (point estimate)' AS scenario, delta_per_member AS contribution_difference_per_eligible_member),
  STRUCT('Upside (approx. 95% upper bound)' AS scenario, approximate_ci_high AS contribution_difference_per_eligible_member)
]) AS scenario_row
ORDER BY CASE scenario_row.scenario
  WHEN 'Conservative (approx. 95% lower bound)' THEN 1
  WHEN 'Base case (point estimate)' THEN 2
  ELSE 3
END;
