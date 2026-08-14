"""Construct an auxiliary demand profile from configured source periods."""

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd
from common.time import as_utc_timestamp

METHOD_NAME = "construct_from_sources"


def _align_leap_day(
    auxiliary: pd.Series,
    *,
    start: pd.Timestamp,
    end: pd.Timestamp,
    target_index: pd.DatetimeIndex,
) -> pd.Series:
    """Align source values with target calendar around February 29."""
    source_values = auxiliary.loc[(auxiliary.index >= start) & (auxiliary.index < end)]

    source_has_leap_day = (
        (source_values.index.month == 2) & (source_values.index.day == 29)
    ).any()

    target_has_leap_day = ((target_index.month == 2) & (target_index.day == 29)).any()

    if source_has_leap_day and not target_has_leap_day:
        leap_day = (source_values.index.month == 2) & (source_values.index.day == 29)

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

        leap_values = (feb_28.to_numpy(dtype=float) + march_1.to_numpy(dtype=float)) / 2

        insertion_point = (source_values.index.month < 3).sum()

        values = source_values.to_numpy(dtype=float)

        aligned = pd.Series(
            data=[*values[:insertion_point], *leap_values, *values[insertion_point:]],
            dtype=float,
        )

        return aligned

    return source_values


def _match_energy(
    profile: pd.Series,
    *,
    auxiliary: pd.DataFrame,
    target_sources: Sequence[Mapping[str, Any]],
) -> pd.Series:
    """Scale a profile to the weighted-mean energy of reference periods."""
    weighted_energy = 0.0
    total_weight = 0.0

    for source in target_sources:
        country = source["country"]
        start = as_utc_timestamp(source["start"])
        end = as_utc_timestamp(source["end"])
        weight = float(source.get("weight", 1))

        source_values = auxiliary.loc[
            (auxiliary.index >= start) & (auxiliary.index < end), country
        ]

        if source_values.empty:
            raise ValueError(
                "Scaling source period contains no values. "
                f"Source {country!r}: {start} to {end}."
            )

        if source_values.isna().any():
            raise ValueError(
                "Scaling source period contains missing values. "
                f"Source {country!r}: {start} to {end}."
            )

        weighted_energy += float(source_values.sum()) * weight
        total_weight += weight

    target_energy = weighted_energy / total_weight
    profile_energy = float(profile.sum())

    if profile_energy == 0:
        raise ValueError(
            "Cannot match energy for a constructed profile with zero total energy."
        )

    return profile * (target_energy / profile_energy)


def _apply_scaling(
    profile: pd.Series, *, auxiliary: pd.DataFrame, scaling: Mapping[str, Any]
) -> pd.Series:
    """Scale a constructed profile to configured reference energy."""
    return _match_energy(
        profile, auxiliary=auxiliary, target_sources=scaling["target_sources"]
    )


def construct_from_sources(
    auxiliary: pd.DataFrame,
    *,
    target_index: pd.DatetimeIndex,
    sources: Sequence[Mapping[str, Any]],
    scaling: Mapping[str, Any] | None = None,
) -> pd.Series:
    """Construct a target demand profile from weighted auxiliary sources."""
    weighted_sources: list[pd.Series] = []
    weights: list[float] = []

    for source in sources:
        country = source["country"]
        start = as_utc_timestamp(source["start"])
        end = as_utc_timestamp(source["end"])
        weight = float(source.get("weight", 1))

        source_values = _align_leap_day(
            auxiliary[country], start=start, end=end, target_index=target_index
        )

        if len(source_values) != len(target_index):
            raise ValueError(
                "Auxiliary source period must contain "
                "the same number of values as the target "
                f"period. Source {country!r} contains "
                f"{len(source_values)} values; target "
                f"contains {len(target_index)}."
            )

        if source_values.isna().any():
            raise ValueError(
                "Auxiliary source period contains missing values. "
                f"Source {country!r}: {start} to {end}."
            )

        remapped = pd.Series(source_values.to_numpy(), index=target_index, dtype=float)

        weighted_sources.append(remapped * weight)
        weights.append(weight)

    weighted_sum = sum(weighted_sources[1:], weighted_sources[0].copy())

    profile = weighted_sum / sum(weights)

    if scaling is not None:
        profile = _apply_scaling(profile, auxiliary=auxiliary, scaling=scaling)

    return profile
