"""Construct an auxiliary demand profile from configured source periods."""

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd
from _time import as_utc_timestamp

METHOD_NAME = "construct_from_sources"

def _align_leap_day(
    auxiliary: pd.Series,
    *,
    start: pd.Timestamp,
    end: pd.Timestamp,
    target_index: pd.DatetimeIndex,
) -> pd.Series:
    """Align source values with target calendar around February 29."""
    source_values = auxiliary.loc[
        (auxiliary.index >= start)
        & (auxiliary.index < end)
    ]

    source_has_leap_day = (
        (source_values.index.month == 2)
        & (source_values.index.day == 29)
    ).any()

    target_has_leap_day = (
        (target_index.month == 2)
        & (target_index.day == 29)
    ).any()

    if source_has_leap_day and not target_has_leap_day:
        leap_day = (
            (source_values.index.month == 2)
            & (source_values.index.day == 29)
        )

        return source_values.loc[~leap_day]

    if target_has_leap_day and not source_has_leap_day:
        feb_28 = auxiliary.loc[
            (auxiliary.index.year == start.year)
            & (auxiliary.index.month == 2)
            & (auxiliary.index.day == 28)
        ]

        march_1 = auxiliary.loc[
            (auxiliary.index.year == start.year)
            & (auxiliary.index.month == 3)
            & (auxiliary.index.day == 1)
        ]

        if len(feb_28) != 24 or len(march_1) != 24:
            raise ValueError(
                "Cannot construct February 29 because complete "
                "February 28 and March 1 source data are required."
            )

        leap_values = (
            feb_28.to_numpy(dtype=float)
            + march_1.to_numpy(dtype=float)
        ) / 2

        insertion_point = (
            source_values.index.month < 3
        ).sum()

        values = source_values.to_numpy(dtype=float)

        aligned = pd.Series(
            data=[
                *values[:insertion_point],
                *leap_values,
                *values[insertion_point:],
            ],
            dtype=float,
        )

        return aligned

    return source_values


def construct_from_sources(
    auxiliary: pd.DataFrame,
    *,
    target_index: pd.DatetimeIndex,
    sources: Sequence[Mapping[str, Any]],
) -> pd.Series:
    """Construct a target demand profile from weighted auxiliary sources."""
    weighted_sources: list[pd.Series] = []
    weights: list[float] = []

    for source in sources:
        country = source["country"]
        start = as_utc_timestamp(
            source["start"]
        )
        end = as_utc_timestamp(
            source["end"]
        )
        weight = float(
            source.get("weight", 1)
        )

        source_values = _align_leap_day(
            auxiliary[country],
            start=start,
            end=end,
            target_index=target_index,
        )

        if len(source_values) != len(target_index):
            raise ValueError(
                "Auxiliary source period must contain "
                "the same number of values as the target "
                f"period. Source {country!r} contains "
                f"{len(source_values)} values; target "
                f"contains {len(target_index)}."
            )

        remapped = pd.Series(
            source_values.to_numpy(),
            index=target_index,
            dtype=float,
        )

        weighted_sources.append(
            remapped * weight
        )
        weights.append(weight)

    if not weighted_sources:
        raise ValueError(
            "At least one auxiliary source is required."
        )

    weighted_sum = sum(
        weighted_sources[1:],
        weighted_sources[0].copy(),
    )

    return weighted_sum / sum(weights)