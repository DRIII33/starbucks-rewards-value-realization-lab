-- Standardized dimensions/facts and governed views.
-- Sandbox-safe: use clustering, not time partitioning, for historical synthetic dates.
-- DROP fact tables first so this script can migrate any old partitioned definitions safely.
DROP TABLE IF EXISTS `driiiportfolio.starbucks_rewards_lab_restart.fact_member_month`;
DROP TABLE IF EXISTS `driiiportfolio.starbucks_rewards_lab_restart.fact_benefit_events`;
CREATE OR REPLACE TABLE `driiiportfolio.starbucks_rewards_lab_restart.dim_member` AS
SELECT
  TRIM(member_id) AS member_id,
  enrollment_date,
  UPPER(TRIM(tier_at_launch)) AS tier_at_launch,
  UPPER(TRIM(acquisition_channel)) AS acquisition_channel,
  UPPER(TRIM(region_group)) AS region_group,
  SAFE_CAST(prior_90d_transactions AS INT64) AS prior_90d_transactions,
  SAFE_CAST(prior_90d_net_sales AS NUMERIC) AS prior_90d_net_sales,
  eligible_for_experiment,
  UPPER(TRIM(assignment_group)) AS assignment_group,
  assignment_date,
  assignment_probability
FROM `driiiportfolio.starbucks_rewards_lab_restart.raw_members`;

CREATE OR REPLACE TABLE `driiiportfolio.starbucks_rewards_lab_restart.fact_member_month`
CLUSTER BY month_start, member_id AS
SELECT
  TRIM(member_id) AS member_id, month_start, UPPER(TRIM(period_phase)) AS period_phase,
  active_at_start, active_at_end,
  SAFE_CAST(transaction_count AS INT64) AS transaction_count,
  SAFE_CAST(net_sales AS NUMERIC) AS net_sales,
  SAFE_CAST(variable_cost AS NUMERIC) AS variable_cost,
  SAFE_CAST(reward_cost AS NUMERIC) AS reward_cost,
  SAFE_CAST(benefit_cost AS NUMERIC) AS benefit_cost,
  SAFE_CAST(intervention_cost AS NUMERIC) AS intervention_cost,
  SAFE_CAST(contribution AS NUMERIC) AS contribution
FROM `driiiportfolio.starbucks_rewards_lab_restart.raw_member_month`;

CREATE OR REPLACE TABLE `driiiportfolio.starbucks_rewards_lab_restart.fact_benefit_events`
CLUSTER BY month_start, member_id AS
SELECT TRIM(event_id) AS event_id, TRIM(member_id) AS member_id, month_start,
  UPPER(TRIM(benefit_id)) AS benefit_id, eligible_flag, campaign_exposed_flag,
  benefit_used_flag, SAFE_CAST(benefit_cost AS NUMERIC) AS benefit_cost
FROM `driiiportfolio.starbucks_rewards_lab_restart.raw_benefit_events`;

CREATE OR REPLACE TABLE `driiiportfolio.starbucks_rewards_lab_restart.dim_market_context` AS
SELECT month_start, SAFE_CAST(market_index AS NUMERIC) AS market_index,
  SAFE_CAST(seasonality_index AS FLOAT64) AS seasonality_index, source_type
FROM `driiiportfolio.starbucks_rewards_lab_restart.raw_market_context`;

CREATE OR REPLACE VIEW `driiiportfolio.starbucks_rewards_lab_restart.vw_member_month` AS
SELECT f.*, d.tier_at_launch, d.acquisition_channel, d.region_group,
  d.eligible_for_experiment, d.assignment_group,
  m.market_index, m.seasonality_index, m.source_type AS market_source_type
FROM `driiiportfolio.starbucks_rewards_lab_restart.fact_member_month` f
JOIN `driiiportfolio.starbucks_rewards_lab_restart.dim_member` d USING (member_id)
LEFT JOIN `driiiportfolio.starbucks_rewards_lab_restart.dim_market_context` m USING (month_start);

CREATE OR REPLACE VIEW `driiiportfolio.starbucks_rewards_lab_restart.vw_tier_monthly_performance` AS
SELECT month_start, period_phase, tier_at_launch,
  COUNT(DISTINCT member_id) AS panel_members,
  COUNT(DISTINCT IF(transaction_count > 0, member_id, NULL)) AS purchasing_members,
  SAFE_DIVIDE(COUNT(DISTINCT IF(transaction_count > 0, member_id, NULL)), COUNT(DISTINCT member_id)) AS purchasing_member_rate,
  SUM(transaction_count) AS transactions,
  SUM(net_sales) AS net_sales,
  SUM(contribution) AS contribution,
  SAFE_DIVIDE(SUM(net_sales), SUM(transaction_count)) AS average_transaction_value,
  SAFE_DIVIDE(SUM(transaction_count), COUNT(DISTINCT member_id)) AS transactions_per_panel_member,
  SAFE_DIVIDE(SUM(contribution), COUNT(DISTINCT member_id)) AS contribution_per_panel_member
