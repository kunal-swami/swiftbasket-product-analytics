-- Ordered seven-day new-user funnel. A user reaches a stage only after reaching the prior stage.
WITH eligible AS (
    SELECT user_id, first_seen_at
    FROM users
    WHERE is_serviceable AND signup_completed_at IS NOT NULL
      AND first_seen_at < TIMESTAMPTZ '2026-08-01 00:00:00+00'
), stage_times AS (
    SELECT e.user_id,
           MIN(e.event_timestamp) FILTER (WHERE e.event_name = 'app_open') AS app_open_at,
           MIN(e.event_timestamp) FILTER (WHERE e.event_name IN ('search_submitted','category_viewed')) AS discovery_at,
           MIN(e.event_timestamp) FILTER (WHERE e.event_name = 'product_viewed') AS product_view_at,
           MIN(e.event_timestamp) FILTER (WHERE e.event_name = 'add_to_cart') AS add_to_cart_at,
           MIN(e.event_timestamp) FILTER (WHERE e.event_name = 'checkout_started') AS checkout_at,
           MIN(e.event_timestamp) FILTER (WHERE e.event_name = 'payment_attempted') AS payment_at,
           MIN(e.event_timestamp) FILTER (WHERE e.event_name = 'order_placed') AS order_at
    FROM events e
    JOIN eligible u USING (user_id)
    WHERE e.event_timestamp <= u.first_seen_at + INTERVAL '7 days'
    GROUP BY 1
), reached AS (
    SELECT *,
      app_open_at IS NOT NULL AS r1,
      discovery_at >= app_open_at AS r2,
      product_view_at >= discovery_at AS r3,
      add_to_cart_at >= product_view_at AS r4,
      checkout_at >= add_to_cart_at AS r5,
      payment_at >= checkout_at AS r6,
      order_at >= payment_at AS r7
    FROM stage_times
), counts AS (
    SELECT COUNT(*) FILTER (WHERE r1) app_open,
           COUNT(*) FILTER (WHERE r1 AND r2) discovery,
           COUNT(*) FILTER (WHERE r1 AND r2 AND r3) product_view,
           COUNT(*) FILTER (WHERE r1 AND r2 AND r3 AND r4) add_to_cart,
           COUNT(*) FILTER (WHERE r1 AND r2 AND r3 AND r4 AND r5) checkout,
           COUNT(*) FILTER (WHERE r1 AND r2 AND r3 AND r4 AND r5 AND r6) payment,
           COUNT(*) FILTER (WHERE r1 AND r2 AND r3 AND r4 AND r5 AND r6 AND r7) purchase
    FROM reached
)
SELECT * FROM counts;

-- Segment-level first-order conversion.
WITH first_orders AS (
    SELECT user_id, MIN(order_placed_at) AS first_order_at FROM orders GROUP BY 1
)
SELECT u.acquisition_channel, u.initial_platform, u.initial_city,
       COUNT(*) AS new_users,
       COUNT(*) FILTER (
          WHERE f.first_order_at BETWEEN u.first_seen_at AND u.first_seen_at + INTERVAL '7 days'
       ) AS converted_users,
       ROUND(COUNT(*) FILTER (
          WHERE f.first_order_at BETWEEN u.first_seen_at AND u.first_seen_at + INTERVAL '7 days'
       )::numeric / COUNT(*), 4) AS conversion_7d
FROM users u
LEFT JOIN first_orders f USING (user_id)
WHERE u.is_serviceable AND u.signup_completed_at IS NOT NULL
GROUP BY 1,2,3
ORDER BY conversion_7d;
