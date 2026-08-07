"""Compile auxiliary-data requirements for advanced gap filling."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd
from _time import as_utc_timestamp

from cleaning.advanced.construct_from_sources import METHOD_NAME

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

