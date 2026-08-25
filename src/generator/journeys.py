from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

import numpy as np
import pandas as pd


def _clip(value: float, low: float = 0.01, high: float = 0.99) -> float:
    return float(min(high, max(low, value)))


def generate_activity(
    users: pd.DataFrame,
    private: pd.DataFrame,
    stores: pd.DataFrame,
    products: pd.DataFrame,
    assignments: pd.DataFrame,
    config: dict[str, Any],
    rng: np.random.Generator,
) -> dict[str, pd.DataFrame]:
    """Generate coherent sessions, events, searches and commerce records."""

    event_end = pd.Timestamp(config["timeline"]["event_end"], tz="UTC") + pd.Timedelta(days=1)
    problem_start = pd.Timestamp(config["timeline"]["problem_start"], tz="UTC")
    experiment_start = pd.Timestamp(config["timeline"]["experiment_start"], tz="UTC")
    threshold = float(config["commerce"]["free_delivery_threshold"])
    min_order = float(config["commerce"]["minimum_order_value"])

    latent = private.set_index("user_id").to_dict("index")
    user_info = users.set_index("user_id").to_dict("index")
    variant_map = assignments.set_index("user_id")["variant"].to_dict()
    assignment_row = assignments.set_index("user_id")["assignment_id"].to_dict()

    city_stores = stores.groupby("city")["store_id"].apply(list).to_dict()
    active_products = products[products["is_active"]].copy()
    all_product_ids = active_products["product_id"].to_numpy()
    product_rows = active_products.set_index("product_id").to_dict("index")
    category_products = {
        category: frame["product_id"].to_numpy()
        for category, frame in active_products.groupby("category")
    }

    # Generate session shells first, then process them chronologically.
    session_rows: list[dict[str, Any]] = []
    session_id = 1
    for user in users.itertuples(index=False):
        l = latent[user.user_id]
        available_days = max(0, (event_end - user.first_seen_at).days)
        offsets = [0]
        # Explicit retention anchors produce a realistic declining D1/D7/D14/D30 curve.
        for retention_day, base_probability in [(1, 0.18), (7, 0.12), (14, 0.085), (30, 0.055)]:
            probability = _clip(
                base_probability
                + 0.12 * l["need_frequency"]
                + 0.035 * l["purchase_intent"],
                0,
                0.65,
            )
            if retention_day <= available_days and rng.random() < probability:
                offsets.append(retention_day)
        if available_days > 0:
            random_count = int(min(6, rng.poisson(0.35 + 1.25 * l["need_frequency"])))
            if random_count:
                scale = 30 + 55 * (1 - l["need_frequency"])
                extra = np.clip(rng.exponential(scale, random_count).astype(int) + 2, 2, available_days)
                offsets.extend(extra.tolist())
        offsets = sorted(offsets)
        for offset in offsets:
            start = user.first_seen_at + pd.Timedelta(days=int(offset)) + pd.Timedelta(
                seconds=int(rng.integers(0, 20 * 3600 if offset else 1800))
            )
            if start >= event_end:
                continue
            duration = int(np.clip(rng.lognormal(5.4, 0.55), 90, 2400))
            app_version = "5.6.0" if start < problem_start else ("5.7.0" if start < experiment_start else "5.8.0")
            store_id = int(rng.choice(city_stores[user.initial_city])) if user.is_serviceable else None
            session_rows.append(
                {
                    "session_id": session_id,
                    "user_id": user.user_id,
                    "session_started_at": start,
                    "session_ended_at": start + pd.Timedelta(seconds=duration),
                    "platform": user.initial_platform,
                    "app_version": app_version,
                    "device_type": "iPhone" if user.initial_platform == "iOS" else f"Android {user.device_tier}",
                    "network_type": rng.choice(["Wi-Fi", "4G", "5G"], p=[0.36, 0.49, 0.15]),
                    "city": user.initial_city,
                    "store_id": store_id,
                }
            )
            session_id += 1

    sessions = pd.DataFrame(session_rows).sort_values("session_started_at").reset_index(drop=True)

    events: list[dict[str, Any]] = []
    searches: list[dict[str, Any]] = []
    checkouts: list[dict[str, Any]] = []
    payments: list[dict[str, Any]] = []
    orders: list[dict[str, Any]] = []
    order_items: list[dict[str, Any]] = []
    status_history: list[dict[str, Any]] = []
    exposed_at: dict[int, pd.Timestamp] = {}

    counters = defaultdict(int)
    order_count = defaultdict(int)

    def next_id(name: str) -> int:
        counters[name] += 1
        return counters[name]

    def add_event(
        user_id: int,
        session_id: int,
        name: str,
        timestamp: pd.Timestamp,
        *, product_id: int | None = None,
        search_id: int | None = None,
        checkout_id: int | None = None,
        payment_attempt_id: int | None = None,
        order_id: int | None = None,
        store_id: int | None = None,
        screen_name: str | None = None,
        properties: dict[str, Any] | None = None,
    ) -> None:
        events.append(
            {
                "event_id": next_id("event"), "user_id": user_id,
                "session_id": session_id, "event_name": name,
                "event_timestamp": timestamp, "product_id": product_id,
                "search_id": search_id, "checkout_id": checkout_id,
                "payment_attempt_id": payment_attempt_id, "order_id": order_id,
                "store_id": store_id, "screen_name": screen_name,
                "event_properties": json.dumps(properties or {}, separators=(",", ":")),
            }
        )

    for s in sessions.itertuples(index=False):
        u = user_info[s.user_id]
        l = latent[s.user_id]
        t = s.session_started_at
        step = pd.Timedelta(seconds=8)
        returning = order_count[s.user_id] > 0
        add_event(s.user_id, s.session_id, "app_open", t, store_id=s.store_id, screen_name="launch")
        t += step
        add_event(s.user_id, s.session_id, "home_view", t, store_id=s.store_id, screen_name="home")

        if not u["is_serviceable"]:
            add_event(s.user_id, s.session_id, "serviceability_checked", t + step,
                      screen_name="location", properties={"serviceable": False})
            continue
        if pd.isna(u["signup_completed_at"]):
            if rng.random() < 0.65:
                add_event(s.user_id, s.session_id, "signup_started", t + step, screen_name="signup")
            continue

        discovery_p = _clip(0.62 + 0.25 * l["purchase_intent"] + 0.04 * returning)
        if rng.random() >= discovery_p:
            continue
        t += step

        preferred = l["preferred_category"]
        product_pool = category_products.get(preferred, all_product_ids) if rng.random() < 0.62 else all_product_ids
        product_id = int(rng.choice(product_pool))
        product = product_rows[product_id]
        used_search = rng.random() < 0.57
        search_id_value: int | None = None
        if used_search:
            search_id_value = next_id("search")
            zero_results = rng.random() < (0.035 if returning else 0.055)
            result_count = 0 if zero_results else int(rng.integers(4, 45))
            searches.append(
                {
                    "search_id": search_id_value, "user_id": s.user_id,
                    "session_id": s.session_id, "searched_at": t,
                    "search_query": str(product["subcategory"]).lower(),
                    "result_count": result_count,
                    "response_time_ms": int(np.clip(rng.normal(520, 170), 80, 1800)),
                }
            )
            add_event(s.user_id, s.session_id, "search_submitted", t,
                      search_id=search_id_value, store_id=s.store_id, screen_name="search")
            add_event(s.user_id, s.session_id, "search_results_viewed", t + step,
                      search_id=search_id_value, store_id=s.store_id, screen_name="search_results",
                      properties={"result_count": result_count})
            if zero_results:
                add_event(s.user_id, s.session_id, "zero_results_seen", t + 2 * step,
                          search_id=search_id_value, store_id=s.store_id, screen_name="search_results")
                continue
        else:
            add_event(s.user_id, s.session_id, "category_viewed", t,
                      store_id=s.store_id, screen_name="category",
                      properties={"category": product["category"]})

        if rng.random() >= _clip(0.73 + 0.15 * l["purchase_intent"]):
            continue
        t += 2 * step
        add_event(s.user_id, s.session_id, "product_viewed", t, product_id=product_id,
                  search_id=search_id_value, store_id=s.store_id, screen_name="product_detail")

        add_cart_p = _clip(0.22 + 0.40 * l["purchase_intent"] + 0.06 * returning)
        if rng.random() >= add_cart_p:
            continue

        item_n = int(rng.choice([1, 2, 3, 4], p=[0.48, 0.31, 0.15, 0.06]))
        selected_ids = [product_id]
        if item_n > 1:
            selected_ids.extend(rng.choice(all_product_ids, size=item_n - 1, replace=False).astype(int).tolist())
        cart_items: list[dict[str, Any]] = []
        subtotal = 0.0
        for pid in selected_ids:
            p = product_rows[int(pid)]
            qty = int(rng.choice([1, 2], p=[0.87, 0.13]))
            unit_price = float(p["base_selling_price"])
            line_total = unit_price * qty
            subtotal += line_total
            cart_items.append({"product_id": int(pid), "quantity": qty, "unit_price": unit_price, "line_total": line_total})
            t += step
            add_event(s.user_id, s.session_id, "add_to_cart", t, product_id=int(pid),
                      search_id=search_id_value if pid == product_id else None,
                      store_id=s.store_id, screen_name="product_detail",
                      properties={"quantity": qty, "unit_price": unit_price})
        add_event(s.user_id, s.session_id, "cart_viewed", t + step, store_id=s.store_id,
                  screen_name="cart", properties={"subtotal": round(subtotal, 2), "item_count": item_n})

        variant = variant_map.get(s.user_id)
        exposed = variant is not None and subtotal < float(config["experiment"]["eligible_cart_maximum"])
        if exposed and s.user_id not in exposed_at:
            exposed_at[s.user_id] = t + step
            add_event(s.user_id, s.session_id, "experiment_exposure", t + step,
                      store_id=s.store_id, screen_name="cart",
                      properties={"experiment_id": config["experiment"]["id"], "variant": variant})

        checkout_p = _clip(0.50 + 0.23 * l["purchase_intent"] + 0.06 * returning)
        if exposed and variant == "treatment" and t >= experiment_start:
            checkout_p -= 0.035 * l["price_sensitivity"]
        if rng.random() >= checkout_p:
            continue

        checkout_id = next_id("checkout")
        checkout_started = t + 2 * step
        post_problem = checkout_started >= problem_start
        handling_fee = float(config["commerce"]["revised_handling_fee"] if post_problem else config["commerce"]["baseline_handling_fee"])
        if subtotal >= threshold:
            handling_fee = 0.0
        delivery_fee = 25.0 if subtotal < 199 else 0.0
        discount = 30.0 if (not returning and subtotal >= 199 and rng.random() < 0.55 * l["discount_affinity"]) else 0.0
        total = round(max(0.0, subtotal + delivery_fee + handling_fee - discount), 2)
        eta = int(np.clip(rng.normal(23, 6), 10, 45))
        add_event(s.user_id, s.session_id, "checkout_started", checkout_started,
                  checkout_id=checkout_id, store_id=s.store_id, screen_name="checkout")
        add_event(s.user_id, s.session_id, "fee_breakdown_viewed", checkout_started + step,
                  checkout_id=checkout_id, store_id=s.store_id, screen_name="checkout",
                  properties={"handling_fee": handling_fee, "delivery_fee": delivery_fee, "total": total})

        pay_attempt_p = 0.94
        if post_problem and subtotal < threshold:
            relative_fee = (handling_fee + delivery_fee) / max(subtotal, min_order)
            penalty = 0.42 * l["price_sensitivity"] * min(relative_fee, 0.45)
            if not returning:
                penalty += 0.055
            if exposed and variant == "treatment":
                penalty *= 0.55
            pay_attempt_p -= penalty
        payment_attempted = subtotal >= min_order and rng.random() < _clip(pay_attempt_p)

        payment_success = False
        attempt_rows: list[dict[str, Any]] = []
        payment_method = None
        end_time = checkout_started + 3 * step
        if payment_attempted:
            methods = ["UPI", "card", "wallet", "netbanking"]
            method_probs = [0.60, 0.20, 0.12, 0.08]
            max_attempts = 2
            for attempt_no in range(1, max_attempts + 1):
                payment_method = str(rng.choice(methods, p=method_probs))
                attempt_id = next_id("payment")
                attempted_at = checkout_started + pd.Timedelta(seconds=35 * attempt_no)
                method_shift = {"UPI": -0.025, "card": 0.015, "wallet": 0.025, "netbanking": -0.06}[payment_method]
                success_p = _clip(l["payment_reliability"] + method_shift)
                success = rng.random() < success_p
                failure_code = None if success else str(rng.choice(["BANK_DECLINE", "TIMEOUT", "AUTH_FAILED", "NETWORK_ERROR"]))
                payment_row = {
                    "payment_attempt_id": attempt_id, "checkout_id": checkout_id,
                    "attempt_number": attempt_no, "attempted_at": attempted_at,
                    "payment_method": payment_method,
                    "payment_provider": str(rng.choice(["RazorFlow", "PayBridge", "SwiftPay"])),
                    "payment_status": "success" if success else "failed",
                    "failure_code": failure_code,
                    "failure_reason": None if success else failure_code.replace("_", " ").title(),
                    "amount": total,
                    "processing_time_ms": int(np.clip(rng.normal(1300 if success else 2400, 650), 150, 6500)),
                }
                payments.append(payment_row)
                attempt_rows.append(payment_row)
                add_event(s.user_id, s.session_id, "payment_attempted", attempted_at,
                          checkout_id=checkout_id, payment_attempt_id=attempt_id,
                          store_id=s.store_id, screen_name="payment", properties={"method": payment_method})
                add_event(s.user_id, s.session_id, "payment_succeeded" if success else "payment_failed",
                          attempted_at + pd.Timedelta(seconds=3), checkout_id=checkout_id,
                          payment_attempt_id=attempt_id, store_id=s.store_id, screen_name="payment",
                          properties={} if success else {"failure_code": failure_code})
                end_time = attempted_at + pd.Timedelta(seconds=4)
                if success:
                    payment_success = True
                    break
                retry_p = _clip(0.28 + 0.30 * l["purchase_intent"])
                if attempt_no == max_attempts or rng.random() >= retry_p:
                    break

        if not payment_attempted:
            outcome, abandonment_stage = "abandoned", "fee_review"
        elif not payment_success:
            outcome, abandonment_stage = "payment_failed", None
        else:
            outcome, abandonment_stage = "order_created", None

        checkouts.append(
            {
                "checkout_id": checkout_id, "user_id": s.user_id,
                "session_id": s.session_id, "store_id": s.store_id,
                "checkout_started_at": checkout_started,
                "checkout_ended_at": end_time,
                "item_count": sum(x["quantity"] for x in cart_items),
                "subtotal": round(subtotal, 2), "delivery_fee": delivery_fee,
                "handling_fee": handling_fee, "discount_amount": discount,
                "total_payable": total, "estimated_delivery_minutes": eta,
                "checkout_outcome": outcome, "abandonment_stage": abandonment_stage,
            }
        )
        if not payment_success:
            continue

        order_id = next_id("order")
        placed_at = end_time + pd.Timedelta(seconds=2)
        add_event(s.user_id, s.session_id, "order_placed", placed_at,
                  checkout_id=checkout_id, order_id=order_id, store_id=s.store_id,
                  screen_name="order_confirmation", properties={"order_value": total})
        order_count[s.user_id] += 1

        fulfillment_draw = rng.random()
        if fulfillment_draw < 0.935:
            final_status = "delivered"
        elif fulfillment_draw < 0.958:
            final_status = "cancelled_by_user"
        elif fulfillment_draw < 0.982:
            final_status = "cancelled_by_store"
        else:
            final_status = "delivery_failed"
        confirmed_at = placed_at + pd.Timedelta(minutes=int(rng.integers(1, 4)))
        delivered_at = None
        cancelled_at = None
        cancellation_actor = None
        cancellation_reason = None
        if final_status == "delivered":
            delivered_at = placed_at + pd.Timedelta(minutes=int(np.clip(rng.normal(eta, 6), 10, 70)))
        elif final_status.startswith("cancelled"):
            cancelled_at = placed_at + pd.Timedelta(minutes=int(rng.integers(2, 12)))
            cancellation_actor = "user" if final_status == "cancelled_by_user" else "store"
            cancellation_reason = str(rng.choice(["changed_mind", "item_unavailable", "address_issue", "capacity_constraint"]))

        refund_amount = 0.0
        refund_status = "none"
        if final_status == "delivered" and rng.random() < 0.032:
            if rng.random() < 0.30:
                refund_status, refund_amount = "full", total
            else:
                refund_status = "partial"
                refund_amount = round(total * float(rng.uniform(0.10, 0.45)), 2)
        fulfillment_cost = round(float(np.clip(rng.normal(43, 7), 25, 70)), 2)
        processing_cost = round(total * (0.006 if payment_method == "UPI" else 0.012), 2)
        orders.append(
            {
                "order_id": order_id, "checkout_id": checkout_id, "user_id": s.user_id,
                "store_id": s.store_id, "order_placed_at": placed_at,
                "confirmed_at": confirmed_at, "delivered_at": delivered_at,
                "cancelled_at": cancelled_at, "final_status": final_status,
                "item_count": sum(x["quantity"] for x in cart_items),
                "subtotal": round(subtotal, 2), "delivery_fee": delivery_fee,
                "handling_fee": handling_fee, "discount_amount": discount,
                "order_value": total, "refund_amount": refund_amount,
                "refund_status": refund_status, "fulfillment_cost": fulfillment_cost,
                "payment_processing_cost": processing_cost,
                "cancellation_actor": cancellation_actor,
                "cancellation_reason": cancellation_reason,
            }
        )
        for item in cart_items:
            item_discount = 0.0
            unit_cost = round(item["unit_price"] * float(rng.uniform(0.58, 0.78)), 2)
            order_items.append(
                {
                    "order_item_id": next_id("order_item"), "order_id": order_id,
                    "product_id": item["product_id"], "quantity": item["quantity"],
                    "unit_price": item["unit_price"], "unit_cost": unit_cost,
                    "item_discount": item_discount, "item_total": item["line_total"],
                    "was_substituted": bool(rng.random() < 0.025),
                    "was_available_at_checkout": True,
                }
            )
        status_steps = [("placed", placed_at), ("confirmed", confirmed_at)]
        if final_status == "delivered":
            status_steps += [
                ("packed", confirmed_at + pd.Timedelta(minutes=5)),
                ("out_for_delivery", confirmed_at + pd.Timedelta(minutes=10)),
                ("delivered", delivered_at),
            ]
        else:
            status_steps.append(("cancelled", cancelled_at or confirmed_at + pd.Timedelta(minutes=15)))
        for status, stamp in status_steps:
            status_history.append(
                {"status_event_id": next_id("status"), "order_id": order_id,
                 "order_status": status, "status_timestamp": stamp, "reason_code": cancellation_reason if status == "cancelled" else None}
            )

    assignments = assignments.copy()
    assignments["first_exposed_at"] = assignments["user_id"].map(exposed_at)

    frames = {
        "sessions": sessions,
        "events": pd.DataFrame(events),
        "searches": pd.DataFrame(searches),
        "checkout_attempts": pd.DataFrame(checkouts),
        "payment_attempts": pd.DataFrame(payments),
        "orders": pd.DataFrame(orders),
        "order_items": pd.DataFrame(order_items),
        "order_status_history": pd.DataFrame(status_history),
        "experiment_assignments": assignments,
    }
    return frames
