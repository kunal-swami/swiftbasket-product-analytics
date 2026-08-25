# Guided Analysis Order

The portfolio keeps production logic in scripts and SQL rather than committing bulky executed notebooks.

1. Run `src/generator/generate.py` and inspect the validation summary.
2. Review the ordered funnel in `sql/03_funnel_analysis.sql`.
3. Calculate D1/D7/D14/D30 retention with `sql/04_cohort_retention.sql`.
4. Reproduce the channel and cart-band diagnosis in `sql/08_root_cause.sql`.
5. Review intent-to-treat output in `sql/09_experiment_analysis.sql`.
6. Run `python -m src.analyze` to reproduce the confidence interval and dashboard aggregates.

An interview candidate should be able to explain each assumption without relying on notebook output cells.
