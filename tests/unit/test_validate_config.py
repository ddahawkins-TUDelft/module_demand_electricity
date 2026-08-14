"""Tests for semantic configuration validation."""

import pytest
from common.config_validation import validate_config_semantics


def _config() -> dict:
    return {
        "temporal_scope": {
            "start": "2022-01-01",
            "end": "2023-01-01",
        },
        "gap_filling": {
            "advanced": {
                "overrides": {},
            }
        },
    }


def test_accepts_valid_config() -> None:
    """Accept a configuration with valid temporal relationships."""
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
