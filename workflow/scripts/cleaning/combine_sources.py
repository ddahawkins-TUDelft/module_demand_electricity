"""Combine prepared demand sources in priority order."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd


def combine_sources(
    sources: Mapping[str, pd.DataFrame], *, priority: Sequence[str]
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Combine sources and record source and cleaning-method provenance."""
    selected = {source: sources[source] for source in priority}

    _validate_source_alignment(selected)

    first_source = priority[0]
    combined = selected[first_source].copy()

    data_source = pd.DataFrame(
        pd.NA, index=combined.index, columns=combined.columns, dtype="string"
    )

    cleaning_method = pd.DataFrame(
        pd.NA, index=combined.index, columns=combined.columns, dtype="string"
    )

    first_source_values = combined.notna()

    data_source = data_source.mask(first_source_values, first_source)

    cleaning_method = cleaning_method.mask(
        first_source_values, f"observed_{first_source}"
    )

    for source_name in priority[1:]:
        candidate = selected[source_name]

        newly_supplied = combined.isna() & candidate.notna()

        combined = combined.combine_first(candidate)

        data_source = data_source.mask(newly_supplied, source_name)

        cleaning_method = cleaning_method.mask(
            newly_supplied, f"observed_{source_name}"
        )

    return combined, data_source, cleaning_method


def _validate_source_alignment(sources: Mapping[str, pd.DataFrame]) -> None:
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


def combine_auxiliary_sources(
    loads: Mapping[str, pd.DataFrame], *, priority: Sequence[str]
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Combine available auxiliary sources using configured source priority."""
    if not loads:
        empty = pd.DataFrame()
        return empty, empty.copy(), empty.copy()

    available_priority = [source for source in priority if source in loads]

    columns = sorted({column for load in loads.values() for column in load.columns})

    aligned = {source: load.reindex(columns=columns) for source, load in loads.items()}

    return combine_sources(aligned, priority=available_priority)
