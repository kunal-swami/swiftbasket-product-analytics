# Experiment Readout — Early Fee Transparency

## Design

- **Hypothesis:** showing handling fees and estimated payable total in the cart will reduce checkout surprise and improve seven-day order conversion.
- **Control:** fee first appears during checkout.
- **Treatment:** fee and payable estimate appear in the cart.
- **Randomization unit:** user.
- **Primary analysis:** intent-to-treat.
- **Primary metric:** order placed within seven days of assignment.
- **Guardrails:** AOV, contribution margin/order, cancellation, refund and D7 retention.

## Result

| Variant | Assigned users | Exposed users | 7-day conversion |
|---|---:|---:|---:|
| Control | 4,916 | 1,559 | 10.54% |
| Treatment | 4,891 | 1,609 | 10.75% |

- Absolute difference: **+0.22 percentage points**.
- Relative difference: **+2.1%**.
- Two-sided p-value: **0.727**.
- 95% confidence interval: **−1.00 to +1.44 percentage points**.

## Decision

The experiment is inconclusive. The interval includes meaningful harm, no effect and meaningful benefit. Do not ship it as a conversion improvement based on this evidence.

Transparency may still improve trust or reduce support contacts, but those outcomes require explicitly instrumented metrics. A separate experiment should test the fee amount or first-order waiver; combining transparency and a waiver would prevent causal attribution.

At roughly 10.5% baseline conversion, approximately **15.4K users per arm** are needed to detect a one-percentage-point absolute lift with 80% power and a 5% two-sided significance level.
