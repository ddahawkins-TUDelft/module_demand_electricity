"""Shared time-index utilities."""

from __future__ import annotations

import pandas as pd


def as_utc_timestamp(value: object) -> pd.Timestamp:
    """Convert a timestamp-like value to UTC."""
    timestamp = pd.Timestamp(value)

    if timestamp.tzinfo is None:
        return timestamp.tz_localize("UTC")

    return timestamp.tz_convert("UTC")


def build_hourly_index(
    *,
    start: object,
    end: object,
) -> pd.DatetimeIndex:
    """Create an end-exclusive hourly UTC index."""
    start_timestamp = as_utc_timestamp(start)
    end_timestamp = as_utc_timestamp(end)

    if end_timestamp <= start_timestamp:
        raise ValueError(
            "The temporal end must be later than its start."
        )

    return pd.date_range(
        start=start_timestamp,
        end=end_timestamp,
        freq="h",
        inclusive="left",
        name="time",
    )

def years_in_period(
    *,
    start: object,
    end: object,
) -> tuple[int, ...]:
    """Return calendar years intersecting an end-exclusive period."""
    start_timestamp = as_utc_timestamp(start)
    end_timestamp = as_utc_timestamp(end)

    if end_timestamp <= start_timestamp:
        raise ValueError(
            "The period end must be later than its start."
        )

    final_included_time = (
        end_timestamp - pd.Timedelta(microseconds=1)
    )

    return tuple(
        range(
            start_timestamp.year,
            final_included_time.year + 1,
        )
    )