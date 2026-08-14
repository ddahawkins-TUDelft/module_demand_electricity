"""Tests for semantic configuration validation."""

import pytest
from common.config_validation import validate_config_semantics


def _config() -> dict:
    """Return a structurally valid configuration for semantic validation."""
    return {
        "temporal_scope": {"start": "2022-01-01", "end": "2023-01-01"},
        "load_sources": ["entsoe_api", "neso"],
        "gap_filling": {"basic": {"rules": []}, "advanced": {"overrides": {}}},
    }


def test_accepts_valid_config() -> None:
    """Accept a configuration with valid semantic relationships."""
    validate_config_semantics(_config())


def test_rejects_empty_temporal_scope() -> None:
    """Reject a temporal scope whose start and end are identical."""
    config = _config()
    config["temporal_scope"]["end"] = config["temporal_scope"]["start"]

    with pytest.raises(ValueError, match="Temporal scope"):
        validate_config_semantics(config)


def test_rejects_reversed_override_period() -> None:
    """Reject an advanced override whose end precedes its start."""
    config = _config()
    config["gap_filling"]["advanced"]["overrides"] = {
        "bad_period": {
            "country": "ALB",
            "start": "2024-02-01",
            "end": "2024-01-01",
            "scope": "fill_gaps",
            "method": "leave_missing",
        }
    }

    with pytest.raises(ValueError, match="bad_period"):
        validate_config_semantics(config)


def test_rejects_basic_rule_name_reserved_for_observed_source() -> None:
    """Reject a basic rule name reserved for observed-source provenance."""
    config = _config()
    config["gap_filling"]["basic"]["rules"] = [
        {
            "name": "observed_entsoe_api",
            "method": "linear_interpolation",
            "max_gap": "3h",
        }
    ]

    with pytest.raises(ValueError, match="conflict with reserved"):
        validate_config_semantics(config)


def test_rejects_advanced_rule_name_missing() -> None:
    """Reject an advanced override using the reserved missing provenance name."""
    config = _config()
    config["gap_filling"]["advanced"]["overrides"] = {
        "missing": {
            "country": "ALB",
            "start": "2022-03-01",
            "end": "2022-04-01",
            "scope": "fill_gaps",
            "method": "leave_missing",
        }
    }

    with pytest.raises(ValueError, match="conflict with reserved"):
        validate_config_semantics(config)
