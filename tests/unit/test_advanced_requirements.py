"""Tests for compiling auxiliary-data requirements."""

import pandas as pd
from cleaning.advanced.planning.requirements import (
    REQUIREMENT_COLUMNS,
    build_auxiliary_acquisition_requirements,
    compile_auxiliary_requirements,
    expand_auxiliary_requirements,
    get_basic_cleaning_context,
)


def test_compile_auxiliary_requirements_collects_sources() -> None:
    overrides = {
        "reconstruct_albania": {
            "country": "ALB",
            "start": "2021-01-01",
            "end": "2021-01-03",
            "scope": "fill_gaps",
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
            "scope": "fill_gaps",
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
            "method": "leave_missing",
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

def test_expand_requirements_without_rules_is_unchanged() -> None:
    requirements = pd.DataFrame(
        {
            "country": ["GRC"],
            "start": [pd.Timestamp("2020-01-01", tz="UTC")],
            "end": [pd.Timestamp("2020-02-01", tz="UTC")],
        }
    )

    result = expand_auxiliary_requirements(
        requirements,
        rules=[],
    )

    pd.testing.assert_frame_equal(
        result,
        requirements,
    )

def test_expand_requirements_can_be_disabled() -> None:
    requirements = pd.DataFrame(
        {
            "country": ["GRC"],
            "start": [pd.Timestamp("2020-01-01", tz="UTC")],
            "end": [pd.Timestamp("2020-02-01", tz="UTC")],
        }
    )

    rules = [
        {
            "name": "copy_previous_week",
            "method": "copy_period",
            "max_gap": "168h",
            "source_offset": "-168h",
        }
    ]

    result = expand_auxiliary_requirements(
        requirements,
        rules=rules,
        enabled=False,
    )

    pd.testing.assert_frame_equal(
        result,
        requirements,
    )


def test_basic_context_for_copy_period() -> None:
    rules = [
        {
            "name": "copy_previous_week",
            "method": "copy_period",
            "max_gap": "168h",
            "source_offset": "-168h",
        }
    ]

    left, right = get_basic_cleaning_context(rules)

    assert left == pd.Timedelta("7D")
    assert right == pd.Timedelta("7D")


def test_basic_context_compounds_across_ordered_rules() -> None:
    rules = [
        {
            "name": "average_adjacent_weeks",
            "method": "average_periods",
            "max_gap": "168h",
            "source_offsets": [
                "-168h",
                "168h",
            ],
        },
        {
            "name": "copy_previous_week",
            "method": "copy_period",
            "max_gap": "168h",
            "source_offset": "-168h",
        },
    ]

    left, right = get_basic_cleaning_context(rules)

    assert left == pd.Timedelta("14D")
    assert right == pd.Timedelta("7D")


def test_build_auxiliary_acquisition_requirements_uses_basic_cleaning_config() -> None:
    overrides = {
        "reconstruct_albania": {
            "method": "construct_from_sources",
            "sources": [
                {
                    "country": "GRC",
                    "start": "2020-01-01",
                    "end": "2020-02-01",
                },
            ],
        },
    }

    basic_rules = [
        {
            "name": "copy_previous_week",
            "method": "copy_period",
            "max_gap": "168h",
            "source_offset": "-168h",
        },
    ]

    result = build_auxiliary_acquisition_requirements(
        overrides=overrides,
        basic_rules=basic_rules,
        basic_cleaning_enabled=True,
    )

    assert result.iloc[0]["start"] == pd.Timestamp(
        "2019-12-25",
        tz="UTC",
    )
    assert result.iloc[0]["end"] == pd.Timestamp(
        "2020-02-08",
        tz="UTC",
    )
