-- Exact-day retention. Denominators include only cohorts mature for each day.
WITH parameters AS (
    SELECT DATE '2026-08-08' AS analysis_date
), acquired AS (
    SELECT user_id, first_seen_at::date AS cohort_date,
           DATE_TRUNC('week', first_seen_at)::date AS cohort_week
    FROM users
), active_days AS (
    SELECT DISTINCT user_id, session_started_at::date AS activity_date
    FROM sessions
), retention_days AS (
    SELECT * FROM (VALUES (1),(7),(14),(30)) AS d(day_number)
), eligible AS (
    SELECT a.*, d.day_number
    FROM acquired a
    CROSS JOIN retention_days d
    CROSS JOIN parameters p
    WHERE a.cohort_date <= p.analysis_date - d.day_number
), cohort_results AS (
    SELECT e.cohort_week, e.day_number,
           COUNT(DISTINCT e.user_id) AS eligible_users,
           COUNT(DISTINCT a.user_id) AS retained_users
    FROM eligible e
    LEFT JOIN active_days a
      ON a.user_id=e.user_id
     AND a.activity_date=e.cohort_date + e.day_number
    GROUP BY 1,2
)
SELECT cohort_week, day_number, eligible_users, retained_users,
       ROUND(retained_users::numeric / NULLIF(eligible_users,0),4) AS retention_rate
FROM cohort_results
ORDER BY 1,2;
