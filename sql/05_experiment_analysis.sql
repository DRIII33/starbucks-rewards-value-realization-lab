-- Primary unadjusted intention-to-treat summary. This query reports arm means and
-- sample sizes; use Python's Welch CI/test and HC3 sensitivity model for inference.
WITH member_outcomes AS (
 SELECT * FROM `driiiportfolio.starbucks_rewards_lab_restart.vw_experiment_member_outcomes`
)
SELECT assignment_group, COUNT(*) AS randomized_members,
  AVG(post_contribution) AS mean_post_contribution_per_member,
  AVG(post_transactions) AS mean_post_transactions_per_member,
  AVG(post_net_sales) AS mean_post_net_sales_per_member,
  AVG(post_purchaser) AS purchasing_member_rate,
  AVG(post_benefit_cost) AS mean_benefit_cost_per_member,
  AVG(pre_contribution) AS mean_pre_contribution_per_member
FROM member_outcomes
GROUP BY assignment_group ORDER BY assignment_group;

-- Difference in means (treatment minus control), descriptive point estimate only.
WITH a AS (
 SELECT assignment_group, AVG(post_contribution) AS avg_contribution, COUNT(*) AS n
 FROM `driiiportfolio.starbucks_rewards_lab_restart.vw_experiment_member_outcomes`
 GROUP BY assignment_group
)
SELECT MAX(IF(assignment_group='TREATMENT', avg_contribution, NULL))
     - MAX(IF(assignment_group='CONTROL', avg_contribution, NULL)) AS itt_contribution_difference,
       MAX(IF(assignment_group='TREATMENT', n, NULL)) AS n_treatment,
       MAX(IF(assignment_group='CONTROL', n, NULL)) AS n_control
FROM a;
