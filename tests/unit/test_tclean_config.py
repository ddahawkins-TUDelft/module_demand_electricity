"""Tests for the Modelblocks-to-T-Clean configuration adapter."""

import pandas as pd
from _tclean_config import (
    build_advanced_rules,
    build_all_constructed_source_periods,
    build_basic_rules,
    build_scaling_source_periods,
    build_time_grid,
)
from tclean import TimeGrid


def test_build_time_grid_translates_temporal_scope() -> None:
    """Test build time grid accepts temporal scope."""
    grid = build_time_grid(
        {
            "start": "2020-01-01T00:30:00Z",
            "end": "2020-01-01T03:30:00Z",
            "frequency": "1h",
        }
    )
    assert isinstance(grid, TimeGrid)
    assert grid.start == pd.Timestamp("2020-01-01T00:30:00Z")
    assert grid.end == pd.Timestamp("2020-01-01T03:30:00Z")
    assert grid.frequency == pd.Timedelta("1h")


def test_build_basic_rules_returns_no_rules_when_mode_is_off() -> None:
    """Test basic rules returns nothing when disabled."""
    config = {"mode": "off", "basic": {"rules": []}}
    assert build_basic_rules(config) == []


def test_build_basic_rules_preserves_configured_rule_order() -> None:
    """Test basic rules preserves order."""
    rules = [
        {"name": "first", "method": "linear_interpolation", "max_gap": "2h"},
        {
            "name": "second",
            "method": "copy_periods",
            "max_gap": "4h",
            "source_offsets": ["-24h"],
        },
    ]
    config = {"mode": "basic", "basic": {"rules": rules}}
    assert build_basic_rules(config) == rules


def test_build_advanced_rules_returns_canonical_columns_when_empty() -> None:
    """Test advanced returns column headers even when empty."""
    config = {
        "mode": "advanced",
        "basic": {"rules": []},
        "advanced": {"sources": {}, "rules": []},
    }
    result = build_advanced_rules(config)
    assert result.empty
    assert list(result.columns) == [
        "rule_name",
        "method",
        "source",
        "context",
        "start",
        "end",
        "scope",
    ]

def test_build_scaling_source_periods_builds_match_total_periods() -> None:
    """Check match_total scaling periods are translated for T-Clean."""
    definition = {
        "method": "construct_from_sources",
        "periods": [
            {
                "country": "GBR",
                "start": "2024-01-01",
                "end": "2024-02-01",
                "weight": 1,
            }
        ],
        "scaling": {
            "method": "match_total",
            "periods": [
                {
                    "country": "ALB",
                    "start": "2023-01-01",
                    "end": "2023-02-01",
                    "weight": 1,
                }
            ],
        },
    }

    result = build_scaling_source_periods(definition)

    assert result is not None
    assert result["context"].tolist() == ["ALB"]
    assert result["weight"].tolist() == [1]
    assert result["start"].tolist() == [
        pd.Timestamp("2023-01-01", tz="UTC")
    ]
    assert result["end"].tolist() == [
        pd.Timestamp("2023-02-01", tz="UTC")
    ]


def test_build_scaling_source_periods_returns_none_for_normalise_mean() -> None:
    """Check mean normalisation requires no auxiliary scaling periods."""
    definition = {
        "method": "construct_from_sources",
        "periods": [],
        "scaling": {"method": "normalise_mean"},
    }

    assert build_scaling_source_periods(definition) is None


def test_build_scaling_source_periods_returns_none_for_normalise_max() -> None:
    """Check maximum normalisation requires no auxiliary scaling periods."""
    definition = {
        "method": "construct_from_sources",
        "periods": [],
        "scaling": {"method": "normalise_max"},
    }

    assert build_scaling_source_periods(definition) is None

def test_normalisation_scaling_does_not_add_auxiliary_periods() -> None:
    """Check normalisation methods do not add scaling acquisition periods."""
    gap_filling_config = {
        "mode": "advanced",
        "advanced": {
            "sources": {
                "mean_source": {
                    "method": "construct_from_sources",
                    "periods": [
                        {
                            "country": "GBR",
                            "start": "2024-01-01",
                            "end": "2024-02-01",
                            "weight": 1,
                        }
                    ],
                    "scaling": {"method": "normalise_mean"},
                },
                "max_source": {
                    "method": "construct_from_sources",
                    "periods": [
                        {
                            "country": "FRA",
                            "start": "2024-01-01",
                            "end": "2024-02-01",
                            "weight": 1,
                        }
                    ],
                    "scaling": {"method": "normalise_max"},
                },
            }
        },
    }

    result = build_all_constructed_source_periods(gap_filling_config)

    assert set(result) == {"mean_source", "max_source"}
    assert result["mean_source"]["context"].tolist() == ["GBR"]
    assert result["max_source"]["context"].tolist() == ["FRA"]

def test_match_total_scaling_adds_auxiliary_periods() -> None:
    """Check match_total adds reference periods to auxiliary acquisition."""
    gap_filling_config = {
        "mode": "advanced",
        "advanced": {
            "sources": {
                "scaled_source": {
                    "method": "construct_from_sources",
                    "periods": [
                        {
                            "country": "GBR",
                            "start": "2024-01-01",
                            "end": "2024-02-01",
                            "weight": 1,
                        }
                    ],
                    "scaling": {
                        "method": "match_total",
                        "periods": [
                            {
                                "country": "ALB",
                                "start": "2023-01-01",
                                "end": "2023-02-01",
                                "weight": 1,
                            }
                        ],
                    },
                }
            }
        },
    }

    result = build_all_constructed_source_periods(gap_filling_config)

    assert set(result) == {"scaled_source"}
    assert result["scaled_source"]["context"].tolist() == ["GBR", "ALB"]
