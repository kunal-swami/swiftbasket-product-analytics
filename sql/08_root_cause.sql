-- Checkout-to-payment deterioration is localized by period and basket value.
SELECT CASE WHEN checkout_started_at < TIMESTAMPTZ '2026-04-15' THEN 'pre_change' ELSE 'post_change' END AS period,
       CASE WHEN subtotal < 199 THEN '<199'
            WHEN subtotal < 399 THEN '199-398' ELSE '399+' END AS cart_band,
       COUNT(*) AS checkouts,
       ROUND(AVG((checkout_outcome IN ('payment_failed','order_created'))::int),4) AS payment_attempt_rate,
       ROUND(AVG((checkout_outcome='order_created')::int),4) AS checkout_completion_rate
FROM checkout_attempts
GROUP BY 1,2 ORDER BY 1,2;

-- Channel composition and within-channel conversion: separates mix from product effects.
WITH first_orders AS (
    SELECT user_id, MIN(order_placed_at) first_order_at FROM orders GROUP BY 1
), base AS (
    SELECT u.user_id, u.acquisition_channel,
           CASE WHEN u.first_seen_at < TIMESTAMPTZ '2026-04-15' THEN 'pre_change' ELSE 'post_change' END period,
           COALESCE(f.first_order_at BETWEEN u.first_seen_at AND u.first_seen_at + INTERVAL '7 days', FALSE)::int converted
    FROM users u LEFT JOIN first_orders f USING(user_id)
)
SELECT period, acquisition_channel, COUNT(*) users,
       ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER(PARTITION BY period),4) channel_share,
       ROUND(AVG(converted),4) conversion_7d
FROM base GROUP BY 1,2 ORDER BY 1,2;
