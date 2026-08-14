"""A gap filling method: copy period."""

from __future__ import annotations

import pandas as pd

METHOD_NAME = "copy_period"


def apply_copy_period(
    load: pd.DataFrame,
    *,
    max_gap: str | pd.Timedelta,
    source_offset: str | pd.Timedelta,
    original_gap_duration: pd.DataFrame,
    require_complete_source: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fill eligible missing runs from another period in the same time series.

    For a target timestamp ``t``, the source value is taken from
    ``t + source_offset``. A negative offset therefore copies from an
    earlier period.

    Only original missing runs no longer than ``max_gap`` are eligible.
    """
    max_gap = pd.Timedelta(max_gap)
    source_offset = pd.Timedelta(source_offset)

    eligible = (
        load.isna()
        & original_gap_duration.gt(pd.Timedelta(0))
        & original_gap_duration.le(max_gap)
    )

    source = _values_at_offset(load, source_offset=source_offset)

    if require_complete_source:
        eligible = _require_complete_source_for_each_gap(
            eligible=eligible, source=source
        )
    else:
        eligible &= source.notna()

    filled = load.mask(eligible, source)
    newly_filled = load.isna() & filled.notna()

    return filled, newly_filled


def _values_at_offset(
    load: pd.DataFrame, *, source_offset: pd.Timedelta
) -> pd.DataFrame:
    """Align values at ``timestamp + source_offset`` to each target timestamp."""
    source_timestamps = load.index + source_offset

    source = load.reindex(source_timestamps)
    source.index = load.index

    return source


def _require_complete_source_for_each_gap(
    *, eligible: pd.DataFrame, source: pd.DataFrame
) -> pd.DataFrame:
    """Keep a gap eligible only when every source value for that gap exists."""
    result = pd.DataFrame(False, index=eligible.index, columns=eligible.columns)

    for column in eligible.columns:
        eligible_column = eligible[column]
        gap_ids = eligible_column.ne(eligible_column.shift(fill_value=False)).cumsum()

        for _, gap_mask in eligible_column.groupby(gap_ids):
            gap_index = gap_mask.index[gap_mask]

            if gap_index.empty:
                continue

            if source.loc[gap_index, column].notna().all():
                result.loc[gap_index, column] = True

    return result
