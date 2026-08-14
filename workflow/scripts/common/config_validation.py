"""Validate semantic relationships in module configuration."""

from collections.abc import Mapping
from typing import Any

import pandas as pd


def validate_config_semantics(config: Mapping[str, Any]) -> None:
    """Validate configuration constraints not covered by the JSON schema."""
    _validate_temporal_scope(config["temporal_scope"])
    advanced = config["gap_filling"]["advanced"]
    _validate_advanced_overrides(advanced["overrides"])
    _validate_cleaning_method_names(config)


def _validate_temporal_scope(scope: Mapping[str, Any]) -> None:
    _validate_period(scope["start"], scope["end"], context="Temporal scope")


def _validate_advanced_overrides(overrides: Mapping[str, Mapping[str, Any]]) -> None:
    for rule_name, rule in overrides.items():
        _validate_period(
            rule["start"], rule["end"], context=f"Advanced-fill rule {rule_name!r}"
        )

        if rule["method"] != "construct_from_sources":
            continue

        for position, source in enumerate(rule["sources"]):
            _validate_period(
                source["start"],
                source["end"],
                context=f"Source {position} in advanced-fill rule {rule_name!r}",
            )

        scaling = rule.get("scaling")
        if scaling is None:
            continue

        for position, source in enumerate(scaling["target_sources"]):
            _validate_period(
                source["start"],
                source["end"],
                context=(
                    f"Scaling target source {position} "
                    f"in advanced-fill rule {rule_name!r}"
                ),
            )


def _validate_period(start: object, end: object, *, context: str) -> None:
    start_timestamp = pd.Timestamp(start)
    end_timestamp = pd.Timestamp(end)

    if end_timestamp <= start_timestamp:
        raise ValueError(
            f"{context} must have an end timestamp after its start timestamp."
        )


def _validate_cleaning_method_names(config: Mapping[str, Any]) -> None:
    """Reject configured rule names reserved for cleaning provenance."""
    source_names = config["load_sources"]
    basic_rules = config["gap_filling"]["basic"]["rules"]
    advanced_overrides = config["gap_filling"]["advanced"]["overrides"]

    reserved_names = {
        "missing",
        *(f"observed_{source_name}" for source_name in source_names),
    }

    rule_names = [*(rule["name"] for rule in basic_rules), *advanced_overrides.keys()]

    collisions = sorted(set(rule_names) & reserved_names)

    if collisions:
        raise ValueError(
            "Gap-filling rule names conflict with reserved "
            f"cleaning-method names: {collisions}"
        )