FROM `driiiportfolio.starbucks_rewards_lab_restart.vw_member_month`
GROUP BY month_start, period_phase, tier_at_launch;

CREATE OR REPLACE VIEW `driiiportfolio.starbucks_rewards_lab_restart.vw_benefit_funnel` AS
SELECT e.month_start, d.tier_at_launch, d.assignment_group,
  COUNTIF(e.eligible_flag) AS eligible_events,
  COUNTIF(e.campaign_exposed_flag) AS exposed_events,
  COUNTIF(e.benefit_used_flag) AS used_events_total_including_unexposed_organic_use,
  COUNTIF(e.campaign_exposed_flag AND e.benefit_used_flag) AS exposed_and_used_events,
  COUNTIF(NOT e.campaign_exposed_flag AND e.benefit_used_flag) AS unexposed_used_events,
  COUNT(DISTINCT IF(e.benefit_used_flag, e.member_id, NULL)) AS unique_members_using_benefit,
  SUM(e.benefit_cost) AS benefit_cost,
  SAFE_DIVIDE(COUNTIF(e.campaign_exposed_flag), COUNTIF(e.eligible_flag)) AS exposure_per_eligible_event,
  SAFE_DIVIDE(COUNTIF(e.campaign_exposed_flag AND e.benefit_used_flag), COUNTIF(e.campaign_exposed_flag)) AS use_per_exposed_event,
  SAFE_DIVIDE(COUNTIF(e.benefit_used_flag), COUNTIF(e.eligible_flag)) AS use_per_eligible_event
FROM `driiiportfolio.starbucks_rewards_lab_restart.fact_benefit_events` e
JOIN `driiiportfolio.starbucks_rewards_lab_restart.dim_member` d USING (member_id)
GROUP BY e.month_start, d.tier_at_launch, d.assignment_group;

CREATE OR REPLACE VIEW `driiiportfolio.starbucks_rewards_lab_restart.vw_experiment_member_outcomes` AS
WITH pre AS (
  SELECT member_id, SUM(contribution) AS pre_contribution,
    SUM(transaction_count) AS pre_transactions, SUM(net_sales) AS pre_net_sales
  FROM `driiiportfolio.starbucks_rewards_lab_restart.fact_member_month`
  WHERE month_start BETWEEN DATE '2026-01-01' AND DATE '2026-03-01'
  GROUP BY member_id
), post AS (
  SELECT member_id, SUM(contribution) AS post_contribution,
    SUM(transaction_count) AS post_transactions, SUM(net_sales) AS post_net_sales,
    COUNTIF(transaction_count > 0) AS active_purchase_months
  FROM `driiiportfolio.starbucks_rewards_lab_restart.fact_member_month`
  WHERE month_start BETWEEN DATE '2026-04-01' AND DATE '2026-06-01'
  GROUP BY member_id
), costs AS (
  SELECT member_id, SUM(benefit_cost) AS post_benefit_cost,
    SUM(CAST(eligible_flag AS INT64)) AS eligible_events,
    SUM(CAST(campaign_exposed_flag AS INT64)) AS exposed_events,
    SUM(CAST(benefit_used_flag AS INT64)) AS used_events
  FROM `driiiportfolio.starbucks_rewards_lab_restart.fact_benefit_events`
  WHERE month_start BETWEEN DATE '2026-04-01' AND DATE '2026-06-01'
  GROUP BY member_id
)
SELECT d.member_id, d.tier_at_launch, d.acquisition_channel, d.region_group,
  d.assignment_group, d.assignment_probability, p.pre_contribution, p.pre_transactions,
  p.pre_net_sales, q.post_contribution, q.post_transactions, q.post_net_sales,
  CAST(q.post_transactions > 0 AS INT64) AS post_purchaser,
  COALESCE(c.post_benefit_cost, 0) AS post_benefit_cost,
  COALESCE(c.eligible_events, 0) AS eligible_events,
  COALESCE(c.exposed_events, 0) AS exposed_events,
  COALESCE(c.used_events, 0) AS used_events
FROM `driiiportfolio.starbucks_rewards_lab_restart.dim_member` d
JOIN pre p USING (member_id)
JOIN post q USING (member_id)
LEFT JOIN costs c USING (member_id)
WHERE d.eligible_for_experiment
  AND d.assignment_group IN ('TREATMENT', 'CONTROL');
