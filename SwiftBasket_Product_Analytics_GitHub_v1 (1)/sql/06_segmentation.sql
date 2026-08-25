WITH first_orders AS (
    SELECT user_id, MIN(order_placed_at) AS first_order_at FROM orders GROUP BY 1
)
SELECT u.acquisition_channel, u.initial_platform, u.device_tier, u.initial_city,
       COUNT(*) AS users,
       ROUND(AVG(COALESCE(f.first_order_at <= u.first_seen_at + INTERVAL '7 days', FALSE)::int),4) AS conversion_7d,
       ROUND(AVG(u.acquisition_cost),2) AS average_cac
FROM users u LEFT JOIN first_orders f USING (user_id)
WHERE u.is_serviceable AND u.signup_completed_at IS NOT NULL
GROUP BY 1,2,3,4
HAVING COUNT(*) >= 50
ORDER BY conversion_7d;

SELECT p.payment_method,
       COUNT(*) AS attempts,
       ROUND(AVG((p.payment_status='success')::int),4) AS success_rate,
       ROUND(AVG(p.processing_time_ms),0) AS average_processing_ms,
       ROUND(AVG(p.attempt_number),2) AS average_attempt_number
FROM payment_attempts p GROUP BY 1 ORDER BY success_rate DESC;
