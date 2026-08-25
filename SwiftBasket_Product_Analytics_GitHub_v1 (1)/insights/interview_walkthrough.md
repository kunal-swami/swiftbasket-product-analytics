# Ten-Minute Interview Walkthrough

## 0:00–1:00 — Problem

“I created SwiftBasket, a fictional quick-commerce product, using a reproducible synthetic event dataset. The PM request was ambiguous: acquisition was healthy, but first-order conversion appeared to decline. I had to define conversion, locate the change, separate traffic mix from product friction and recommend an experiment.”

## 1:00–2:00 — Measurement

“I defined the North Star as weekly successful delivered orders. The problem metric was the percentage of serviceable, signed-up new users completing a delivered first order within seven days. I excluded immature cohorts. Guardrails included cancellation, refunds, retention and contribution margin.”

## 2:00–4:00 — Data and SQL

“The model contains users, sessions, events, searches, checkouts, payment attempts, orders, items, status history and experiment assignments. I used ordered event timestamps—not independent event counts—to calculate the funnel, and used CTEs, conditional aggregation, window functions and multi-table joins while preventing order-value duplication.”

## 4:00–6:00 — Discovery

“Seven-day conversion fell from 9.40% to 8.67%, a 7.8% relative decline. Meta Ads’ share increased, so I decomposed the change: mix explained 0.33 points, but within-channel deterioration explained another 0.40. Checkout-to-payment attempts fell most below ₹399 and barely changed above ₹399, where the fee was waived. That localized the primary product issue to fee friction, with channel mix acting as an amplifier.”

## 6:00–8:00 — Experiment

“I randomized eligible July users before exposure. Control saw fees at checkout; treatment saw them earlier in the cart. Treatment conversion was 10.75% versus 10.54% control, but p was 0.727 and the confidence interval ranged from −1.00 to +1.44 points. I did not call it a win. The test was underpowered for small effects and transparency might only move abandonment earlier.”

## 8:00–9:30 — Recommendation

“I would next test a first-order fee waiver below ₹399, separately from transparency, while monitoring contribution margin. I would also optimize Meta Ads toward converted users and build a cart-band checkout health monitor.”

## 9:30–10:00 — Learning

“The key learning was that aggregate conversion can hide both composition and within-segment effects. A statistically neutral experiment can still improve the decision by ruling out an overly simple solution.”

## Follow-up questions to practise

1. Why did you use a seven-day rather than same-session conversion window?
2. How did you handle immature cohorts?
3. Why is weekly successful orders a better North Star than app opens or GMV alone?
4. How did you ensure users reached funnel stages in order?
5. Why does a within-channel pre/post decline still not prove causality?
6. How did you calculate the acquisition-mix effect?
7. Why did you analyze the experiment by assignment rather than exposure?
8. What does the confidence interval mean for the product decision?
9. What if conversion rises but contribution margin or D30 retention declines?
10. What additional production data would you request?
