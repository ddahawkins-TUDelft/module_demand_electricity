"""Cleaning-method provenance and ranking helpers."""

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd


def validate_rule_names(
    *,
    rules: Sequence[Mapping[str, Any]],
    source_priority: Sequence[str],
) -> None:
    """Validate rule-name uniqueness and reserved-name collisions."""
    names = [str(rule["name"]) for rule in rules]

    counts = Counter(names)
    duplicates = sorted(
        name
        for name, count in counts.items()
        if count > 1
    )

    if duplicates:
        raise ValueError(
            "Gap-filling rule names must be unique. "
            f"Duplicate names: {duplicates}"
        )

    reserved_names = {
        "missing",
        *(
            f"observed_{source_name}"
            for source_name in source_priority
        ),
    }

    collisions = sorted(
        set(names) & reserved_names
    )

    if collisions:
        raise ValueError(
            "Gap-filling rule names conflict with reserved "
            f"cleaning-method names: {collisions}"
        )


def build_cleaning_method_ranks(
    *,
    source_priority: Sequence[str],
    rules: Sequence[Mapping[str, Any]],
) -> dict[str, int]:
    """Build cleaning-method ranks from configured order."""
    validate_rule_names(
        rules=rules,
        source_priority=source_priority,
    )

    ranks: dict[str, int] = {}

    for rank, source_name in enumerate(source_priority):
        ranks[f"observed_{source_name}"] = rank

    first_gap_filling_rank = len(source_priority)

    for rule_position, rule in enumerate(rules):
        ranks[str(rule["name"])] = (
            first_gap_filling_rank
            + rule_position
        )

    ranks["missing"] = (
        len(source_priority)
        + len(rules)
    )

    return ranks


def derive_cleaning_method_rank(
    *,
    cleaning_method: pd.DataFrame,
    ranks: Mapping[str, int],
) -> pd.DataFrame:
    """Translate cleaning-method names to integer ranks."""
    present_methods = set(
        cleaning_method.stack().astype(str).unique()
    )

    unknown_methods = sorted(
        present_methods - set(ranks)
    )

    if unknown_methods:
        raise ValueError(
            "No cleaning-method rank is defined for: "
            f"{unknown_methods}"
        )

    cleaning_method_rank = cleaning_method.replace(
        ranks
    )

    return cleaning_method_rank.astype("int16")


def build_final_cleaning_rules(
    gap_filling_config: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Return configured cleaning rules in final provenance order."""
    rules = [
        dict(rule)
        for rule in gap_filling_config["basic"]["rules"]
    ]

    if gap_filling_config["mode"] == "advanced":
        rules.extend(
            {
                "name": rule_name,
                **override,
            }
            for rule_name, override in (
                gap_filling_config["advanced"]["overrides"].items()
            )
        )

    return rules

