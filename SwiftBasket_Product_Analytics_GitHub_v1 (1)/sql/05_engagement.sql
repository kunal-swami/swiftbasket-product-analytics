WITH session_days AS (
    SELECT DISTINCT user_id, session_started_at::date AS activity_date FROM sessions
), dates AS (
    SELECT GENERATE_SERIES(MIN(activity_date), MAX(activity_date), INTERVAL '1 day')::date AS activity_date
    FROM session_days
)
SELECT d.activity_date,
       COUNT(DISTINCT s.user_id) FILTER (WHERE s.activity_date = d.activity_date) AS dau,
       COUNT(DISTINCT s.user_id) FILTER (WHERE s.activity_date BETWEEN d.activity_date - 6 AND d.activity_date) AS wau,
       COUNT(DISTINCT s.user_id) FILTER (WHERE s.activity_date BETWEEN d.activity_date - 29 AND d.activity_date) AS mau,
       ROUND(
          COUNT(DISTINCT s.user_id) FILTER (WHERE s.activity_date = d.activity_date)::numeric /
          NULLIF(COUNT(DISTINCT s.user_id) FILTER (WHERE s.activity_date BETWEEN d.activity_date - 29 AND d.activity_date),0), 4
       ) AS dau_mau_stickiness
FROM dates d
LEFT JOIN session_days s ON s.activity_date BETWEEN d.activity_date - 29 AND d.activity_date
GROUP BY 1 ORDER BY 1;

SELECT DATE_TRUNC('week', session_started_at)::date AS week,
       COUNT(*) AS sessions,
       COUNT(DISTINCT user_id) AS active_users,
       ROUND(COUNT(*)::numeric / COUNT(DISTINCT user_id), 2) AS sessions_per_user
FROM sessions GROUP BY 1 ORDER BY 1;
