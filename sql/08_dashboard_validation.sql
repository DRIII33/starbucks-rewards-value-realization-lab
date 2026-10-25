-- Dashboard source QA. Required execution order:
--   1) sql/03_build_analytics.sql (only for an intentional warehouse rebuild)
--   2) sql/07_create_dashboard_views.sql
--   3) Load outputs/looker_studio_results.csv into
--      `driiiportfolio.starbucks_rewards_lab_restart.looker_studio_results`
--   4) Run this file.
--
-- Important: sql/07_create_dashboard_views.sql creates views only. It does NOT
-- create or load `looker_studio_results`; the CSV must be loaded separately.
-- These SELECTs are diagnostic/reconciliation queries; inspect the returned values.

-- 1. Monthly arm view must have one row per month x arm (6 x 2 = 12).
SELECT COUNT(*) AS rows_expected_12,
       COUNT(DISTINCT CONCAT(CAST(month_start AS STRING), '|', assignment_group)) AS unique_month_arm_keys,
       COUNT(*) = 12 AS expected_row_count_passed
FROM `driiiportfolio.starbucks_rewards_lab_restart.vw_dashboard_monthly_arm_performance`;

-- 2. Reconcile randomized counts and post-period contribution means to Python output.
SELECT assignment_group, randomized_members,
       mean_post_contribution_per_member,
       mean_post_transactions_per_member,
       mean_post_net_sales_per_member,
       post_purchaser_rate,
       mean_post_benefit_cost_per_member
FROM `driiiportfolio.starbucks_rewards_lab_restart.vw_dashboard_experiment_arm_summary`
ORDER BY assignment_group;

-- 3. Reconcile Python primary result table to the expected current run.
-- If the synthetic seed or input data changes, regenerate and update the reference values.
SELECT analysis_run_id, analysis_code_version, result_type, outcome,
       n_treatment, n_control, mean_treatment, mean_control,
       effect_estimate, ci95_low, ci95_high, p_value_two_sided
FROM `driiiportfolio.starbucks_rewards_lab_restart.looker_studio_results`
WHERE result_type = 'ITT_OUTCOME' AND outcome = 'post_contribution';

-- 4. Verify only one primary row and one adjusted sensitivity row are present.
SELECT
  COUNTIF(result_type = 'ITT_OUTCOME' AND is_primary AND outcome = 'post_contribution') = 1
    AS exactly_one_primary_result,
  COUNTIF(result_type = 'ADJUSTED_SENSITIVITY') = 1
    AS exactly_one_adjusted_sensitivity,
  COUNTIF(NOT synthetic_data_only) = 0 AS all_rows_marked_synthetic,
  COUNT(DISTINCT analysis_run_id) = 1 AS single_analysis_run
FROM `driiiportfolio.starbucks_rewards_lab_restart.looker_studio_results`;

-- 5. Monthly activity view must have one row per month x arm and rates within [0, 1].
SELECT *
FROM `driiiportfolio.starbucks_rewards_lab_restart.vw_dashboard_monthly_arm_performance`
WHERE purchasing_member_rate < 0 OR purchasing_member_rate > 1
   OR active_at_start_rate < 0 OR active_at_start_rate > 1;

-- 6. Benefit summary: event counts and costs by arm/tier. Control use-per-exposed is NULL
-- because control has no exposed events; do not replace that NULL with zero.
SELECT assignment_group, tier_at_launch, eligible_events, exposed_events,
       exposed_and_used_events, use_per_exposed_event, benefit_cost_total
FROM `driiiportfolio.starbucks_rewards_lab_restart.vw_dashboard_benefit_arm_summary`
ORDER BY assignment_group, tier_at_launch;

-- 7. Check dashboard summary table has no duplicate result keys.
SELECT result_type, outcome, COUNT(*) AS row_count
FROM `driiiportfolio.starbucks_rewards_lab_restart.looker_studio_results`
GROUP BY result_type, outcome
HAVING COUNT(*) != 1;
