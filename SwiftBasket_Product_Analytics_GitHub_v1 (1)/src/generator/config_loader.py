from __future__ import annotations

from datetime import date
from math import isclose
from pathlib import Path
from typing import Any

import yaml


class ConfigValidationError(ValueError):
    """Raised when the generation configuration is invalid."""


REQUIRED_SECTIONS = {
    "project",
    "timeline",
    "scale",
    "cities",
    "platform_distribution",
    "baseline_channel_distribution",
    "post_change_channel_distribution",
    "user_attributes",
    "commerce",
    "experiment",
}


def load_config(config_path: str | Path) -> dict[str, Any]:
    """Read, validate and return the generation configuration."""

    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if not isinstance(config, dict):
        raise ConfigValidationError(
            "Configuration must contain a YAML mapping."
        )

    _validate_config(config)
    return config


def _require_keys(
    mapping: dict[str, Any],
    required_keys: set[str],
    section_name: str,
) -> None:
    """Raise an error when required keys are missing."""

    if not isinstance(mapping, dict):
        raise ConfigValidationError(
            f"'{section_name}' must be a mapping, got {type(mapping).__name__}."
        )

    missing = required_keys - mapping.keys()

    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ConfigValidationError(
            f"'{section_name}' is missing required key(s): {missing_list}"
        )


def _validate_distribution(
    distribution: dict[str, Any],
    distribution_name: str,
) -> None:
    """Validate that probabilities are numeric, bounded and total 1."""

    if not isinstance(distribution, dict) or not distribution:
        raise ConfigValidationError(
            f"'{distribution_name}' must be a non-empty mapping."
        )

    for key, value in distribution.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ConfigValidationError(
                f"'{distribution_name}.{key}' must be a number, "
                f"got {type(value).__name__}."
            )

        if not (0 <= value <= 1):
            raise ConfigValidationError(
                f"'{distribution_name}.{key}' must be between 0 and 1, "
                f"got {value}."
            )

    total = sum(distribution.values())

    if not isclose(total, 1.0, abs_tol=1e-9):
        raise ConfigValidationError(
            f"{distribution_name} probabilities must total 1.0; received {total}"
        )


def _parse_date(value: Any, field_name: str) -> date:
    """Convert an ISO-formatted configuration value into a date."""

    if isinstance(value, date):
        return value

    if not isinstance(value, str):
        raise ConfigValidationError(
            f"{field_name} must be an ISO date string."
        )

    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ConfigValidationError(
            f"{field_name} has an invalid date: {value}"
        ) from error


def _validate_timeline(timeline: dict[str, Any]) -> None:
    """Validate chronological relationships between project dates."""

    required_dates = {
        "acquisition_start",
        "acquisition_end",
        "event_end",
        "problem_start",
        "experiment_start",
        "experiment_end",
    }

    _require_keys(timeline, required_dates, "timeline")

    acquisition_start = _parse_date(
        timeline["acquisition_start"], "timeline.acquisition_start"
    )
    acquisition_end = _parse_date(
        timeline["acquisition_end"], "timeline.acquisition_end"
    )
    event_end = _parse_date(timeline["event_end"], "timeline.event_end")
    problem_start = _parse_date(
        timeline["problem_start"], "timeline.problem_start"
    )
    experiment_start = _parse_date(
        timeline["experiment_start"], "timeline.experiment_start"
    )
    experiment_end = _parse_date(
        timeline["experiment_end"], "timeline.experiment_end"
    )

    if not acquisition_start < problem_start:
        raise ConfigValidationError(
            "timeline.acquisition_start must be before timeline.problem_start "
            f"(got {acquisition_start} >= {problem_start})."
        )

    if not problem_start < experiment_start:
        raise ConfigValidationError(
            "timeline.problem_start must be before timeline.experiment_start "
            f"(got {problem_start} >= {experiment_start})."
        )

    if not experiment_start <= experiment_end:
        raise ConfigValidationError(
            "timeline.experiment_start must be on or before "
            f"timeline.experiment_end (got {experiment_start} > {experiment_end})."
        )

    if not experiment_end <= acquisition_end:
        raise ConfigValidationError(
            "timeline.experiment_end must be on or before "
            f"timeline.acquisition_end (got {experiment_end} > {acquisition_end})."
        )

    if not acquisition_end < event_end:
        raise ConfigValidationError(
            "timeline.acquisition_end must be before timeline.event_end "
            f"(got {acquisition_end} >= {event_end})."
        )


def _validate_positive_integer(value: Any, field_name: str) -> None:
    """Validate a positive integer configuration field."""

    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigValidationError(
            f"{field_name} must be a positive integer, got {type(value).__name__}."
        )

    if value <= 0:
        raise ConfigValidationError(
            f"{field_name} must be a positive integer, got {value}."
        )


