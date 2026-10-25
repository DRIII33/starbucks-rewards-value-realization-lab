-- DESTRUCTIVE RESET: drops/recreates the four synthetic raw tables. Run only in this project dataset.
-- Sandbox-safe design: do not time-partition the synthetic date fields.
-- The BigQuery Sandbox can impose a 60-day partition expiry that purges historical slices.
-- These tables are clustered where useful; run this destructive reset only before reloading all four CSVs.
-- Sandbox may still expire entire tables/views after about 60 days; this DDL does not override that policy.
DROP TABLE IF EXISTS `driiiportfolio.starbucks_rewards_lab_restart.raw_members`;
CREATE TABLE `driiiportfolio.starbucks_rewards_lab_restart.raw_members` (
  member_id STRING NOT NULL, enrollment_date DATE, tier_at_launch STRING,
  acquisition_channel STRING, region_group STRING, prior_90d_transactions INT64,
  prior_90d_net_sales NUMERIC, eligible_for_experiment BOOL, assignment_group STRING,
  assignment_date DATE, assignment_probability FLOAT64
);
DROP TABLE IF EXISTS `driiiportfolio.starbucks_rewards_lab_restart.raw_member_month`;
CREATE TABLE `driiiportfolio.starbucks_rewards_lab_restart.raw_member_month` (
  member_id STRING NOT NULL, month_start DATE NOT NULL, period_phase STRING,
  active_at_start BOOL, active_at_end BOOL, transaction_count INT64,
  net_sales NUMERIC, variable_cost NUMERIC, reward_cost NUMERIC,
  benefit_cost NUMERIC, intervention_cost NUMERIC, contribution NUMERIC
)
CLUSTER BY month_start, member_id;
DROP TABLE IF EXISTS `driiiportfolio.starbucks_rewards_lab_restart.raw_benefit_events`;
CREATE TABLE `driiiportfolio.starbucks_rewards_lab_restart.raw_benefit_events` (
  event_id STRING NOT NULL, member_id STRING NOT NULL, month_start DATE NOT NULL,
  benefit_id STRING, eligible_flag BOOL, campaign_exposed_flag BOOL,
  benefit_used_flag BOOL, benefit_cost NUMERIC
)
CLUSTER BY month_start, member_id;
DROP TABLE IF EXISTS `driiiportfolio.starbucks_rewards_lab_restart.raw_market_context`;
CREATE TABLE `driiiportfolio.starbucks_rewards_lab_restart.raw_market_context` (
  month_start DATE NOT NULL, market_index NUMERIC, seasonality_index FLOAT64, source_type STRING
);
