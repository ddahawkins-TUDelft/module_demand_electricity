from collections.abc import Mapping, Sequence

import pandas as pd

from cleaning.combine_sources import combine_sources


def combine_auxiliary_sources(
    loads: Mapping[str, pd.DataFrame],
    *,
    priority: Sequence[str],
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    """Combine available auxiliary sources using configured source priority."""
    if not loads:
        empty = pd.DataFrame()
        return empty, empty.copy(), empty.copy()

    unexpected_sources = set(loads) - set(priority)

    if unexpected_sources:
        raise ValueError(
            "Auxiliary sources were supplied but are not configured in "
            f"source priority: {sorted(unexpected_sources)}."
        )

    available_priority = [
        source
        for source in priority
        if source in loads
    ]

    columns = sorted(
        {
            column
            for load in loads.values()
            for column in load.columns
        }
    )

    aligned = {
        source: load.reindex(columns=columns)
        for source, load in loads.items()
    }

    return combine_sources(
        aligned,
        priority=available_priority,
    )
