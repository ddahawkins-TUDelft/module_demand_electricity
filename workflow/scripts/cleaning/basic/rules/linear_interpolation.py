"""A gap filling method: linear interpolation."""

from __future__ import annotations

import pandas as pd

METHOD_NAME = "linear_interpolation"


def apply_linear_interpolation(
    load: pd.DataFrame,
    *,
    max_gap: str | pd.Timedelta,
    original_gap_duration: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fill bounded missing runs using linear interpolation.

    Only complete original gaps whose duration is less than or equal to
    ``max_gap`` are eligible.

    Returns:
    -------
    filled:
        Load dataframe after applying this rule.
    newly_filled:
        Boolean dataframe identifying values filled by this rule.
    """
    max_gap = pd.Timedelta(max_gap)

    eligible = (
        load.isna()
        & original_gap_duration.gt(pd.Timedelta(0))
        & original_gap_duration.le(max_gap)
    )

    interpolated = load.interpolate(method="time", limit_area="inside")

    filled = load.mask(eligible, interpolated)
    newly_filled = load.isna() & filled.notna()

    return filled, newly_filled
