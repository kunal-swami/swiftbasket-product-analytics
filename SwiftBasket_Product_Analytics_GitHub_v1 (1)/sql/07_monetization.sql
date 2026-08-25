WITH costs AS (
    SELECT order_id, SUM(unit_cost * quantity) AS cogs
    FROM order_items GROUP BY 1
), delivered AS (
    SELECT o.*, c.cogs,
           o.order_value - o.refund_amount - c.cogs
             - o.fulfillment_cost - o.payment_processing_cost AS contribution_margin
    FROM orders o JOIN costs c USING (order_id)
    WHERE o.final_status='delivered'
)
SELECT DATE_TRUNC('month', order_placed_at)::date AS month,
       COUNT(*) AS delivered_orders,
       ROUND(SUM(order_value),2) AS gmv,
       ROUND(AVG(order_value),2) AS aov,
       ROUND(SUM(order_value) / COUNT(DISTINCT user_id),2) AS gmv_per_buyer,
       ROUND(AVG(contribution_margin),2) AS contribution_margin_per_order
FROM delivered GROUP BY 1 ORDER BY 1;

WITH buyer_orders AS (
    SELECT user_id, COUNT(*) AS delivered_orders
    FROM orders WHERE final_status='delivered' GROUP BY 1
)
SELECT COUNT(*) AS buyers,
       ROUND(AVG((delivered_orders >= 2)::int),4) AS repeat_purchase_rate,
       ROUND(AVG(delivered_orders),2) AS orders_per_buyer
FROM buyer_orders;
