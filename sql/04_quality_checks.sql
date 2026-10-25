-- Each query should return zero rows unless a comment says otherwise.
-- Fail loudly on empty/incomplete tables before interpreting zero-row checks.
ASSERT (SELECT COUNT(*) FROM `driiiportfolio.starbucks_rewards_lab_restart.raw_members`) = 20000
  AS 'raw_members must contain exactly 20,000 rows';
ASSERT (SELECT COUNT(*) FROM `driiiportfolio.starbucks_rewards_lab_restart.raw_member_month`) = 120000
  AS 'raw_member_month must contain exactly 120,000 rows';
ASSERT (SELECT COUNT(*) FROM `driiiportfolio.starbucks_rewards_lab_restart.raw_benefit_events`) = 60000
  AS 'raw_benefit_events must contain exactly 60,000 rows';
ASSERT (SELECT COUNT(*) FROM `driiiportfolio.starbucks_rewards_lab_restart.raw_market_context`) = 6
  AS 'raw_market_context must contain exactly 6 rows';
ASSERT (SELECT COUNT(*) FROM `driiiportfolio.starbucks_rewards_lab_restart.dim_member`) = 20000
  AS 'dim_member must contain exactly 20,000 rows';
ASSERT (SELECT COUNT(*) FROM `driiiportfolio.starbucks_rewards_lab_restart.fact_member_month`) = 120000
  AS 'fact_member_month must contain exactly 120,000 rows';
ASSERT (SELECT COUNT(*) FROM `driiiportfolio.starbucks_rewards_lab_restart.fact_benefit_events`) = 60000
  AS 'fact_benefit_events must contain exactly 60,000 rows';
ASSERT (SELECT COUNT(*) FROM `driiiportfolio.starbucks_rewards_lab_restart.dim_market_context`) = 6
  AS 'dim_market_context must contain exactly 6 rows';

-- 1. Duplicate member keys
SELECT member_id, COUNT(*) AS n FROM `driiiportfolio.starbucks_rewards_lab_restart.dim_member`
GROUP BY member_id HAVING COUNT(*) != 1;
-- 2. Duplicate member-month grain
SELECT member_id, month_start, COUNT(*) AS n
FROM `driiiportfolio.starbucks_rewards_lab_restart.fact_member_month`
GROUP BY member_id, month_start HAVING COUNT(*) != 1;
-- 3. Orphan member-months
SELECT f.member_id FROM `driiiportfolio.starbucks_rewards_lab_restart.fact_member_month` f
LEFT JOIN `driiiportfolio.starbucks_rewards_lab_restart.dim_member` d USING (member_id)
WHERE d.member_id IS NULL;
-- 4. Invalid tier or assignment labels
SELECT * FROM `driiiportfolio.starbucks_rewards_lab_restart.dim_member`
WHERE tier_at_launch IS NULL OR assignment_group IS NULL
   OR tier_at_launch NOT IN ('GREEN', 'GOLD', 'RESERVE')
   OR assignment_group NOT IN ('TREATMENT', 'CONTROL', 'NOT_ELIGIBLE');
-- 5. Monetary reconciliation; should return zero rows
SELECT * FROM `driiiportfolio.starbucks_rewards_lab_restart.fact_member_month`
WHERE ABS(contribution - (net_sales - variable_cost - reward_cost - benefit_cost - intervention_cost)) > NUMERIC '0.011';
-- 6. Event-to-ledger benefit cost reconciliation; should return zero rows
WITH event_cost AS (
 SELECT member_id, month_start, SUM(benefit_cost) AS benefit_cost
 FROM `driiiportfolio.starbucks_rewards_lab_restart.fact_benefit_events` GROUP BY member_id, month_start
)
SELECT f.member_id, f.month_start, f.benefit_cost AS ledger_cost, COALESCE(e.benefit_cost, 0) AS event_cost
FROM `driiiportfolio.starbucks_rewards_lab_restart.fact_member_month` f
LEFT JOIN event_cost e USING (member_id, month_start)
WHERE ABS(f.benefit_cost - COALESCE(e.benefit_cost, 0)) > NUMERIC '0.011';
-- 7. Invalid event logic; should return zero rows
SELECT * FROM `driiiportfolio.starbucks_rewards_lab_restart.fact_benefit_events`
WHERE (campaign_exposed_flag AND NOT eligible_flag)
   OR (benefit_used_flag AND NOT eligible_flag)
   OR benefit_cost < 0;
