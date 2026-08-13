"""A gap-filling method: average corresponding values from other periods."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

METHOD_NAME = "average_periods"


def apply_average_periods(
    load: pd.DataFrame,
    *,
    max_gap: str | pd.Timedelta,
    source_offsets: Sequence[str | pd.Timedelta],
    original_gap_duration: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fill missing runs using the mean of complete source periods.

    For a target timestamp ``t``, source values are taken from
    ``t + source_offset`` for each configured offset.

    For example, offsets ``-7D`` and ``7D`` average the same hour
    from the previous and following weeks.

    A gap is filled only when:

    - it was missing in the original data;
    - its original duration does not exceed ``max_gap``;
    - every configured source period is complete for the whole gap.
    """
    max_gap = pd.Timedelta(max_gap)

    offsets = tuple(pd.Timedelta(offset) for offset in source_offsets)

    if max_gap <= pd.Timedelta(0):
        raise ValueError("'max_gap' must be greater than zero.")

    if len(offsets) < 2:
        raise ValueError("'source_offsets' must contain at least two offsets.")

    if len(set(offsets)) != len(offsets):
        raise ValueError("'source_offsets' must not contain duplicates.")

    if pd.Timedelta(0) in offsets:
        raise ValueError("'source_offsets' must not contain zero.")

    eligible = (
        load.isna()
        & original_gap_duration.gt(pd.Timedelta(0))
        & original_gap_duration.le(max_gap)
    )

    sources = [_values_at_offset(load, source_offset=offset) for offset in offsets]

    candidate = _mean_complete_sources(sources=sources)

    eligible &= candidate.notna()

    filled = load.mask(eligible, candidate)

    newly_filled = load.isna() & filled.notna()

    return filled, newly_filled


def _values_at_offset(
    load: pd.DataFrame, *, source_offset: pd.Timedelta
) -> pd.DataFrame:
    """Align values at timestamp + offset to target timestamps."""
    source_timestamps = load.index + source_offset

    source = load.reindex(source_timestamps)

    source.index = load.index

    return source


def _mean_complete_sources(*, sources: Sequence[pd.DataFrame]) -> pd.DataFrame:
    """Calculate the mean only where every source is available."""
    source_sum = sources[0].copy()
    complete = sources[0].notna()

    for source in sources[1:]:
        source_sum = source_sum + source
        complete &= source.notna()

    candidate = source_sum / len(sources)

    return candidate.where(complete)