def _validate_probability(value: Any, field_name: str) -> None:
    """Validate an individual probability between zero and one."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigValidationError(
            f"{field_name} must be a number, got {type(value).__name__}."
        )

    if not (0 <= value <= 1):
        raise ConfigValidationError(
            f"{field_name} must be between 0 and 1, got {value}."
        )


def _validate_config(config: dict[str, Any]) -> None:
    """Run all configuration validation rules."""

    _require_keys(config, REQUIRED_SECTIONS, "root")

    # ---------- 1. Project ----------
    project = config["project"]
    _require_keys(
        project,
        {"name", "synthetic_data", "random_seed", "currency", "timezone"},
        "project",
    )

    if isinstance(project["random_seed"], bool) or not isinstance(
        project["random_seed"], int
    ):
        raise ConfigValidationError("project.random_seed must be an integer.")

    if project["synthetic_data"] is not True:
        raise ConfigValidationError("project.synthetic_data must be true.")

    if project["timezone"] != "UTC":
        raise ConfigValidationError("project.timezone must be 'UTC'.")

    if project["name"] != "swiftbasket":
        raise ConfigValidationError("project.name must be 'swiftbasket'.")

    if project["currency"] != "INR":
        raise ConfigValidationError("project.currency must be 'INR'.")

    if project["name"] != "swiftbasket":
        raise ConfigValidationError("project.name must be 'swiftbasket'.")

    if project["currency"] != "INR":
        raise ConfigValidationError("project.currency must be 'INR'.")

    # ---------- 2. Timeline ----------
    _validate_timeline(config["timeline"])

    # ---------- 3. Scale ----------
    scale = config["scale"]
    _require_keys(scale, {"users", "products", "stores_per_city"}, "scale")

    _validate_positive_integer(scale["users"], "scale.users")
    _validate_positive_integer(scale["products"], "scale.products")
    _validate_positive_integer(
        scale["stores_per_city"], "scale.stores_per_city"
    )

    # ---------- 4. Cities ----------
    cities = config["cities"]

    if not isinstance(cities, list) or not cities:
        raise ConfigValidationError("cities must be a non-empty list.")

    for city in cities:
        if not isinstance(city, str) or not city.strip():
            raise ConfigValidationError(
                f"cities must contain only non-empty strings, got {city!r}."
            )

    if len(cities) != len(set(cities)):
        raise ConfigValidationError("cities must not contain duplicate names.")

    # ---------- 5. Distributions ----------
    _validate_distribution(config["platform_distribution"], "platform_distribution")
    _validate_distribution(
        config["baseline_channel_distribution"], "baseline_channel_distribution"
    )
    _validate_distribution(
        config["post_change_channel_distribution"],
        "post_change_channel_distribution",
    )

    # ---------- 6. User attributes ----------
    user_attributes = config["user_attributes"]
    _require_keys(
        user_attributes,
        {"serviceable_probability", "signup_completion_probability"},
        "user_attributes",
    )

    _validate_probability(
        user_attributes["serviceable_probability"],
        "user_attributes.serviceable_probability",
    )
    _validate_probability(
        user_attributes["signup_completion_probability"],
        "user_attributes.signup_completion_probability",
    )

    # ---------- 7. Commerce ----------
    commerce = config["commerce"]
    _require_keys(
        commerce,
        {
            "baseline_handling_fee",
            "revised_handling_fee",
            "free_delivery_threshold",
            "minimum_order_value",
        },
        "commerce",
    )

    for field_name in (
        "baseline_handling_fee",
        "revised_handling_fee",
        "free_delivery_threshold",
        "minimum_order_value",
    ):
        value = commerce[field_name]

        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ConfigValidationError(
                f"commerce.{field_name} must be a number, "
                f"got {type(value).__name__}."
            )

        if value < 0:
            raise ConfigValidationError(
                f"commerce.{field_name} must be non-negative, got {value}."
            )

    if commerce["revised_handling_fee"] < commerce["baseline_handling_fee"]:
        raise ConfigValidationError(
            "commerce.revised_handling_fee must be greater than or equal to "
            "commerce.baseline_handling_fee."
        )

    if commerce["free_delivery_threshold"] < commerce["minimum_order_value"]:
        raise ConfigValidationError(
            "commerce.free_delivery_threshold must be greater than or equal "
            "to commerce.minimum_order_value."
        )

    # ---------- 8. Experiment ----------
    experiment = config["experiment"]
    _require_keys(
        experiment,
        {"id", "allocation", "eligible_user_type", "eligible_cart_maximum"},
        "experiment",
    )

    if not isinstance(experiment["id"], str) or not experiment["id"].strip():
        raise ConfigValidationError("experiment.id must be a non-empty string.")

    allocation = experiment["allocation"]
    _require_keys(allocation, {"control", "treatment"}, "experiment.allocation")

    if set(allocation.keys()) != {"control", "treatment"}:
        extra = set(allocation.keys()) - {"control", "treatment"}
        raise ConfigValidationError(
            "experiment.allocation must contain exactly 'control' and "
            f"'treatment', found unexpected key(s): {sorted(extra)}"
        )

    _validate_distribution(allocation, "experiment.allocation")

    if (
        not isinstance(experiment["eligible_user_type"], str)
        or not experiment["eligible_user_type"].strip()
    ):
        raise ConfigValidationError(
            "experiment.eligible_user_type must be a non-empty string."
        )

    eligible_cart_maximum = experiment["eligible_cart_maximum"]

    if isinstance(eligible_cart_maximum, bool) or not isinstance(
        eligible_cart_maximum, (int, float)
    ):
        raise ConfigValidationError(
            "experiment.eligible_cart_maximum must be a number."
        )

    if eligible_cart_maximum <= 0:
        raise ConfigValidationError(
            "experiment.eligible_cart_maximum must be positive."
        )
