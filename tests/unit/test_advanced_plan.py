"""Tests for advanced auxiliary-fill planning."""

import pandas as pd
import pytest
from cleaning.advanced.planning.plan import (
    build_auxiliary_fill_plan,
    validate_auxiliary_fill_rule,
)

TARGET_COUNTRIES = ["ALB"]

TARGET_START = pd.Timestamp(
    "2022-01-01",
    tz="UTC",
)

TARGET_END = pd.Timestamp(
    "2025-01-01",
    tz="UTC",
)


def test_validate_construct_from_sources_rule() -> None:
    rule = {
        "country": "ALB",
        "start": "2023-01-01",
        "end": "2023-12-31 23:00",
        "scope": "overwrite",
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
        "scope": "overwrite",
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
        "scope": "overwrite",
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
        "scope": "overwrite",
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
        "scope": "overwrite",
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
        "scope": "overwrite",
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
        "scope": "overwrite",
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
            "scope": "overwrite",
            "method": "external_profile",
        },
        "construct_albania": {
            "country": "ALB",
            "start": "2023-01-01",
            "end": "2023-12-31 23:00",
            "scope": "overwrite",
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

    result = build_auxiliary_fill_plan(
        rules,
        target_countries=TARGET_COUNTRIES,
        target_start=TARGET_START,
        target_end=TARGET_END,
    )

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
                "overwrite",
                "overwrite",
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
    result = build_auxiliary_fill_plan(
        {},
        target_countries=TARGET_COUNTRIES,
        target_start=TARGET_START,
        target_end=TARGET_END,
    )

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


def test_build_auxiliary_fill_plan_ignores_wrong_country() -> None:
    rules = {
        "albania": {
            "country": "ALB",
            "start": "2023-01-01",
            "end": "2023-02-01",
            "scope": "overwrite",
            "method": "construct_from_sources",
            "sources": [
                {
                    "country": "GBR",
                    "start": "2023-01-01",
                    "end": "2023-02-01",
                }
            ],
        },
        "montenegro": {
            "country": "MNE",
            "start": "2023-01-01",
            "end": "2023-02-01",
            "scope": "overwrite",
            "method": "construct_from_sources",
            "sources": [
                {
                    "country": "GBR",
                    "start": "2023-01-01",
                    "end": "2023-02-01",
                }
            ],
        },
    }

    result = build_auxiliary_fill_plan(
        rules,
        target_countries=["ALB"],
        target_start=TARGET_START,
        target_end=TARGET_END,
    )

    assert result["rule_name"].tolist() == [
        "albania"
    ]


def test_build_auxiliary_fill_plan_ignores_non_overlapping_periods() -> None:
    rules = {
        "before": {
            "country": "ALB",
            "start": "2020-01-01",
            "end": "2020-02-01",
            "scope": "overwrite",
            "method": "construct_from_sources",
            "sources": [
                {
                    "country": "GBR",
                    "start": "2020-01-01",
                    "end": "2020-02-01",
                }
            ],
        },
        "after": {
            "country": "ALB",
            "start": "2026-01-01",
            "end": "2026-02-01",
            "scope": "overwrite",
            "method": "construct_from_sources",
            "sources": [
                {
                    "country": "GBR",
                    "start": "2026-01-01",
                    "end": "2026-02-01",
                }
            ],
        },
    }

    result = build_auxiliary_fill_plan(
        rules,
        target_countries=TARGET_COUNTRIES,
        target_start=TARGET_START,
        target_end=TARGET_END,
    )

    assert result.empty


def test_build_auxiliary_fill_plan_keeps_partial_overlap() -> None:
    rules = {
        "partial": {
            "country": "ALB",
            "start": "2021-12-01",
            "end": "2022-02-01",
            "scope": "overwrite",
            "method": "construct_from_sources",
            "sources": [
                {
                    "country": "GBR",
                    "start": "2021-12-01",
                    "end": "2022-02-01",
                }
            ],
        },
    }

    result = build_auxiliary_fill_plan(
        rules,
        target_countries=TARGET_COUNTRIES,
        target_start=TARGET_START,
        target_end=TARGET_END,
    )

    assert result["rule_name"].tolist() == [
        "partial"
    ]


def test_build_auxiliary_fill_plan_validates_inactive_rule() -> None:
    rules = {
        "invalid_montenegro": {
            "country": "MNE",
            "start": "2020-01-01",
            "end": "2020-02-01",
            "scope": "not_a_scope",
            "method": "construct_from_sources",
            "sources": [
                {
                    "country": "GBR",
                    "start": "2020-01-01",
                    "end": "2020-02-01",
                }
            ],
        },
    }

    with pytest.raises(
        ValueError,
        match="Unsupported scope",
    ):
        build_auxiliary_fill_plan(
            rules,
            target_countries=TARGET_COUNTRIES,
            target_start=TARGET_START,
            target_end=TARGET_END,
        )


def test_build_auxiliary_fill_plan_excludes_touching_periods() -> None:
    rules = {
        "ends_at_start": {
            "country": "ALB",
            "start": "2021-12-01",
            "end": "2022-01-01",
            "scope": "overwrite",
            "method": "construct_from_sources",
            "sources": [
                {
                    "country": "GBR",
                    "start": "2021-12-01",
                    "end": "2022-01-01",
                }
            ],
        },
        "starts_at_end": {
            "country": "ALB",
            "start": "2025-01-01",
            "end": "2025-02-01",
            "scope": "overwrite",
            "method": "construct_from_sources",
            "sources": [
                {
                    "country": "GBR",
                    "start": "2025-01-01",
                    "end": "2025-02-01",
                }
            ],
        },
    }

    result = build_auxiliary_fill_plan(
        rules,
        target_countries=TARGET_COUNTRIES,
        target_start=TARGET_START,
        target_end=TARGET_END,
    )

    assert result.empty
