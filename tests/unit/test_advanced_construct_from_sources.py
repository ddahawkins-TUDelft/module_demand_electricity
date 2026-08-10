"""Tests for source-based advanced profile construction."""

import pandas as pd
from cleaning.advanced.construct_from_sources import construct_from_sources


def test_construct_from_single_source() -> None:
    auxiliary_index = pd.date_range(
        "2019-01-01",
        periods=3,
        freq="h",
        tz="UTC",
    )

    auxiliary = pd.DataFrame(
        {
            "GRC": [
                10.0,
                20.0,
                30.0,
            ]
        },
        index=auxiliary_index,
    )

    target_index = pd.date_range(
        "2020-01-01",
        periods=3,
        freq="h",
        tz="UTC",
    )

    result = construct_from_sources(
        auxiliary,
        target_index=target_index,
        sources=[
            {
                "country": "GRC",
                "start": "2019-01-01T00:00:00+00:00",
                "end": "2019-01-01T03:00:00+00:00",
                "weight": 1,
            }
        ],
    )

    expected = pd.Series(
        [
            10.0,
            20.0,
            30.0,
        ],
        index=target_index,
        dtype=float,
    )

    pd.testing.assert_series_equal(
        result,
        expected,
    )

def test_construct_from_sources_uses_weighted_mean() -> None:
    auxiliary_index = pd.date_range(
        "2019-01-01",
        periods=3,
        freq="h",
        tz="UTC",
    )

    auxiliary = pd.DataFrame(
        {
            "GRC": [
                10.0,
                20.0,
                30.0,
            ],
            "GBR": [
                30.0,
                40.0,
                50.0,
            ],
        },
        index=auxiliary_index,
    )

    target_index = pd.date_range(
        "2020-01-01",
        periods=3,
        freq="h",
        tz="UTC",
    )

    result = construct_from_sources(
        auxiliary,
        target_index=target_index,
        sources=[
            {
                "country": "GRC",
                "start": "2019-01-01T00:00:00+00:00",
                "end": "2019-01-01T03:00:00+00:00",
                "weight": 1,
            },
            {
                "country": "GBR",
                "start": "2019-01-01T00:00:00+00:00",
                "end": "2019-01-01T03:00:00+00:00",
                "weight": 3,
            },
        ],
    )

    expected = pd.Series(
        [
            25.0,
            35.0,
            45.0,
        ],
        index=target_index,
        dtype=float,
    )

    pd.testing.assert_series_equal(
        result,
        expected,
    )


def test_construct_from_sources_drops_february_29() -> None:
    source_index = pd.date_range(
        "2020-02-01",
        "2020-03-01",
        freq="h",
        inclusive="left",
        tz="UTC",
    )

    values = pd.Series(
        1.0,
        index=source_index,
    )

    values.loc[
        (values.index.month == 2)
        & (values.index.day == 29)
    ] = 999.0

    auxiliary = values.to_frame("GBR")

    target_index = pd.date_range(
        "2021-02-01",
        "2021-03-01",
        freq="h",
        inclusive="left",
        tz="UTC",
    )

    result = construct_from_sources(
        auxiliary,
        target_index=target_index,
        sources=[
            {
                "country": "GBR",
                "start": "2020-02-01",
                "end": "2020-03-01",
            }
        ],
    )

    assert len(result) == 672
    assert not (result == 999.0).any()


def test_construct_from_sources_interpolates_february_29() -> None:
    auxiliary_index = pd.date_range(
        "2021-02-01",
        "2021-03-02",
        freq="h",
        inclusive="left",
        tz="UTC",
    )

    values = pd.Series(
        10.0,
        index=auxiliary_index,
    )

    values.loc[
        (values.index.month == 2)
        & (values.index.day == 28)
    ] = 20.0

    values.loc[
        (values.index.month == 3)
        & (values.index.day == 1)
    ] = 40.0

    auxiliary = values.to_frame("GBR")

    target_index = pd.date_range(
        "2020-02-01",
        "2020-03-01",
        freq="h",
        inclusive="left",
        tz="UTC",
    )

    result = construct_from_sources(
        auxiliary,
        target_index=target_index,
        sources=[
            {
                "country": "GBR",
                "start": "2021-02-01",
                "end": "2021-03-01",
            }
        ],
    )

    target_feb_29 = (
        (result.index.month == 2)
        & (result.index.day == 29)
    )

    assert len(result) == 696
    assert (result.loc[target_feb_29] == 30.0).all()

