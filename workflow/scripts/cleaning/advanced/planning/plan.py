"""Build advanced auxiliary-fill plans."""

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd

LEAVE_MISSING = "leave_missing"


def _as_utc_timestamp(value: object) -> pd.Timestamp:
    """Return a timestamp normalized to UTC."""
    timestamp = pd.Timestamp(value)

    if timestamp.tzinfo is None:
        return timestamp.tz_localize("UTC")

    return timestamp.tz_convert("UTC")


def override_intersects_target_scope(
    rule: Mapping[str, Any],
    *,
    target_countries: Sequence[str],
    target_start: pd.Timestamp,
    target_end: pd.Timestamp,
) -> bool:
    """Return whether an advanced override intersects the model scope."""
    rule_start = _as_utc_timestamp(rule["start"])
    rule_end = _as_utc_timestamp(rule["end"])
    target_start = _as_utc_timestamp(target_start)
    target_end = _as_utc_timestamp(target_end)

    country_intersects = rule["country"] in target_countries
    period_intersects = rule_start < target_end and rule_end > target_start

    return country_intersects and period_intersects


def build_auxiliary_fill_plan(
    rules: Mapping[str, Mapping[str, Any]],
    *,
    target_countries: Sequence[str],
    target_start: pd.Timestamp,
    target_end: pd.Timestamp,
) -> pd.DataFrame:
    """Build the advanced-fill plan for overrides intersecting the model scope."""
    records: list[dict[str, Any]] = []

    for rule_name, rule in rules.items():
        if not override_intersects_target_scope(
            rule,
            target_countries=target_countries,
            target_start=target_start,
            target_end=target_end,
        ):
            continue

        method = rule["method"]
        scaling = rule.get("scaling")

        records.append(
            {
                "rule_name": rule_name,
                "country": rule["country"],
                "target_start": _as_utc_timestamp(rule["start"]),
                "target_end": _as_utc_timestamp(rule["end"]),
                "scope": rule["scope"],
                "method": method,
                "status": ("leave_missing" if method == LEAVE_MISSING else "ready"),
                "source_count": len(rule.get("sources", [])),
                "scaling_method": (scaling["method"] if scaling is not None else None),
            }
        )

    columns = [
        "rule_name",
        "country",
        "target_start",
        "target_end",
        "scope",
        "method",
        "status",
        "source_count",
        "scaling_method",
    ]

    plan = pd.DataFrame.from_records(records, columns=columns)

    if plan.empty:
        return plan

    return plan.sort_values(["country", "target_start", "rule_name"]).reset_index(
        drop=True
    )
