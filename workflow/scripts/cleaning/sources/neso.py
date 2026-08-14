"""Prepare NESO settlement-period data."""

import pandas as pd


def add_utc_timestamps(data: pd.DataFrame) -> pd.DataFrame:
    """Convert NESO settlement dates and periods to UTC timestamps."""
    prepared = data.copy()

    prepared["SETTLEMENT_DATE"] = pd.to_datetime(
        prepared["SETTLEMENT_DATE"], errors="raise"
    ).dt.normalize()

    prepared["SETTLEMENT_PERIOD"] = pd.to_numeric(
        prepared["SETTLEMENT_PERIOD"], errors="raise"
    ).astype(int)

    timestamp_parts: list[pd.Series] = []

    for settlement_date, day in prepared.groupby("SETTLEMENT_DATE", sort=True):
        day = day.sort_values("SETTLEMENT_PERIOD").copy()

        expected_periods = list(range(1, len(day) + 1))
        observed_periods = day["SETTLEMENT_PERIOD"].tolist()

        if observed_periods != expected_periods:
            raise ValueError(
                "NESO settlement periods are not consecutive for "
                f"{settlement_date.date()}. Expected 1-{len(day)}."
            )

        local_start = pd.Timestamp(settlement_date, tz="Europe/London")
        local_end = local_start + pd.DateOffset(days=1)

        expected_index = pd.date_range(
            start=local_start, end=local_end, freq="30min", inclusive="left"
        )

        if len(day) != len(expected_index):
            raise ValueError(
                "NESO settlement-period count does not match the "
                "Europe/London clock for "
                f"{settlement_date.date()}: "
                f"{len(day)} records versus "
                f"{len(expected_index)} expected."
            )

        timestamp_parts.append(
            pd.Series(expected_index, index=day.index, name="timestamp")
        )

    prepared["timestamp"] = pd.concat(timestamp_parts).sort_index()

    prepared["timestamp"] = prepared["timestamp"].dt.tz_convert("UTC")

    return prepared.sort_values("timestamp")
