# Dashboard

`screenshots/swiftbasket_executive_dashboard.png` is generated from verified aggregates using `build_dashboard.py`.

The same layout can be recreated in Power BI or Metabase using CSV files under `data/analysis_outputs/`:

1. KPI cards: users, seven-day conversion, GMV/AOV and experiment lift.
2. Weekly conversion trend with a 15 April product-change marker.
3. Ordered new-user funnel.
4. Checkout-to-payment rate by cart band and period.
5. D1/D7/D14/D30 retention.
6. Control versus treatment conversion with the p-value stated in the subtitle.

The dashboard is intentionally limited to decision-relevant visuals.
