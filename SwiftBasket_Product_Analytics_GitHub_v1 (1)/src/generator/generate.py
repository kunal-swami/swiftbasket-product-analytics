from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.generator.config_loader import load_config
from src.generator.dimensions import (
    OUTPUT_COLUMNS,
    generate_products,
    generate_stores,
    validate_dimensions,
)
from src.generator.experiments import assign_experiment
from src.generator.journeys import generate_activity
from src.generator.users import generate_users
from src.generator.validation import validate_generated_data


def _save_frame(frame: pd.DataFrame, path_without_suffix: Path) -> str:
    frame.to_csv(path_without_suffix.with_suffix(".csv"), index=False)
    try:
        frame.to_parquet(path_without_suffix.with_suffix(".parquet"), index=False)
        return ".csv + .parquet"
    except ImportError:
        return ".csv"


def run_generation(
    config_path: str | Path = "config/generation_config.yaml",
    output_root: str | Path = "data",
) -> dict[str, pd.DataFrame]:
    config = load_config(config_path)
    seed = int(config["project"]["random_seed"])
    seed_sequence = np.random.SeedSequence(seed)
    dim_rng, user_rng, experiment_rng, journey_rng = [
        np.random.default_rng(child) for child in seed_sequence.spawn(4)
    ]

    stores = generate_stores(config, dim_rng)
    products_full = generate_products(config, dim_rng)
    validate_dimensions(stores, products_full, config)
    products = products_full[OUTPUT_COLUMNS].copy()

    users, private = generate_users(config, user_rng)
    assignments = assign_experiment(users, config, experiment_rng)
    activity = generate_activity(
        users, private, stores, products, assignments, config, journey_rng
    )
    frames: dict[str, pd.DataFrame] = {
        "users": users,
        "stores": stores,
        "products": products,
        **activity,
    }
    validation_summary = validate_generated_data(frames, config)

    output_root = Path(output_root)
    generated = output_root / "generated"
    samples = output_root / "samples"
    generated.mkdir(parents=True, exist_ok=True)
    samples.mkdir(parents=True, exist_ok=True)

    formats: dict[str, str] = {}
    for name, frame in frames.items():
        formats[name] = _save_frame(frame, generated / name)
        frame.head(100).to_csv(samples / f"{name}_sample.csv", index=False)

    summary = {**validation_summary, "seed": seed, "formats": formats}
    (output_root / "generation_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return frames


if __name__ == "__main__":
    run_generation()
