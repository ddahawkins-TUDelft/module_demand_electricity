"""Cleaning-method provenance and ranking helpers."""

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd


def build_cleaning_method_ranks(
    *, source_priority: Sequence[str], rules: Sequence[Mapping[str, Any]]
) -> dict[str, int]:
    """Build cleaning-method ranks from configured order."""
    ranks: dict[str, int] = {}

    for rank, source_name in enumerate(source_priority):
        ranks[f"observed_{source_name}"] = rank

    first_gap_filling_rank = len(source_priority)

    for rule_position, rule in enumerate(rules):
        ranks[str(rule["name"])] = first_gap_filling_rank + rule_position

    ranks["missing"] = len(source_priority) + len(rules)

    return ranks


def derive_cleaning_method_rank(
    *, cleaning_method: pd.DataFrame, ranks: Mapping[str, int]
) -> pd.DataFrame:
    """Translate cleaning-method names to integer ranks."""
    present_methods = set(cleaning_method.stack().astype(str).unique())

    unknown_methods = sorted(present_methods - set(ranks))

    if unknown_methods:
        raise ValueError(f"No cleaning-method rank is defined for: {unknown_methods}")

    cleaning_method_rank = cleaning_method.replace(ranks)

    return cleaning_method_rank.astype("int16")


def build_final_cleaning_rules(
    gap_filling_config: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Return configured cleaning rules in final provenance order."""
    rules = [dict(rule) for rule in gap_filling_config["basic"]["rules"]]

    if gap_filling_config["mode"] == "advanced":
        rules.extend(
            {"name": rule_name, **override}
            for rule_name, override in (
                gap_filling_config["advanced"]["overrides"].items()
            )
        )

    return rules
