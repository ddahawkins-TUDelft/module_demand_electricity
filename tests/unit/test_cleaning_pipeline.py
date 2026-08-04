"""Tests for the demand-cleaning pipeline."""

from __future__ import annotations

import numpy as np
import pandas as pd

from cleaning.pipeline import clean_demand


def test_clean_demand_records_methods_and_ranks() -> None:
    """Track observed sources, filling rules, and unresolved gaps."""
    index = pd.date_range(
        start="2017-01-01",
        periods=400,
        freq="h",
        tz="UTC",
    )

    primary = pd.DataFrame(
        {
            "AAA": np.arange(
                len(index),
                dtype=float,
            ),
        },
        index=index,
    )

    fallback = pd.DataFrame(
        np.nan,
        index=index,
        columns=["AAA"],
        dtype=float,
    )

    # Four missing values at the start cannot be interpolated because
    # the run exceeds max_gap and cannot be copied from a previous week.
    unresolved_timestamps = index[0:4]
    primary.loc[
        unresolved_timestamps,
        "AAA",
    ] = np.nan

    # One primary-source gap is supplied directly by the fallback source.
    fallback_timestamp = index[200]
    primary.loc[
        fallback_timestamp,
        "AAA",
    ] = np.nan
    fallback.loc[
        fallback_timestamp,
        "AAA",
    ] = 10_000.0

    # A two-hour gap is filled by the first rule.
    interpolation_timestamps = index[220:222]
    primary.loc[
        interpolation_timestamps,
        "AAA",
    ] = np.nan

    # A four-hour gap exceeds the interpolation limit but can be copied
    # from the corresponding values seven days earlier.
    copy_timestamps = index[250:254]
    primary.loc[
        copy_timestamps,
        "AAA",
    ] = np.nan

    sources = {
        "primary": primary,
        "fallback": fallback,
    }

    gap_filling_config = {
        "enabled": True,
        "rules": [
            {
                "name": "interpolate_short_gaps",
                "method": "linear_interpolation",
                "max_gap": "3h",
            },
            {
                "name": "copy_previous_week",
                "method": "copy_period",
                "max_gap": "168h",
                "source_offset": "-168h",
                "require_complete_source": True,
            },
        ],
    }

    (
        cleaned,
        data_source,
        cleaning_method,
        cleaning_method_rank,
    ) = clean_demand(
        sources,
        source_priority=[
            "primary",
            "fallback",
        ],
        gap_filling_config=gap_filling_config,
    )

    # All outputs use the same grid.
    for frame in [
        data_source,
        cleaning_method,
        cleaning_method_rank,
    ]:
        assert frame.index.equals(cleaned.index)
        assert frame.columns.equals(cleaned.columns)

    # Primary observations have rank 0.
    primary_mask = (
        primary.notna()
        & fallback.isna()
    )

    assert (
        data_source.to_numpy()[
            primary_mask.to_numpy()
        ]
        == "primary"
    ).all()

    assert (
        cleaning_method.to_numpy()[
            primary_mask.to_numpy()
        ]
        == "observed_primary"
    ).all()

    assert (
        cleaning_method_rank.to_numpy()[
            primary_mask.to_numpy()
        ]
        == 0
    ).all()

    # The fallback observation has rank 1.
    assert (
        cleaned.loc[
            fallback_timestamp,
            "AAA",
        ]
        == 10_000.0
    )

    assert (
        data_source.loc[
            fallback_timestamp,
            "AAA",
        ]
        == "fallback"
    )

    assert (
        cleaning_method.loc[
            fallback_timestamp,
            "AAA",
        ]
        == "observed_fallback"
    )

    assert (
        cleaning_method_rank.loc[
            fallback_timestamp,
            "AAA",
        ]
        == 1
    )

    # The two-hour gap is filled by interpolation at rank 2.
    assert cleaned.loc[
        interpolation_timestamps,
        "AAA",
    ].notna().all()

    assert cleaning_method.loc[
        interpolation_timestamps,
        "AAA",
    ].eq(
        "interpolate_short_gaps"
    ).all()

    assert cleaning_method_rank.loc[
        interpolation_timestamps,
        "AAA",
    ].eq(2).all()

    left_value = cleaned.loc[
        index[219],
        "AAA",
    ]
    right_value = cleaned.loc[
        index[222],
        "AAA",
    ]

    expected_interpolation = np.linspace(
        left_value,
        right_value,
        4,
    )[1:3]

    np.testing.assert_allclose(
        cleaned.loc[
            interpolation_timestamps,
            "AAA",
        ].to_numpy(),
        expected_interpolation,
    )

    # The four-hour gap is copied from seven days earlier at rank 3.
    source_timestamps = (
        copy_timestamps
        - pd.Timedelta(hours=168)
    )

    np.testing.assert_allclose(
        cleaned.loc[
            copy_timestamps,
            "AAA",
        ].to_numpy(),
        cleaned.loc[
            source_timestamps,
            "AAA",
        ].to_numpy(),
    )

    assert cleaning_method.loc[
        copy_timestamps,
        "AAA",
    ].eq(
        "copy_previous_week"
    ).all()

    assert cleaning_method_rank.loc[
        copy_timestamps,
        "AAA",
    ].eq(3).all()

    # The initial gap remains unresolved at the final rank.
    assert cleaned.loc[
        unresolved_timestamps,
        "AAA",
    ].isna().all()

    assert cleaning_method.loc[
        unresolved_timestamps,
        "AAA",
    ].eq("missing").all()

    assert cleaning_method_rank.loc[
        unresolved_timestamps,
        "AAA",
    ].eq(4).all()

    # Derived and unresolved values have no observed data source.
    derived_or_missing = (
        interpolation_timestamps
        .append(copy_timestamps)
        .append(unresolved_timestamps)
    )

    assert data_source.loc[
        derived_or_missing,
        "AAA",
    ].isna().all()

    expected_method_counts = {
        "observed_primary": 389,
        "observed_fallback": 1,
        "interpolate_short_gaps": 2,
        "copy_previous_week": 4,
        "missing": 4,
    }

    assert (
        cleaning_method["AAA"]
        .value_counts()
        .to_dict()
        == expected_method_counts
    )

    expected_rank_counts = {
        0: 389,
        1: 1,
        2: 2,
        3: 4,
        4: 4,
    }

    assert (
        cleaning_method_rank["AAA"]
        .value_counts()
        .sort_index()
        .to_dict()
        == expected_rank_counts
    )