"""Tests for compiling auxiliary-data requirements."""

import pandas as pd
from cleaning.advanced.requirements import (
    REQUIREMENT_COLUMNS,
    compile_auxiliary_requirements,
)


def test_compile_auxiliary_requirements_collects_sources() -> None:
    overrides = {
        "reconstruct_albania": {
            "country": "ALB",
            "start": "2021-01-01",
            "end": "2021-01-03",
            "scope": "fill_gaps_within_period",
            "method": "construct_from_sources",
            "sources": [
                {
                    "country": "GRC",
                    "start": "2019-01-01",
                    "end": "2019-01-03",
                },
                {
                    "country": "MNE",
                    "start": "2020-01-01",
                    "end": "2020-01-03",
                    "weight": 2,
                },
            ],
        },
    }

    result = compile_auxiliary_requirements(overrides)

    expected = pd.DataFrame(
        {
            "country": ["GRC", "MNE"],
            "start": pd.to_datetime(
                [
                    "2019-01-01",
                    "2020-01-01",
                ],
                utc=True,
            ),
            "end": pd.to_datetime(
                [
                    "2019-01-03",
                    "2020-01-03",
                ],
                utc=True,
            ),
        }
    )

    pd.testing.assert_frame_equal(
        result,
        expected,
    )


def test_compile_auxiliary_requirements_includes_scaling_sources() -> None:
    overrides = {
        "reconstruct_albania": {
            "country": "ALB",
            "start": "2021-01-01",
            "end": "2021-01-03",
            "scope": "fill_gaps_within_period",
            "method": "construct_from_sources",
            "sources": [
                {
                    "country": "GRC",
                    "start": "2019-01-01",
                    "end": "2019-01-03",
                },
            ],
            "scaling": {
                "method": "match_energy",
                "target_sources": [
                    {
                        "country": "ALB",
                        "start": "2020-01-01",
                        "end": "2020-01-03",
                    },
                ],
            },
        },
    }

    result = compile_auxiliary_requirements(overrides)

    assert list(result["country"]) == [
        "ALB",
        "GRC",
    ]

    assert result.loc[
        result["country"] == "ALB",
        "start",
    ].iloc[0] == pd.Timestamp(
        "2020-01-01",
        tz="UTC",
    )


def test_compile_auxiliary_requirements_deduplicates_sources() -> None:
    source = {
        "country": "GRC",
        "start": "2019-01-01",
        "end": "2019-01-03",
    }

    overrides = {
        "first_rule": {
            "method": "construct_from_sources",
            "sources": [source],
        },
        "second_rule": {
            "method": "construct_from_sources",
            "sources": [source],
        },
    }

    result = compile_auxiliary_requirements(overrides)

    assert len(result) == 1


def test_compile_auxiliary_requirements_ignores_other_methods() -> None:
    overrides = {
        "manual_case": {
            "method": "manual_review",
        },
        "leave_case": {
            "method": "leave_missing",
        },
    }

    result = compile_auxiliary_requirements(overrides)

    assert result.empty
    assert list(result.columns) == REQUIREMENT_COLUMNS


def test_compile_auxiliary_requirements_returns_empty_schema() -> None:
    result = compile_auxiliary_requirements({})

    assert result.empty
    assert list(result.columns) == REQUIREMENT_COLUMNS

def test_compile_auxiliary_requirements_merges_overlapping_periods() -> None:
    overrides = {
        "first_rule": {
            "method": "construct_from_sources",
            "sources": [
                {
                    "country": "GRC",
                    "start": "2019-01-01",
                    "end": "2019-06-01",
                },
            ],
        },
        "second_rule": {
            "method": "construct_from_sources",
            "sources": [
                {
                    "country": "GRC",
                    "start": "2019-05-01",
                    "end": "2019-12-01",
                },
            ],
        },
    }

    result = compile_auxiliary_requirements(overrides)

    assert len(result) == 1
    assert result.iloc[0]["start"] == pd.Timestamp(
        "2019-01-01",
        tz="UTC",
    )
    assert result.iloc[0]["end"] == pd.Timestamp(
        "2019-12-01",
        tz="UTC",
    )

def test_compile_auxiliary_requirements_merges_adjacent_periods() -> None:
    overrides = {
        "first_rule": {
            "method": "construct_from_sources",
            "sources": [
                {
                    "country": "GRC",
                    "start": "2019-01-01",
                    "end": "2019-02-01",
                },
            ],
        },
        "second_rule": {
            "method": "construct_from_sources",
            "sources": [
                {
                    "country": "GRC",
                    "start": "2019-02-01",
                    "end": "2019-03-01",
                },
            ],
        },
    }

    result = compile_auxiliary_requirements(overrides)

    assert len(result) == 1
    assert result.iloc[0]["start"] == pd.Timestamp(
        "2019-01-01",
        tz="UTC",
    )
    assert result.iloc[0]["end"] == pd.Timestamp(
        "2019-03-01",
        tz="UTC",
    )
