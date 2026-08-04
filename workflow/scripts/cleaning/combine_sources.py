"""Combine prepared demand sources in priority order."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd


def combine_sources(
    sources: Mapping[str, pd.DataFrame],
    *,
    priority: Sequence[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Combine sources and record which source supplied each value."""
    if not priority:
        raise ValueError(
            "At least one demand source must be configured."
        )

    missing_sources = [
        source
        for source in priority
        if source not in sources
    ]

    if missing_sources:
        raise ValueError(
            "Configured demand sources were not supplied: "
            f"{missing_sources}"
        )

    selected = {
        source: sources[source]
        for source in priority
    }

    _validate_source_alignment(selected)

    first_source = priority[0]
    combined = selected[first_source].copy()

    data_source = pd.DataFrame(
        pd.NA,
        index=combined.index,
        columns=combined.columns,
        dtype="string",
    )

    data_source = data_source.mask(
        combined.notna(),
        first_source,
    )

    for source_name in priority[1:]:
        candidate = selected[source_name]

        newly_supplied = (
            combined.isna()
            & candidate.notna()
        )

        combined = combined.combine_first(candidate)

        data_source = data_source.mask(
            newly_supplied,
            source_name,
        )

    return combined, data_source


def _validate_source_alignment(
    sources: Mapping[str, pd.DataFrame],
) -> None:
    """Require all prepared sources to use the same target grid."""
    source_items = list(sources.items())

    reference_name, reference = source_items[0]

    for source_name, source in source_items[1:]:
        if not source.index.equals(reference.index):
            raise ValueError(
                f"Demand source {source_name!r} does not use the "
                f"same time index as {reference_name!r}."
            )

        if not source.columns.equals(reference.columns):
            raise ValueError(
                f"Demand source {source_name!r} does not use the "
                f"same country columns as {reference_name!r}."
            )
