"""Construct an auxiliary demand profile from configured source periods."""

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd
from _time import as_utc_timestamp

METHOD_NAME = "construct_from_sources"


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

        source_values = auxiliary.loc[
            (auxiliary.index >= start)
            & (auxiliary.index < end),
            country,
        ]

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