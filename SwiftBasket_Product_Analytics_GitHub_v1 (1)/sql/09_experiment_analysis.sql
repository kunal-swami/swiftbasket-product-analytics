-- Intent-to-treat readout: analyze by randomized assignment, not feature usage.
WITH outcomes AS (
    SELECT a.experiment_id, a.variant, a.user_id, a.assigned_at, a.first_exposed_at,
           MIN(o.order_placed_at) FILTER (
               WHERE o.order_placed_at BETWEEN a.assigned_at AND a.assigned_at + INTERVAL '7 days'
           ) AS converted_at
    FROM experiment_assignments a
    LEFT JOIN orders o ON o.user_id=a.user_id
    WHERE a.experiment_id='early_fee_transparency_v1'
    GROUP BY 1,2,3,4,5
)
SELECT variant,
       COUNT(*) AS assigned_users,
       COUNT(first_exposed_at) AS exposed_users,
       ROUND(COUNT(first_exposed_at)::numeric / COUNT(*),4) AS exposure_rate,
       COUNT(converted_at) AS converted_users,
       ROUND(COUNT(converted_at)::numeric / COUNT(*),4) AS conversion_7d
FROM outcomes GROUP BY 1 ORDER BY 1;

-- Statistical significance and confidence intervals are calculated in src/analyze.py.
