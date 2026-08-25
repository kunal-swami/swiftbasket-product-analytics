from __future__ import annotations

from typing import Any

import pandas as pd


class DataValidationError(ValueError):
    """Raised when generated behavioral data violates a data contract."""


def validate_generated_data(frames: dict[str, pd.DataFrame], config: dict[str, Any]) -> dict[str, Any]:
    users = frames["users"]
    sessions = frames["sessions"]
    events = frames["events"]
    checkouts = frames["checkout_attempts"]
    payments = frames["payment_attempts"]
    orders = frames["orders"]
    items = frames["order_items"]

    checks: list[tuple[str, bool]] = [
        ("user_id unique", users["user_id"].is_unique),
        ("session_id unique", sessions["session_id"].is_unique),
        ("event_id unique", events["event_id"].is_unique),
        ("checkout_id unique", checkouts.empty or checkouts["checkout_id"].is_unique),
        ("payment_attempt_id unique", payments.empty or payments["payment_attempt_id"].is_unique),
        ("order_id unique", orders.empty or orders["order_id"].is_unique),
        ("order_item_id unique", items.empty or items["order_item_id"].is_unique),
        ("session timestamps ordered", (sessions["session_ended_at"] >= sessions["session_started_at"]).all()),
        ("event users valid", events["user_id"].isin(users["user_id"]).all()),
        ("event sessions valid", events["session_id"].isin(sessions["session_id"]).all()),
        ("checkout sessions valid", checkouts.empty or checkouts["session_id"].isin(sessions["session_id"]).all()),
        ("payments reference checkout", payments.empty or payments["checkout_id"].isin(checkouts["checkout_id"]).all()),
        ("orders reference checkout", orders.empty or orders["checkout_id"].isin(checkouts["checkout_id"]).all()),
        ("items reference order", items.empty or items["order_id"].isin(orders["order_id"]).all()),
    ]

    if not checkouts.empty:
        expected_total = (
            checkouts["subtotal"] + checkouts["delivery_fee"]
            + checkouts["handling_fee"] - checkouts["discount_amount"]
        ).round(2)
        checks.append(("checkout totals reconcile", (expected_total - checkouts["total_payable"]).abs().le(0.01).all()))
    if not orders.empty:
        expected_order = (
            orders["subtotal"] + orders["delivery_fee"]
            + orders["handling_fee"] - orders["discount_amount"]
        ).round(2)
        checks.append(("order totals reconcile", (expected_order - orders["order_value"]).abs().le(0.01).all()))
        checks.append(("one order per checkout", orders["checkout_id"].is_unique))
    if not items.empty:
        expected_item = (items["unit_price"] * items["quantity"] - items["item_discount"]).round(2)
        checks.append(("item totals reconcile", (expected_item - items["item_total"]).abs().le(0.01).all()))

    failed = [name for name, passed in checks if not bool(passed)]
    if failed:
        raise DataValidationError("Generated data failed: " + ", ".join(failed))

    return {
        "checks_passed": len(checks),
        "users": len(users), "sessions": len(sessions), "events": len(events),
        "checkouts": len(checkouts), "payments": len(payments), "orders": len(orders),
    }
