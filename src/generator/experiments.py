from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def assign_experiment(
    users: pd.DataFrame,
    config: dict[str, Any],
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Randomize eligible July-acquired users before exposure."""

    experiment = config["experiment"]
    start = pd.Timestamp(config["timeline"]["experiment_start"], tz="UTC")
    end = pd.Timestamp(config["timeline"]["experiment_end"], tz="UTC") + pd.Timedelta(days=1)
    eligible = users[
        (users["first_seen_at"] >= start)
        & (users["first_seen_at"] < end)
        & users["is_serviceable"]
        & users["signup_completed_at"].notna()
    ].copy()

    variants = list(experiment["allocation"])
    eligible["variant"] = rng.choice(
        variants,
        size=len(eligible),
        p=list(experiment["allocation"].values()),
    )
    eligible["assignment_id"] = np.arange(1, len(eligible) + 1, dtype=np.int64)
    eligible["experiment_id"] = experiment["id"]
    eligible["assigned_at"] = eligible["first_seen_at"]
    eligible["first_exposed_at"] = pd.NaT
    eligible["eligibility_reason"] = "new_serviceable_user"
    return eligible[
        [
            "assignment_id", "experiment_id", "user_id", "variant",
            "assigned_at", "first_exposed_at", "eligibility_reason",
        ]
    ].reset_index(drop=True)
