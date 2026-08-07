"""Tests for auxiliary source-request planning."""

import pandas as pd
import pytest
from cleaning.advanced.source_requests import (
    SOURCE_REQUEST_COLUMNS,
    build_auxiliary_source_requests,
    build_auxiliary_source_batches,
)


def test_build_source_requests_uses_all_applicable_sources() -> None:
    requirements = pd.DataFrame(
        {
            "country": ["GBR", "GRC"],
            "start": pd.to_datetime(
                [
                    "2020-01-01",
                    "2021-01-01",
                ],
                utc=True,
            ),
            "end": pd.to_datetime(
                [
                    "2020-02-01",
                    "2021-02-01",
                ],
                utc=True,
            ),
        }
    )

    result = build_auxiliary_source_requests(
        requirements,
        source_names=[
            "entsoe_api",
            "neso",
            "opsd",
        ],
    )

    assert list(
        result[["source", "country"]]
        .itertuples(index=False, name=None)
    ) == [
        ("entsoe_api", "GBR"),
        ("entsoe_api", "GRC"),
        ("neso", "GBR"),
        ("opsd", "GBR"),
        ("opsd", "GRC"),
    ]


def test_neso_is_only_requested_for_gbr() -> None:
    requirements = pd.DataFrame(
        {
            "country": ["GRC"],
            "start": [
                pd.Timestamp(
                    "2020-01-01",
                    tz="UTC",
                )
            ],
            "end": [
                pd.Timestamp(
                    "2020-02-01",
                    tz="UTC",
                )
            ],
        }
    )

    result = build_auxiliary_source_requests(
        requirements,
        source_names=["neso"],
    )

    assert result.empty
    assert list(result.columns) == SOURCE_REQUEST_COLUMNS


def test_empty_requirements_return_empty_source_request_schema() -> None:
    requirements = pd.DataFrame(
        columns=[
            "country",
            "start",
            "end",
        ]
    )

    result = build_auxiliary_source_requests(
        requirements,
        source_names=[
            "entsoe_api",
            "neso",
            "opsd",
        ],
    )

    assert result.empty
    assert list(result.columns) == SOURCE_REQUEST_COLUMNS


def test_unknown_source_is_rejected() -> None:
    requirements = pd.DataFrame(
        columns=[
            "country",
            "start",
            "end",
        ]
    )

    with pytest.raises(
        ValueError,
        match="Unsupported auxiliary load sources",
    ):
        build_auxiliary_source_requests(
            requirements,
            source_names=["mystery_source"],
        )


def test_duplicate_source_names_are_rejected() -> None:
    requirements = pd.DataFrame(
        columns=[
            "country",
            "start",
            "end",
        ]
    )

    with pytest.raises(
        ValueError,
        match="must be unique",
    ):
        build_auxiliary_source_requests(
            requirements,
            source_names=[
                "entsoe_api",
                "entsoe_api",
            ],
        )

def test_build_source_batches_groups_matching_periods() -> None:
    requests = pd.DataFrame(
        {
            "source": [
                "entsoe_api",
                "entsoe_api",
                "entsoe_api",
            ],
            "country": [
                "ALB",
                "GRC",
                "MNE",
            ],
            "start": pd.to_datetime(
                [
                    "2020-01-01",
                    "2020-01-01",
                    "2021-01-01",
                ],
                utc=True,
            ),
            "end": pd.to_datetime(
                [
                    "2020-02-01",
                    "2020-02-01",
                    "2021-02-01",
                ],
                utc=True,
            ),
        }
    )

    result = build_auxiliary_source_batches(
        requests
    )

    assert result == [
        {
            "source": "entsoe_api",
            "start": pd.Timestamp(
                "2020-01-01",
                tz="UTC",
            ),
            "end": pd.Timestamp(
                "2020-02-01",
                tz="UTC",
            ),
            "countries": [
                "ALB",
                "GRC",
            ],
        },
        {
            "source": "entsoe_api",
            "start": pd.Timestamp(
                "2021-01-01",
                tz="UTC",
            ),
            "end": pd.Timestamp(
                "2021-02-01",
                tz="UTC",
            ),
            "countries": [
                "MNE",
            ],
        },
    ]

def test_build_source_batches_keeps_sources_separate() -> None:
    start = pd.Timestamp(
        "2020-01-01",
        tz="UTC",
    )
    end = pd.Timestamp(
        "2020-02-01",
        tz="UTC",
    )

    requests = pd.DataFrame(
        {
            "source": [
                "entsoe_api",
                "opsd",
            ],
            "country": [
                "GBR",
                "GBR",
            ],
            "start": [
                start,
                start,
            ],
            "end": [
                end,
                end,
            ],
        }
    )

    result = build_auxiliary_source_batches(
        requests
    )

    assert len(result) == 2

    assert [
        batch["source"]
        for batch in result
    ] == [
        "entsoe_api",
        "opsd",
    ]

def test_build_source_batches_returns_empty_list() -> None:
    requests = pd.DataFrame(
        columns=SOURCE_REQUEST_COLUMNS
    )

    assert build_auxiliary_source_batches(
        requests
    ) == []
