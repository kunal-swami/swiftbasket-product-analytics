# Data Dictionary

| Table | Grain | Key fields | Analytical purpose |
|---|---|---|---|
| `users` | One user | `user_id`, acquisition, first seen, city/platform | Acquisition cohorts and eligibility |
| `sessions` | One app session | `session_id`, `user_id`, start/end, app version | Activity, retention, engagement |
| `events` | One behavioral event | event/user/session IDs, name and timestamp | Ordered funnel and feature usage |
| `searches` | One submitted search | query, results and response time | Search success and discovery |
| `checkout_attempts` | One checkout journey | cart economics, fees, outcome | Checkout abandonment and fee friction |
| `payment_attempts` | One digital payment attempt | method, provider, status and failure | Success, failure and retry analysis |
| `orders` | One created order | value, final status, refund and costs | GMV, AOV, fulfilment and contribution |
| `order_items` | One SKU line per order | product, quantity, price and cost | Category and unit-economics analysis |
| `order_status_history` | One order status transition | status and timestamp | Fulfilment sequence |
| `experiment_assignments` | One user per experiment | variant, assignment and exposure | Intent-to-treat analysis |
| `stores` | One fictional service zone | city and zone | Geography segmentation |
| `products` | One simulated SKU | category, brand and price | Product/category segmentation |

## Event taxonomy

| Journey | Events |
|---|---|
| Entry and onboarding | `app_open`, `home_view`, `serviceability_checked`, `signup_started` |
| Discovery | `search_submitted`, `search_results_viewed`, `zero_results_seen`, `category_viewed`, `product_viewed` |
| Purchase intent | `add_to_cart`, `cart_viewed` |
| Checkout | `checkout_started`, `fee_breakdown_viewed` |
| Payment | `payment_attempted`, `payment_failed`, `payment_succeeded` |
| Purchase | `order_placed` |
| Experiment | `experiment_exposure` |

Backend delivery transitions are stored in `order_status_history` rather than duplicated as in-session behavioral events.
