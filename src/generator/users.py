from __future__ import annotations

from datetime import date
from typing import Any

import numpy as np
import pandas as pd


CHANNEL_COST = {
    "organic": 0.0,
    "google_ads": 118.0,
    "meta_ads": 92.0,
    "referral": 55.0,
    "affiliate": 76.0,
}

CHANNEL_INTENT_SHIFT = {
    "organic": 0.12,
    "google_ads": 0.02,
    "meta_ads": -0.13,
    "referral": 0.09,
    "affiliate": -0.03,
}


def _date_choices(start: date, end: date) -> np.ndarray:
    return np.arange(np.datetime64(start), np.datetime64(end) + 1)


def generate_users(
    config: dict[str, Any], rng: np.random.Generator
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate observable users plus a private behavioral frame.

    The private frame contains latent simulation variables and is never exported.
    """

    n = int(config["scale"]["users"])
    timeline = config["timeline"]
    start = date.fromisoformat(timeline["acquisition_start"])
    end = date.fromisoformat(timeline["acquisition_end"])
    problem_start = pd.Timestamp(timeline["problem_start"], tz="UTC")

    days = _date_choices(start, end)
    first_days = rng.choice(days, size=n, replace=True)
    seconds = rng.integers(8 * 3600, 23 * 3600, size=n)
    first_seen = pd.to_datetime(first_days, utc=True) + pd.to_timedelta(seconds, unit="s")

    post_change = first_seen >= problem_start
    baseline_channels = config["baseline_channel_distribution"]
    changed_channels = config["post_change_channel_distribution"]
    channel_names = list(baseline_channels)
    channels = np.empty(n, dtype=object)
    before_count = int((~post_change).sum())
    after_count = int(post_change.sum())
    channels[~post_change] = rng.choice(
        channel_names,
        size=before_count,
        p=[baseline_channels[x] for x in channel_names],
    )
    channels[post_change] = rng.choice(
        channel_names,
        size=after_count,
        p=[changed_channels[x] for x in channel_names],
    )

    platforms = rng.choice(
        list(config["platform_distribution"]),
        size=n,
        p=list(config["platform_distribution"].values()),
    )
    cities = rng.choice(config["cities"], size=n, replace=True)
    device_tier = np.where(
        platforms == "iOS",
        rng.choice(["mid", "high"], size=n, p=[0.25, 0.75]),
        rng.choice(["low", "mid", "high"], size=n, p=[0.36, 0.49, 0.15]),
    )

    base_intent = rng.beta(2.4, 2.8, size=n)
    intent_shift = np.array([CHANNEL_INTENT_SHIFT[x] for x in channels])
    purchase_intent = np.clip(base_intent + intent_shift, 0.02, 0.98)
    price_sensitivity = np.clip(
        rng.beta(2.6, 2.2, size=n)
        + np.where(channels == "meta_ads", 0.10, 0)
        - np.where(channels == "organic", 0.05, 0),
        0.02,
        0.98,
    )
    need_frequency = rng.beta(2.1, 3.1, size=n)
    discount_affinity = rng.beta(2.4, 2.0, size=n)
    payment_reliability = np.clip(rng.normal(0.90, 0.055, size=n), 0.65, 0.99)

    serviceable = rng.random(n) < config["user_attributes"]["serviceable_probability"]
    signup_probability = np.clip(
        config["user_attributes"]["signup_completion_probability"]
        + 0.08 * purchase_intent
        - np.where(~serviceable, 0.75, 0),
        0,
        0.99,
    )
    signup_completed = rng.random(n) < signup_probability
    signup_delay = pd.to_timedelta(rng.integers(30, 900, size=n), unit="s")
    signup_at = pd.Series(first_seen + signup_delay).where(signup_completed, pd.NaT)

    campaign = np.where(
        channels == "organic",
        None,
        np.char.add(np.char.add(channels.astype(str), "_acq_"),
                    rng.integers(1, 5, size=n).astype(str)),
    )
    acquisition_cost = np.array([CHANNEL_COST[x] for x in channels])
    acquisition_cost *= rng.uniform(0.85, 1.15, size=n)

    users = pd.DataFrame(
        {
            "user_id": np.arange(1, n + 1, dtype=np.int64),
            "first_seen_at": first_seen,
            "signup_completed_at": signup_at,
            "acquisition_channel": channels,
            "campaign_name": campaign,
            "initial_city": cities,
            "initial_platform": platforms,
            "device_tier": device_tier,
            "is_serviceable": serviceable,
            "acquisition_cost": np.round(acquisition_cost, 2),
        }
    )

    preferred_categories = rng.choice(
        [
            "Fruits and vegetables", "Dairy and breakfast", "Snacks",
            "Beverages", "Packaged foods", "Household care",
            "Personal care", "Baby care",
        ],
        size=n,
        p=[0.16, 0.16, 0.16, 0.13, 0.18, 0.09, 0.08, 0.04],
    )
    private = pd.DataFrame(
        {
            "user_id": users["user_id"],
            "purchase_intent": purchase_intent,
            "price_sensitivity": price_sensitivity,
            "need_frequency": need_frequency,
            "discount_affinity": discount_affinity,
            "payment_reliability": payment_reliability,
            "preferred_category": preferred_categories,
        }
    )
    return users, private