-- 8. Assignment counts (inspect output; not a zero-row test)
SELECT tier_at_launch, assignment_group, COUNT(*) AS members
FROM `driiiportfolio.starbucks_rewards_lab_restart.dim_member`
WHERE eligible_for_experiment GROUP BY tier_at_launch, assignment_group
ORDER BY tier_at_launch, assignment_group;
-- 9. Expected panel row count (should equal member count * 6)
SELECT (SELECT COUNT(*) FROM `driiiportfolio.starbucks_rewards_lab_restart.fact_member_month`) AS panel_rows,
       (SELECT COUNT(*) FROM `driiiportfolio.starbucks_rewards_lab_restart.dim_member`) * 6 AS expected_rows,
       (SELECT COUNT(*) FROM `driiiportfolio.starbucks_rewards_lab_restart.fact_member_month`) =
         (SELECT COUNT(*) FROM `driiiportfolio.starbucks_rewards_lab_restart.dim_member`) * 6
         AND (SELECT COUNT(*) FROM `driiiportfolio.starbucks_rewards_lab_restart.fact_member_month`) > 0 AS passed;

-- 10. Required fields and monetary values must not be NULL; should return zero rows.
SELECT 'fact_member_month' AS table_name, member_id AS row_key
FROM `driiiportfolio.starbucks_rewards_lab_restart.fact_member_month`
WHERE member_id IS NULL OR month_start IS NULL OR period_phase IS NULL
   OR active_at_start IS NULL OR active_at_end IS NULL OR transaction_count IS NULL
   OR net_sales IS NULL OR variable_cost IS NULL OR reward_cost IS NULL
   OR benefit_cost IS NULL OR intervention_cost IS NULL OR contribution IS NULL
UNION ALL
SELECT 'dim_member' AS table_name, member_id AS row_key
FROM `driiiportfolio.starbucks_rewards_lab_restart.dim_member`
WHERE member_id IS NULL OR enrollment_date IS NULL OR tier_at_launch IS NULL
   OR acquisition_channel IS NULL OR region_group IS NULL
   OR eligible_for_experiment IS NULL OR assignment_group IS NULL
UNION ALL
SELECT 'fact_benefit_events' AS table_name, event_id AS row_key
FROM `driiiportfolio.starbucks_rewards_lab_restart.fact_benefit_events`
WHERE event_id IS NULL OR member_id IS NULL OR month_start IS NULL
   OR eligible_flag IS NULL OR campaign_exposed_flag IS NULL
   OR benefit_used_flag IS NULL OR benefit_cost IS NULL;
-- 11. Phase/month boundary and activity-state transitions; should return zero rows.
WITH ordered AS (
 SELECT member_id, month_start, period_phase, active_at_start, active_at_end,
   LEAD(active_at_start) OVER (PARTITION BY member_id ORDER BY month_start) AS next_month_active_at_start
 FROM `driiiportfolio.starbucks_rewards_lab_restart.fact_member_month`
)
SELECT * FROM ordered
WHERE (month_start < DATE '2026-04-01' AND period_phase != 'PRE')
   OR (month_start >= DATE '2026-04-01' AND period_phase != 'POST')
   OR (active_at_start = FALSE AND active_at_end = TRUE)
   OR (next_month_active_at_start IS NOT NULL AND active_at_end != next_month_active_at_start);
-- 12. Exposure assignment and both benefit/intervention costs reconcile to event flags.
SELECT e.event_id, e.member_id, e.month_start, e.campaign_exposed_flag,
       e.benefit_used_flag, e.benefit_cost, f.intervention_cost
