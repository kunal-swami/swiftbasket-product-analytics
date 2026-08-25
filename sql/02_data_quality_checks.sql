-- Data-contract checks. Every query should return zero rows or zero differences.

SELECT event_id, COUNT(*) FROM events GROUP BY 1 HAVING COUNT(*) > 1;

SELECT c.checkout_id
FROM checkout_attempts c
LEFT JOIN sessions s ON s.session_id = c.session_id AND s.user_id = c.user_id
WHERE s.session_id IS NULL;

SELECT checkout_id, total_payable,
       subtotal + delivery_fee + handling_fee - discount_amount AS reconstructed_total
FROM checkout_attempts
WHERE ABS(total_payable - (subtotal + delivery_fee + handling_fee - discount_amount)) > 0.01;

SELECT o.order_id, o.order_value, SUM(oi.item_total) AS item_subtotal
FROM orders o
JOIN order_items oi USING (order_id)
GROUP BY 1, 2, o.subtotal
HAVING ABS(o.subtotal - SUM(oi.item_total)) > 0.01;

WITH sequenced AS (
    SELECT order_id, order_status, status_timestamp,
           LAG(status_timestamp) OVER (PARTITION BY order_id ORDER BY status_timestamp) AS prior_timestamp
    FROM order_status_history
)
SELECT * FROM sequenced WHERE status_timestamp < prior_timestamp;
