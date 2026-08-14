"""Tests for auxiliary source-request planning."""

import pandas as pd
import pytest
from cleaning.advanced.planning.source_requests import (
    SOURCE_REQUEST_COLUMNS,
    _build_batch_id,
    _build_group_id,
    build_auxiliary_source_batches,
    build_auxiliary_source_requests,
)


def test_build_source_requests_uses_all_applicable_sources() -> None:
    requirements = pd.DataFrame(
        {
            "country": ["GBR", "GRC"],
            "start": pd.to_datetime(["2020-01-01", "2021-01-01"], utc=True),
            "end": pd.to_datetime(["2020-02-01", "2021-02-01"], utc=True),
        }
    )

    result = build_auxiliary_source_requests(
        requirements, source_names=["entsoe_api", "neso", "opsd_api"]
    )

    assert list(result[["source", "country"]].itertuples(index=False, name=None)) == [
        ("entsoe_api", "GBR"),
        ("entsoe_api", "GRC"),
        ("neso", "GBR"),
        ("opsd_api", "GBR"),
        ("opsd_api", "GRC"),
    ]


def test_neso_is_only_requested_for_gbr() -> None:
    requirements = pd.DataFrame(
        {
            "country": ["GRC"],
            "start": [pd.Timestamp("2020-01-01", tz="UTC")],
            "end": [pd.Timestamp("2020-02-01", tz="UTC")],
        }
    )

    result = build_auxiliary_source_requests(requirements, source_names=["neso"])

    assert result.empty
    assert list(result.columns) == SOURCE_REQUEST_COLUMNS


def test_empty_requirements_return_empty_source_request_schema() -> None:
    requirements = pd.DataFrame(columns=["country", "start", "end"])

    result = build_auxiliary_source_requests(
        requirements, source_names=["entsoe_api", "neso", "opsd_api"]
    )

    assert result.empty
    assert list(result.columns) == SOURCE_REQUEST_COLUMNS


def test_unknown_source_is_rejected_when_planning_request() -> None:
    """Reject a source without defined country applicability."""
    requirements = pd.DataFrame(
        {
            "country": ["ALB"],
            "start": [pd.Timestamp("2020-01-01", tz="UTC")],
            "end": [pd.Timestamp("2020-02-01", tz="UTC")],
        }
    )

    with pytest.raises(ValueError, match="Unsupported auxiliary load source"):
        build_auxiliary_source_requests(requirements, source_names=["mystery_source"])


def test_build_batch_id_is_independent_of_country_order() -> None:
    first = _build_batch_id(
        source="entsoe_api",
        start=pd.Timestamp("2020-01-01", tz="UTC"),
        end=pd.Timestamp("2020-02-01", tz="UTC"),
        countries=["ALB", "GRC"],
    )

    second = _build_batch_id(
        source="entsoe_api",
        start=pd.Timestamp("2020-01-01", tz="UTC"),
        end=pd.Timestamp("2020-02-01", tz="UTC"),
        countries=["GRC", "ALB"],
    )

    assert first == second

    assert first.startswith("entsoe_api__20200101T0000__20200201T0000__")


def test_build_batch_id_changes_for_different_country_sets() -> None:
    common = {
        "source": "entsoe_api",
        "start": pd.Timestamp("2020-01-01", tz="UTC"),
        "end": pd.Timestamp("2020-02-01", tz="UTC"),
    }

    first = _build_batch_id(**common, countries=["ALB"])

    second = _build_batch_id(**common, countries=["ALB", "GRC"])

    assert first != second


def test_build_group_id_depends_only_on_period() -> None:
    start = pd.Timestamp("2020-01-01", tz="UTC")
    end = pd.Timestamp("2020-02-01", tz="UTC")

    assert _build_group_id(start=start, end=end) == ("20200101T0000__20200201T0000")


def test_build_source_batches_groups_matching_periods() -> None:
    requests = pd.DataFrame(
        {
            "source": ["entsoe_api", "entsoe_api", "entsoe_api"],
            "country": ["ALB", "GRC", "MNE"],
            "start": pd.to_datetime(
                ["2020-01-01", "2020-01-01", "2021-01-01"], utc=True
            ),
            "end": pd.to_datetime(["2020-02-01", "2020-02-01", "2021-02-01"], utc=True),
        }
    )

    result = build_auxiliary_source_batches(requests)

    first_start = pd.Timestamp("2020-01-01", tz="UTC")
    first_end = pd.Timestamp("2020-02-01", tz="UTC")
    second_start = pd.Timestamp("2021-01-01", tz="UTC")
    second_end = pd.Timestamp("2021-02-01", tz="UTC")

    assert result == [
        {
            "group_id": _build_group_id(start=first_start, end=first_end),
            "batch_id": _build_batch_id(
                source="entsoe_api",
                start=first_start,
                end=first_end,
                countries=["ALB", "GRC"],
            ),
            "source": "entsoe_api",
            "start": first_start,
            "end": first_end,
            "countries": ["ALB", "GRC"],
        },
        {
            "group_id": _build_group_id(start=second_start, end=second_end),
            "batch_id": _build_batch_id(
                source="entsoe_api",
                start=second_start,
                end=second_end,
                countries=["MNE"],
            ),
            "source": "entsoe_api",
            "start": second_start,
            "end": second_end,
            "countries": ["MNE"],
        },
    ]


def test_build_source_batches_keeps_sources_separate() -> None:
    start = pd.Timestamp("2020-01-01", tz="UTC")
    end = pd.Timestamp("2020-02-01", tz="UTC")

    requests = pd.DataFrame(
        {
            "source": ["entsoe_api", "opsd_api"],
            "country": ["GBR", "GBR"],
            "start": [start, start],
            "end": [end, end],
        }
    )

    result = build_auxiliary_source_batches(requests)

    group_id = _build_group_id(start=start, end=end)

    assert result == [
        {
            "group_id": group_id,
            "batch_id": _build_batch_id(
                source="entsoe_api", start=start, end=end, countries=["GBR"]
            ),
            "source": "entsoe_api",
            "start": start,
            "end": end,
            "countries": ["GBR"],
        },
        {
            "group_id": group_id,
            "batch_id": _build_batch_id(
                source="opsd_api", start=start, end=end, countries=["GBR"]
            ),
            "source": "opsd_api",
            "start": start,
            "end": end,
            "countries": ["GBR"],
        },
    ]


def test_build_source_batches_returns_empty_list() -> None:
    requests = pd.DataFrame(columns=SOURCE_REQUEST_COLUMNS)

    assert build_auxiliary_source_batches(requests) == []
