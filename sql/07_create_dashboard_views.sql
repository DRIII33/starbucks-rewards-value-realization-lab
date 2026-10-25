-- Dashboard-specific governed views. These aggregate at the grain named in each view;
-- do not sum monthly unique-member counts to represent unique members across the full period.
CREATE OR REPLACE VIEW `driiiportfolio.starbucks_rewards_lab_restart.vw_dashboard_monthly_arm_performance` AS
SELECT
  month_start,
  period_phase,
  assignment_group,
  COUNT(DISTINCT member_id) AS randomized_members_in_panel,
  COUNTIF(active_at_start) AS active_at_start_members,
  COUNTIF(active_at_end) AS active_at_end_members,
  COUNTIF(transaction_count > 0) AS purchasing_members,
  SAFE_DIVIDE(COUNTIF(transaction_count > 0), COUNT(DISTINCT member_id)) AS purchasing_member_rate,
  SAFE_DIVIDE(COUNTIF(active_at_start), COUNT(DISTINCT member_id)) AS active_at_start_rate,
  SUM(transaction_count) AS transactions,
  AVG(transaction_count) AS transactions_per_randomized_member,
  SUM(net_sales) AS net_sales,
  AVG(net_sales) AS net_sales_per_randomized_member,
  SAFE_DIVIDE(SUM(net_sales), SUM(transaction_count)) AS average_transaction_value,
  SUM(contribution) AS contribution,
  AVG(contribution) AS contribution_per_randomized_member,
  SUM(benefit_cost) AS benefit_cost,
  AVG(benefit_cost) AS benefit_cost_per_randomized_member,
  SUM(intervention_cost) AS intervention_cost,
  AVG(intervention_cost) AS intervention_cost_per_randomized_member
FROM `driiiportfolio.starbucks_rewards_lab_restart.vw_member_month`
WHERE eligible_for_experiment
  AND assignment_group IN ('TREATMENT', 'CONTROL')
GROUP BY month_start, period_phase, assignment_group;

CREATE OR REPLACE VIEW `driiiportfolio.starbucks_rewards_lab_restart.vw_dashboard_tier_arm_summary` AS
SELECT
  tier_at_launch,
  assignment_group,
  COUNT(*) AS randomized_members,
  AVG(post_contribution) AS mean_post_contribution_per_member,
  AVG(post_transactions) AS mean_post_transactions_per_member,
  AVG(post_net_sales) AS mean_post_net_sales_per_member,
  AVG(post_purchaser) AS post_purchaser_rate,
  AVG(post_benefit_cost) AS mean_post_benefit_cost_per_member,
  AVG(pre_contribution) AS mean_pre_contribution_per_member
FROM `driiiportfolio.starbucks_rewards_lab_restart.vw_experiment_member_outcomes`
GROUP BY tier_at_launch, assignment_group;

CREATE OR REPLACE VIEW `driiiportfolio.starbucks_rewards_lab_restart.vw_dashboard_channel_arm_summary` AS
SELECT
  acquisition_channel,
  assignment_group,
  COUNT(*) AS randomized_members,
  AVG(post_contribution) AS mean_post_contribution_per_member,
  AVG(post_transactions) AS mean_post_transactions_per_member,
  AVG(post_net_sales) AS mean_post_net_sales_per_member,
  AVG(post_purchaser) AS post_purchaser_rate,
  AVG(post_benefit_cost) AS mean_post_benefit_cost_per_member
FROM `driiiportfolio.starbucks_rewards_lab_restart.vw_experiment_member_outcomes`
GROUP BY acquisition_channel, assignment_group;

CREATE OR REPLACE VIEW `driiiportfolio.starbucks_rewards_lab_restart.vw_dashboard_benefit_arm_summary` AS
SELECT
  d.assignment_group,
  d.tier_at_launch,
  COUNTIF(e.eligible_flag) AS eligible_events,
  COUNTIF(e.campaign_exposed_flag) AS exposed_events,
  COUNTIF(e.benefit_used_flag) AS used_events_total_including_unexposed_organic_use,
  COUNTIF(e.campaign_exposed_flag AND e.benefit_used_flag) AS exposed_and_used_events,
  COUNTIF(NOT e.campaign_exposed_flag AND e.benefit_used_flag) AS unexposed_used_events,
  COUNT(DISTINCT IF(e.benefit_used_flag, e.member_id, NULL)) AS unique_members_using_benefit_post_period,
  SUM(e.benefit_cost) AS benefit_cost_total,
  SAFE_DIVIDE(COUNTIF(e.campaign_exposed_flag), COUNTIF(e.eligible_flag)) AS exposure_per_eligible_event,
  SAFE_DIVIDE(COUNTIF(e.campaign_exposed_flag AND e.benefit_used_flag), COUNTIF(e.campaign_exposed_flag)) AS use_per_exposed_event,
  SAFE_DIVIDE(COUNTIF(e.benefit_used_flag), COUNTIF(e.eligible_flag)) AS use_per_eligible_event
FROM `driiiportfolio.starbucks_rewards_lab_restart.fact_benefit_events` e
JOIN `driiiportfolio.starbucks_rewards_lab_restart.dim_member` d USING (member_id)
WHERE e.month_start BETWEEN DATE '2026-04-01' AND DATE '2026-06-01'
  AND d.eligible_for_experiment
  AND d.assignment_group IN ('TREATMENT', 'CONTROL')
GROUP BY d.assignment_group, d.tier_at_launch;

CREATE OR REPLACE VIEW `driiiportfolio.starbucks_rewards_lab_restart.vw_dashboard_experiment_arm_summary` AS
SELECT
  assignment_group,
  COUNT(*) AS randomized_members,
  AVG(pre_contribution) AS mean_pre_contribution_per_member,
  AVG(post_contribution) AS mean_post_contribution_per_member,
  AVG(post_transactions) AS mean_post_transactions_per_member,
  AVG(post_net_sales) AS mean_post_net_sales_per_member,
  AVG(post_purchaser) AS post_purchaser_rate,
  AVG(post_benefit_cost) AS mean_post_benefit_cost_per_member
FROM `driiiportfolio.starbucks_rewards_lab_restart.vw_experiment_member_outcomes`
GROUP BY assignment_group;
