"""Load and validate locally supplied external demand profiles."""

from pathlib import Path

import pandas as pd

METHOD_NAME = "external_profile"

EXPECTED_COLUMNS = {
    "timestamp",
    "demand",
}


def read_external_profile(
    path: str | Path,
) -> pd.Series:
    """Read a timestamped external demand series from CSV."""
    profile = pd.read_csv(path)

    if set(profile.columns) != EXPECTED_COLUMNS:
        raise ValueError(
            "External profile must contain exactly the columns "
            "'timestamp' and 'demand'."
        )

    timestamps = pd.to_datetime(
        profile["timestamp"],
        utc=True,
        errors="raise",
    )

    if timestamps.duplicated().any():
        raise ValueError(
            "External profile timestamps must be unique."
        )

    if (
        (timestamps.dt.minute != 0).any()
        or (timestamps.dt.second != 0).any()
        or (timestamps.dt.microsecond != 0).any()
    ):
        raise ValueError(
            "External profile timestamps must be aligned "
            "to whole hours."
        )

    values = pd.to_numeric(
        profile["value"],
        errors="raise",
    )

    if values.isna().any():
        raise ValueError(
            "External profile demand values must not be missing."
        )

    result = pd.Series(
        values.to_numpy(),
        index=pd.DatetimeIndex(timestamps),
        dtype=float,
    )

    return result.sort_index()
