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
    """Combine prepared auxiliary sources using configured source priority."""
    if not loads:
        empty = pd.DataFrame()
        return empty, empty.copy(), empty.copy()

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
        priority=priority,
    )
