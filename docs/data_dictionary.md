# Data dictionary and grain contracts

## `raw_members.csv` — one row per synthetic member
- `member_id` STRING: unique synthetic ID.
- `enrollment_date` DATE: synthetic historical enrollment date.
- `tier_at_launch` STRING: GREEN / GOLD / RESERVE synthetic category.
- `acquisition_channel` STRING: APP / IN_STORE / WEB / REFERRAL.
- `region_group` STRING: WEST / CENTRAL / EAST / SOUTH; not real market assignment.
- `prior_90d_transactions` INT: synthetic baseline proxy.
- `prior_90d_net_sales` NUMERIC: synthetic baseline proxy.
- `eligible_for_experiment` BOOL: active at the end of March and eligible for April assignment.
- `assignment_group` STRING: TREATMENT / CONTROL / NOT_ELIGIBLE.
- `assignment_date` DATE: 2026-04-01 for eligible members; blank otherwise.
- `assignment_probability` FLOAT: 0.5 for eligible members; null otherwise.

## `raw_member_month.csv` — exactly one row per member and month (six rows/member)
- Key: (`member_id`, `month_start`).
- `period_phase`: PRE for Jan-Mar; POST for Apr-Jun.
- `active_at_start`, `active_at_end`: panel activity flags; inactive status is absorbing.
- `transaction_count`: nonnegative integer; zero for inactive members.
- `net_sales`, `variable_cost`, `reward_cost`, `benefit_cost`, `intervention_cost`: nonnegative synthetic USD-like amounts.
- `contribution`: `net_sales - variable_cost - reward_cost - benefit_cost - intervention_cost`, rounded to cents.

## `raw_benefit_events.csv` — one synthetic opportunity per member per post-period month
- Key: `event_id`; member/month is also unique in this prototype.
- `eligible_flag`: member is eligible and active at the start of that post month.
- `campaign_exposed_flag`: treatment assignment, active eligibility, and a stochastic exposure draw all apply.
- `benefit_used_flag`: synthetic use; organic use can occur in either arm, while exposure raises the use probability.
- `benefit_cost`: zero when unused; positive synthetic cost when used. Event costs reconcile to member-month ledger costs.

## `raw_market_context.csv` — one row per month
- `market_index`, `seasonality_index`: explicit synthetic assumptions only.
- `source_type`: `SYNTHETIC_ASSUMPTION`; not actual syndicated data.

## Join rules
- Member-month joins to members on `member_id` (many-to-one).
- Benefit events join to members on `member_id` (many-to-one).
- Market context joins to member-month on `month_start` (many-to-one).
- Do not join raw benefit events directly to member-month and then sum member-month measures without pre-aggregating events; that would multiply monetary outcomes.