FROM `driiiportfolio.starbucks_rewards_lab_restart.fact_benefit_events` e
JOIN `driiiportfolio.starbucks_rewards_lab_restart.dim_member` d USING (member_id)
LEFT JOIN `driiiportfolio.starbucks_rewards_lab_restart.fact_member_month` f
  USING (member_id, month_start)
WHERE (e.campaign_exposed_flag AND d.assignment_group != 'TREATMENT')
   OR (e.benefit_used_flag AND e.benefit_cost <= 0)
   OR (NOT e.benefit_used_flag AND e.benefit_cost != 0)
   OR e.benefit_cost IS NULL
   OR f.member_id IS NULL
   OR ABS(f.intervention_cost - IF(e.campaign_exposed_flag, NUMERIC '0.10', NUMERIC '0')) > NUMERIC '0.011';
-- 13. Eligibility/assignment date and probability consistency; should return zero rows.
SELECT * FROM `driiiportfolio.starbucks_rewards_lab_restart.dim_member`
WHERE (eligible_for_experiment AND (assignment_group NOT IN ('TREATMENT','CONTROL') OR assignment_date IS DISTINCT FROM DATE '2026-04-01' OR assignment_probability IS DISTINCT FROM 0.5))
   OR (NOT eligible_for_experiment AND (assignment_group IS DISTINCT FROM 'NOT_ELIGIBLE' OR assignment_date IS NOT NULL OR assignment_probability IS NOT NULL));

-- 14. Duplicate benefit-event IDs and malformed market context; should return zero rows.
SELECT event_id, COUNT(*) AS n
FROM `driiiportfolio.starbucks_rewards_lab_restart.fact_benefit_events`
GROUP BY event_id HAVING COUNT(*) != 1;
SELECT month_start FROM `driiiportfolio.starbucks_rewards_lab_restart.dim_market_context`
WHERE month_start IS NULL OR market_index IS NULL OR seasonality_index IS NULL OR source_type IS NULL;

-- 15. Every member must have one benefit-event row for each of Apr, May and Jun.
SELECT member_id, COUNT(*) AS event_rows, COUNT(DISTINCT month_start) AS distinct_months
FROM `driiiportfolio.starbucks_rewards_lab_restart.fact_benefit_events`
GROUP BY member_id
HAVING COUNT(*) != 3 OR COUNT(DISTINCT month_start) != 3;

-- 16. Market context must cover exactly the six modeled months; should return zero rows.
WITH expected_months AS (
 SELECT month_start FROM UNNEST([
   DATE '2026-01-01', DATE '2026-02-01', DATE '2026-03-01',
   DATE '2026-04-01', DATE '2026-05-01', DATE '2026-06-01'
 ]) AS month_start
), actual_months AS (
 SELECT month_start FROM `driiiportfolio.starbucks_rewards_lab_restart.dim_market_context`
)
SELECT 'MISSING_EXPECTED_MONTH' AS issue, e.month_start
FROM expected_months e LEFT JOIN actual_months a USING (month_start)
WHERE a.month_start IS NULL
UNION ALL
SELECT 'UNEXPECTED_MONTH' AS issue, a.month_start
FROM actual_months a LEFT JOIN expected_months e USING (month_start)
WHERE e.month_start IS NULL;

-- 17. Benefit events must not contain orphan member IDs; should return zero rows.
SELECT e.member_id, e.event_id
FROM `driiiportfolio.starbucks_rewards_lab_restart.fact_benefit_events` e
LEFT JOIN `driiiportfolio.starbucks_rewards_lab_restart.dim_member` d USING (member_id)
WHERE d.member_id IS NULL;

-- 18. Experiment eligibility must equal the March month-end activity state; should return zero rows.
SELECT d.member_id, d.eligible_for_experiment, f.active_at_end AS march_active_at_end
FROM `driiiportfolio.starbucks_rewards_lab_restart.dim_member` d
JOIN `driiiportfolio.starbucks_rewards_lab_restart.fact_member_month` f
  ON d.member_id = f.member_id AND f.month_start = DATE '2026-03-01'
WHERE d.eligible_for_experiment IS DISTINCT FROM f.active_at_end;
