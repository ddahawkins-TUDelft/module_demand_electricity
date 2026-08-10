"""Compile auxiliary-data requirements for advanced gap filling."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd
from common.time import as_utc_timestamp

from cleaning.advanced.methods.construct_from_sources import METHOD_NAME

REQUIREMENT_COLUMNS = [
    "country",
    "start",
    "end",
]


def compile_auxiliary_requirements(
    overrides: Mapping[str, Mapping[str, Any]],
) -> pd.DataFrame:
    """Compile country-period data required by advanced overrides."""
    requirements: list[dict[str, Any]] = []

    for rule in overrides.values():
        if rule["method"] != METHOD_NAME:
            continue

        requirements.extend(
            _collect_sources(rule["sources"])
        )

        scaling = rule.get("scaling")

        if scaling is not None:
            requirements.extend(
                _collect_sources(
                    scaling["target_sources"]
                )
            )

    if not requirements:
        return pd.DataFrame(
            columns=REQUIREMENT_COLUMNS
        )

    requirements_frame = (
        pd.DataFrame(requirements)
        .drop_duplicates()
        .sort_values(
            ["country", "start", "end"]
        )
        .reset_index(drop=True)
    )

    return _merge_requirements(
        requirements_frame
    )


def _collect_sources(
    sources: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Extract acquisition-relevant fields from source definitions."""
    return [
        {
            "country": source["country"],
            "start": as_utc_timestamp(source["start"]),
            "end": as_utc_timestamp(source["end"]),
        }
        for source in sources
    ]

def _merge_requirements(
    requirements: pd.DataFrame,
) -> pd.DataFrame:
    """Merge overlapping or adjacent country-period requirements."""
    if requirements.empty:
        return requirements.copy()

    merged_rows: list[dict[str, Any]] = []

    for country, country_requirements in requirements.groupby(
        "country",
        sort=True,
    ):
        ordered = country_requirements.sort_values(
            ["start", "end"]
        )

        current_start = ordered.iloc[0]["start"]
        current_end = ordered.iloc[0]["end"]

        for row in ordered.iloc[1:].itertuples(index=False):
            if row.start <= current_end:
                current_end = max(
                    current_end,
                    row.end,
                )
                continue

            merged_rows.append(
                {
                    "country": country,
                    "start": current_start,
                    "end": current_end,
                }
            )

            current_start = row.start
            current_end = row.end

        merged_rows.append(
            {
                "country": country,
                "start": current_start,
                "end": current_end,
            }
        )

    return pd.DataFrame(
        merged_rows,
        columns=REQUIREMENT_COLUMNS,
    )

def get_basic_cleaning_context(
    rules: Sequence[Mapping[str, Any]],
) -> tuple[pd.Timedelta, pd.Timedelta]:
    """Return required left and right context for ordered basic rules."""
    left = pd.Timedelta(0)
    right = pd.Timedelta(0)

    for rule in rules:
        method = rule["method"]
        max_gap = pd.Timedelta(rule["max_gap"])

        # Context is also needed to classify gaps correctly at boundaries.
        rule_left = -max_gap
        rule_right = max_gap

        if method == "linear_interpolation":
            offsets = [
                -pd.Timedelta(hours=1),
                pd.Timedelta(hours=1),
            ]

        elif method == "copy_period":
            offsets = [
                pd.Timedelta(rule["source_offset"]),
            ]

        elif method == "average_periods":
            offsets = [
                pd.Timedelta(offset)
                for offset in rule["source_offsets"]
            ]

        else:
            raise ValueError(
                f"Unsupported basic gap-filling method: {method!r}"
            )

        previous_left = left
        previous_right = right

        for offset in offsets:
            rule_left = min(
                rule_left,
                offset + previous_left,
            )
            rule_right = max(
                rule_right,
                offset + previous_right,
            )

        left = min(
            previous_left,
            rule_left,
        )
        right = max(
            previous_right,
            rule_right,
        )

    return -left, right

def expand_auxiliary_requirements(
    requirements: pd.DataFrame,
    *,
    rules: Sequence[Mapping[str, Any]],
    enabled: bool = True,
) -> pd.DataFrame:
    """Expand auxiliary periods with context needed for basic cleaning."""
    if requirements.empty or not enabled or not rules:
        return requirements.copy()

    left_context, right_context = get_basic_cleaning_context(
        rules
    )

    expanded = requirements.copy()

    expanded["start"] = (
        expanded["start"] - left_context
    )
    expanded["end"] = (
        expanded["end"] + right_context
    )

    return _merge_requirements(expanded)


def build_auxiliary_acquisition_requirements(
    *,
    overrides: Mapping[str, Mapping[str, Any]],
    basic_rules: Sequence[Mapping[str, Any]],
    basic_cleaning_enabled: bool,
) -> pd.DataFrame:
    """Build expanded auxiliary-data requirements for acquisition."""
    exact_requirements = compile_auxiliary_requirements(
        overrides
    )

    return expand_auxiliary_requirements(
        exact_requirements,
        rules=basic_rules,
        enabled=basic_cleaning_enabled,
    )