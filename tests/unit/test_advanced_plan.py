"""Tests for advanced auxiliary-fill planning."""

import pandas as pd
from cleaning.advanced.planning.plan import build_auxiliary_fill_plan

TARGET_COUNTRIES = ["ALB"]
TARGET_START = pd.Timestamp("2022-01-01", tz="UTC")
TARGET_END = pd.Timestamp("2025-01-01", tz="UTC")


def test_build_auxiliary_fill_plan_normalizes_rules() -> None:
    """Build a normalized plan for active overrides."""
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
                {"country": "MNE", "start": "2023-01-01", "end": "2023-12-31 23:00"},
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
                    {"country": "ALB", "start": "2022-01-01", "end": "2022-12-31 23:00"}
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
            "rule_name": ["construct_albania", "external_albania"],
            "country": ["ALB", "ALB"],
            "target_start": [
                pd.Timestamp("2023-01-01", tz="UTC"),
                pd.Timestamp("2024-01-01", tz="UTC"),
            ],
            "target_end": [
                pd.Timestamp("2023-12-31 23:00", tz="UTC"),
                pd.Timestamp("2024-12-31 23:00", tz="UTC"),
            ],
            "scope": ["overwrite", "overwrite"],
            "method": ["construct_from_sources", "external_profile"],
            "status": ["ready", "ready"],
            "source_count": [2, 0],
            "scaling_method": ["match_energy", None],
        }
    )

    pd.testing.assert_frame_equal(result, expected)


def test_build_auxiliary_fill_plan_returns_empty_schema() -> None:
    """Return the expected empty plan structure when no overrides are configured."""
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

    pd.testing.assert_frame_equal(result, expected)


def test_build_auxiliary_fill_plan_ignores_wrong_country() -> None:
    """Exclude overrides for countries outside the target scope."""
    rules = {
        "albania": {
            "country": "ALB",
            "start": "2023-01-01",
            "end": "2023-02-01",
            "scope": "overwrite",
            "method": "construct_from_sources",
            "sources": [{"country": "GBR", "start": "2023-01-01", "end": "2023-02-01"}],
        },
        "montenegro": {
            "country": "MNE",
            "start": "2023-01-01",
            "end": "2023-02-01",
            "scope": "overwrite",
            "method": "construct_from_sources",
            "sources": [{"country": "GBR", "start": "2023-01-01", "end": "2023-02-01"}],
        },
    }

    result = build_auxiliary_fill_plan(
        rules,
        target_countries=["ALB"],
        target_start=TARGET_START,
        target_end=TARGET_END,
    )

    assert result["rule_name"].tolist() == ["albania"]


def test_build_auxiliary_fill_plan_ignores_non_overlapping_periods() -> None:
    """Exclude overrides whose periods do not intersect the target period."""
    rules = {
        "before": {
            "country": "ALB",
            "start": "2020-01-01",
            "end": "2020-02-01",
            "scope": "overwrite",
            "method": "construct_from_sources",
            "sources": [{"country": "GBR", "start": "2020-01-01", "end": "2020-02-01"}],
        },
        "after": {
            "country": "ALB",
            "start": "2026-01-01",
            "end": "2026-02-01",
            "scope": "overwrite",
            "method": "construct_from_sources",
            "sources": [{"country": "GBR", "start": "2026-01-01", "end": "2026-02-01"}],
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
    """Keep overrides that partially overlap the target period."""
    rules = {
        "partial": {
            "country": "ALB",
            "start": "2021-12-01",
            "end": "2022-02-01",
            "scope": "overwrite",
            "method": "construct_from_sources",
            "sources": [{"country": "GBR", "start": "2021-12-01", "end": "2022-02-01"}],
        }
    }

    result = build_auxiliary_fill_plan(
        rules,
        target_countries=TARGET_COUNTRIES,
        target_start=TARGET_START,
        target_end=TARGET_END,
    )

    assert result["rule_name"].tolist() == ["partial"]


def test_build_auxiliary_fill_plan_excludes_touching_periods() -> None:
    """Treat touching half-open periods as non-overlapping."""
    rules = {
        "ends_at_start": {
            "country": "ALB",
            "start": "2021-12-01",
            "end": "2022-01-01",
            "scope": "overwrite",
            "method": "construct_from_sources",
            "sources": [{"country": "GBR", "start": "2021-12-01", "end": "2022-01-01"}],
        },
        "starts_at_end": {
            "country": "ALB",
            "start": "2025-01-01",
            "end": "2025-02-01",
            "scope": "overwrite",
            "method": "construct_from_sources",
            "sources": [{"country": "GBR", "start": "2025-01-01", "end": "2025-02-01"}],
        },
    }

    result = build_auxiliary_fill_plan(
        rules,
        target_countries=TARGET_COUNTRIES,
        target_start=TARGET_START,
        target_end=TARGET_END,
    )

    assert result.empty
