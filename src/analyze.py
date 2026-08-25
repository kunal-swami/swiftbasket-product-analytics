from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm


DATA_DIR = Path("data/generated")
OUTPUT_DIR = Path("data/analysis_outputs")


def _read(name: str, dates: list[str] | None = None) -> pd.DataFrame:
    parquet = DATA_DIR / f"{name}.parquet"
    csv = DATA_DIR / f"{name}.csv"
    if parquet.exists():
        return pd.read_parquet(parquet)
    return pd.read_csv(csv, parse_dates=dates or [])


def _two_proportion_test(success_a: int, n_a: int, success_b: int, n_b: int) -> tuple[float, float, float]:
    rate_a, rate_b = success_a / n_a, success_b / n_b
    pooled = (success_a + success_b) / (n_a + n_b)
    se = np.sqrt(pooled * (1 - pooled) * (1 / n_a + 1 / n_b))
    z = (rate_b - rate_a) / se
    p_value = 2 * (1 - norm.cdf(abs(z)))
    se_diff = np.sqrt(rate_a * (1 - rate_a) / n_a + rate_b * (1 - rate_b) / n_b)
    return float(p_value), float((rate_b - rate_a) - 1.96 * se_diff), float((rate_b - rate_a) + 1.96 * se_diff)


def run_analysis() -> dict[str, float]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    users = _read("users", ["first_seen_at", "signup_completed_at"])
    sessions = _read("sessions", ["session_started_at", "session_ended_at"])
    events = _read("events", ["event_timestamp"])
    checkouts = _read("checkout_attempts", ["checkout_started_at", "checkout_ended_at"])
    orders = _read("orders", ["order_placed_at", "delivered_at", "cancelled_at"])
    items = _read("order_items")
    assignments = _read("experiment_assignments", ["assigned_at", "first_exposed_at"])

    cutoff = pd.Timestamp("2026-08-08", tz="UTC")
    problem_start = pd.Timestamp("2026-04-15", tz="UTC")
    first_delivered = orders[orders["final_status"] == "delivered"].groupby("user_id")["delivered_at"].min()
    cohorts = users.copy()
    cohorts["first_delivered_at"] = cohorts["user_id"].map(first_delivered)
    cohorts["converted_7d"] = (
        (cohorts["first_delivered_at"] - cohorts["first_seen_at"]).dt.total_seconds().between(0, 7 * 86400)
    )
    cohorts["period"] = np.where(cohorts["first_seen_at"] < problem_start, "pre_change", "post_change")
    cohorts["acquisition_week"] = cohorts["first_seen_at"].dt.to_period("W").dt.start_time
    weekly = cohorts.groupby("acquisition_week").agg(
        acquired_users=("user_id", "nunique"),
        converted_users=("converted_7d", "sum"),
        conversion_7d=("converted_7d", "mean"),
    ).reset_index()
    weekly.to_csv(OUTPUT_DIR / "weekly_conversion.csv", index=False)

    eligible = users[users["is_serviceable"] & users["signup_completed_at"].notna()][["user_id", "first_seen_at"]]
    event7 = events.merge(eligible, on="user_id", how="inner")
    event7 = event7[event7["event_timestamp"] <= event7["first_seen_at"] + pd.Timedelta(days=7)]
    stages = ["app_open", "search_submitted", "product_viewed", "add_to_cart", "checkout_started", "payment_attempted", "order_placed"]
    reached: set[int] | None = None
    funnel_rows = []
    prior_count = None
    for stage in stages:
        users_at_stage = set(event7.loc[event7["event_name"] == stage, "user_id"].unique())
        reached = users_at_stage if reached is None else reached.intersection(users_at_stage)
        count = len(reached)
        funnel_rows.append({
            "stage": stage, "users": count,
            "step_conversion": 1.0 if prior_count is None else count / prior_count,
            "overall_conversion": count / len(eligible),
            "drop_off": 0 if prior_count is None else prior_count - count,
        })
        prior_count = count
    funnel = pd.DataFrame(funnel_rows)
    funnel.to_csv(OUTPUT_DIR / "funnel_summary.csv", index=False)

    channel = cohorts.groupby(["period", "acquisition_channel"]).agg(
        users=("user_id", "size"), conversion=("converted_7d", "mean")
    ).reset_index()
    channel["share"] = channel["users"] / channel.groupby("period")["users"].transform("sum")
    pivot_share = channel.pivot(index="acquisition_channel", columns="period", values="share")
    pivot_conv = channel.pivot(index="acquisition_channel", columns="period", values="conversion")
    mix_effect = ((pivot_share["post_change"] - pivot_share["pre_change"]) * pivot_conv["pre_change"]).sum()
    within_effect = (pivot_share["post_change"] * (pivot_conv["post_change"] - pivot_conv["pre_change"])).sum()
    channel.to_csv(OUTPUT_DIR / "channel_decomposition.csv", index=False)

    checkout = checkouts.merge(users[["user_id", "first_seen_at", "acquisition_channel"]], on="user_id")
    checkout["period"] = np.where(checkout["checkout_started_at"] < problem_start, "pre_change", "post_change")
    checkout["payment_attempted"] = checkout["checkout_outcome"].isin(["payment_failed", "order_created"])
    checkout["cart_band"] = pd.cut(checkout["subtotal"], [-1, 199, 399, np.inf], labels=["<₹199", "₹199–398", "₹399+"])
    cart_bands = checkout.groupby(["period", "cart_band"], observed=True).agg(
        checkouts=("checkout_id", "size"), payment_attempt_rate=("payment_attempted", "mean")
    ).reset_index()
    cart_bands.to_csv(OUTPUT_DIR / "checkout_cart_band.csv", index=False)

    session_days = sessions.merge(users[["user_id", "first_seen_at"]], on="user_id")
    session_days["retention_day"] = (
        session_days["session_started_at"].dt.normalize() - session_days["first_seen_at"].dt.normalize()
    ).dt.days
    retention_rows = []
    for day in [1, 7, 14, 30]:
        matured = users[users["first_seen_at"] <= cutoff - pd.Timedelta(days=day)]
        retained = session_days[
            (session_days["retention_day"] == day) & session_days["user_id"].isin(matured["user_id"])
        ]["user_id"].nunique()
        retention_rows.append({"day": f"D{day}", "eligible_users": len(matured), "retained_users": retained, "retention_rate": retained / len(matured)})
    retention = pd.DataFrame(retention_rows)
    retention.to_csv(OUTPUT_DIR / "retention_summary.csv", index=False)

    delivered = orders[orders["final_status"] == "delivered"].copy()
    cost_by_order = items.assign(cogs=items["unit_cost"] * items["quantity"]).groupby("order_id")["cogs"].sum()
    delivered["cogs"] = delivered["order_id"].map(cost_by_order).fillna(0)
    delivered["contribution_margin"] = (
        delivered["order_value"] - delivered["refund_amount"] - delivered["cogs"]
        - delivered["fulfillment_cost"] - delivered["payment_processing_cost"]
    )
    counts = delivered.groupby("user_id").size()

    first_order = orders.groupby("user_id")["order_placed_at"].min()
    experiment = assignments.copy()
    experiment["first_order_at"] = experiment["user_id"].map(first_order)
    experiment["converted_7d"] = (
        (experiment["first_order_at"] - experiment["assigned_at"]).dt.total_seconds().between(0, 7 * 86400)
    )
    exp_summary = experiment.groupby("variant").agg(
        assigned_users=("user_id", "size"), exposed_users=("first_exposed_at", "count"),
        converted_users=("converted_7d", "sum"), conversion_rate=("converted_7d", "mean")
    ).reset_index()
    exp_summary["exposure_rate"] = exp_summary["exposed_users"] / exp_summary["assigned_users"]
    exp_summary.to_csv(OUTPUT_DIR / "experiment_summary.csv", index=False)
    control = exp_summary.set_index("variant").loc["control"]
    treatment = exp_summary.set_index("variant").loc["treatment"]
    p_value, ci_low, ci_high = _two_proportion_test(
        int(control["converted_users"]), int(control["assigned_users"]),
        int(treatment["converted_users"]), int(treatment["assigned_users"]),
    )

    pre_rate = cohorts.loc[cohorts["period"] == "pre_change", "converted_7d"].mean()
    post_rate = cohorts.loc[cohorts["period"] == "post_change", "converted_7d"].mean()
    metrics = {
        "users": int(len(users)), "sessions": int(len(sessions)), "events": int(len(events)),
        "orders": int(len(orders)), "delivered_orders": int(len(delivered)),
        "gmv": round(float(delivered["order_value"].sum()), 2),
        "aov": round(float(delivered["order_value"].mean()), 2),
        "repeat_purchase_rate": round(float((counts >= 2).mean()), 6),
        "mean_contribution_margin": round(float(delivered["contribution_margin"].mean()), 2),
        "pre_conversion_7d": round(float(pre_rate), 6),
        "post_conversion_7d": round(float(post_rate), 6),
        "relative_conversion_change": round(float(post_rate / pre_rate - 1), 6),
        "mix_effect_pp": round(float(mix_effect * 100), 4),
        "within_segment_effect_pp": round(float(within_effect * 100), 4),
        "experiment_control_rate": round(float(control["conversion_rate"]), 6),
        "experiment_treatment_rate": round(float(treatment["conversion_rate"]), 6),
        "experiment_relative_lift": round(float(treatment["conversion_rate"] / control["conversion_rate"] - 1), 6),
        "experiment_absolute_lift_pp": round(float((treatment["conversion_rate"] - control["conversion_rate"]) * 100), 4),
        "experiment_p_value": round(p_value, 6),
        "experiment_ci_low_pp": round(ci_low * 100, 4),
        "experiment_ci_high_pp": round(ci_high * 100, 4),
    }
    for row in retention.itertuples(index=False):
        metrics[f"{row.day.lower()}_retention"] = round(float(row.retention_rate), 6)
    (OUTPUT_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    return metrics


if __name__ == "__main__":
    run_analysis()
