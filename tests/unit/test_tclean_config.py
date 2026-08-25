"""Tests for the Modelblocks-to-T-Clean configuration adapter."""

import pandas as pd
from _tclean_config import build_advanced_rules, build_basic_rules, build_time_grid
from tclean import TimeGrid


def test_build_time_grid_translates_temporal_scope() -> None:
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
    config = {"mode": "off", "basic": {"rules": []}}
    assert build_basic_rules(config) == []


def test_build_basic_rules_preserves_configured_rule_order() -> None:
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
