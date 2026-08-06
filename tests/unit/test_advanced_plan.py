"""Tests for advanced auxiliary-fill planning."""
import pandas as pd
import pytest
from cleaning.advanced.plan import (
    build_auxiliary_fill_plan,
    validate_auxiliary_fill_rule,
)


def test_validate_construct_from_sources_rule() -> None:
    rule = {
        "country": "ALB",
        "start": "2023-01-01",
        "end": "2023-12-31 23:00",
        "scope": "overwrite_entire_period",
        "method": "construct_from_sources",
        "sources": [
            {
                "country": "MKD",
                "start": "2023-01-01",
                "end": "2023-12-31 23:00",
            },
            {
                "country": "MNE",
                "start": "2023-01-01",
                "end": "2023-12-31 23:00",
                "weight": 2,
            },
        ],
    }

    validate_auxiliary_fill_rule(
        "replace_albania_2023",
        rule,
    )

def test_validate_external_profile_rule() -> None:
    rule = {
        "country": "ALB",
        "start": "2023-01-01",
        "end": "2023-12-31 23:00",
        "scope": "overwrite_entire_period",
        "method": "external_profile",
    }

    validate_auxiliary_fill_rule(
        "external_albania_2023",
        rule,
    )

def test_construct_from_sources_requires_sources() -> None:
    rule = {
        "country": "ALB",
        "start": "2023-01-01",
        "end": "2023-12-31 23:00",
        "scope": "overwrite_entire_period",
        "method": "construct_from_sources",
    }

    with pytest.raises(
        ValueError,
        match="must define 'sources'",
    ):
        validate_auxiliary_fill_rule(
            "replace_albania_2023",
            rule,
        )

def test_source_weight_must_be_positive() -> None:
    rule = {
        "country": "ALB",
        "start": "2023-01-01",
        "end": "2023-12-31 23:00",
        "scope": "overwrite_entire_period",
        "method": "construct_from_sources",
        "sources": [
            {
                "country": "MNE",
                "start": "2023-01-01",
                "end": "2023-12-31 23:00",
                "weight": 0,
            }
        ],
    }

    with pytest.raises(
        ValueError,
        match="must be greater than zero",
    ):
        validate_auxiliary_fill_rule(
            "replace_albania_2023",
            rule,
        )

def test_validate_construct_from_sources_with_scaling() -> None:
    rule = {
        "country": "ALB",
        "start": "2023-01-01",
        "end": "2023-12-31 23:00",
        "scope": "overwrite_entire_period",
        "method": "construct_from_sources",
        "sources": [
            {
                "country": "MKD",
                "start": "2023-01-01",
                "end": "2023-12-31 23:00",
            }
        ],
        "scaling": {
            "method": "match_energy",
            "target_sources": [
                {
                    "country": "ALB",
                    "start": "2022-01-01",
                    "end": "2022-12-31 23:00",
                },
                {
                    "country": "ALB",
                    "start": "2024-01-01",
                    "end": "2024-12-31 23:00",
                    "weight": 2,
                },
            ],
        },
    }

    validate_auxiliary_fill_rule(
        "replace_albania_2023",
        rule,
    )

def test_match_energy_scaling_requires_target_sources() -> None:
    rule = {
        "country": "ALB",
        "start": "2023-01-01",
        "end": "2023-12-31 23:00",
        "scope": "overwrite_entire_period",
        "method": "construct_from_sources",
        "sources": [
            {
                "country": "MNE",
                "start": "2023-01-01",
                "end": "2023-12-31 23:00",
            }
        ],
        "scaling": {
            "method": "match_energy",
        },
    }

    with pytest.raises(
        ValueError,
        match="must define 'target_sources'",
    ):
        validate_auxiliary_fill_rule(
            "replace_albania_2023",
            rule,
        )

def test_rejects_unsupported_scaling_method() -> None:
    rule = {
        "country": "ALB",
        "start": "2023-01-01",
        "end": "2023-12-31 23:00",
        "scope": "overwrite_entire_period",
        "method": "construct_from_sources",
        "sources": [
            {
                "country": "MNE",
                "start": "2023-01-01",
                "end": "2023-12-31 23:00",
            }
        ],
        "scaling": {
            "method": "unknown",
            "target_sources": [
                {
                    "country": "ALB",
                    "start": "2022-01-01",
                    "end": "2022-12-31 23:00",
                }
            ],
        },
    }

    with pytest.raises(
        ValueError,
        match="Unsupported scaling method",
    ):
        validate_auxiliary_fill_rule(
            "replace_albania_2023",
            rule,
        )

def test_build_auxiliary_fill_plan_normalizes_rules() -> None:
    rules = {
        "external_albania": {
            "country": "ALB",
            "start": "2024-01-01",
            "end": "2024-12-31 23:00",
            "scope": "overwrite_entire_period",
            "method": "external_profile",
        },
        "construct_albania": {
            "country": "ALB",
            "start": "2023-01-01",
            "end": "2023-12-31 23:00",
            "scope": "overwrite_entire_period",
            "method": "construct_from_sources",
            "sources": [
                {
                    "country": "MNE",
                    "start": "2023-01-01",
                    "end": "2023-12-31 23:00",
                },
                {
                    "country": "MKD",
                    "start": "2023-01-01",
                    "end": "2023-12-31 23:00",
                    "weight": 2,
                },
            ],
            "scaling": {
                "method": "match_energy",
                "target_sources": [
                    {
                        "country": "ALB",
                        "start": "2022-01-01",
                        "end": "2022-12-31 23:00",
                    }
                ],
            },
        },
    }

    result = build_auxiliary_fill_plan(rules)

    expected = pd.DataFrame(
        {
            "rule_name": [
                "construct_albania",
                "external_albania",
            ],
            "country": [
                "ALB",
                "ALB",
            ],
            "target_start": [
                pd.Timestamp(
                    "2023-01-01",
                    tz="UTC",
                ),
                pd.Timestamp(
                    "2024-01-01",
                    tz="UTC",
                ),
            ],
            "target_end": [
                pd.Timestamp(
                    "2023-12-31 23:00",
                    tz="UTC",
                ),
                pd.Timestamp(
                    "2024-12-31 23:00",
                    tz="UTC",
                ),
            ],
            "scope": [
                "overwrite_entire_period",
                "overwrite_entire_period",
            ],
            "method": [
                "construct_from_sources",
                "external_profile",
            ],
            "status": [
                "ready",
                "not_implemented",
            ],
            "source_count": [
                2,
                0,
            ],
            "scaling_method": [
                "match_energy",
                None,
            ],
        }
    )

    pd.testing.assert_frame_equal(
        result,
        expected,
    )

def test_build_auxiliary_fill_plan_returns_empty_schema() -> None:
    result = build_auxiliary_fill_plan({})

    expected = pd.DataFrame(
        columns=[
            "rule_name",
            "country",
            "target_start",
            "target_end",
            "scope",
            "method",
            "status",
            "source_count",
            "scaling_method",
        ]
    )

    pd.testing.assert_frame_equal(
        result,
        expected,
    )
