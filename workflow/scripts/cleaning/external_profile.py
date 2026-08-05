"""A gap-filling method using an aligned external profile."""

import pandas as pd

METHOD_NAME = "external_profile"


def apply_external_profile(
    load: pd.DataFrame,
    *,
    profile: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fill remaining missing cells from an aligned external profile."""
    if not profile.index.equals(load.index):
        raise ValueError(
            "External profile must use the same index as load."
        )

    if not profile.columns.equals(load.columns):
        raise ValueError(
            "External profile must use the same columns as load."
        )

    eligible = load.isna() & profile.notna()

    filled = load.mask(
        eligible,
        profile,
    )

    newly_filled = (
        load.isna()
        & filled.notna()
    )

    return filled, newly_filled