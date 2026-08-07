"""Tests for the module configuration schema."""

from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPOSITORY_ROOT / "config" / "config.yaml"
SCHEMA_PATH = (
    REPOSITORY_ROOT
    / "workflow"
    / "internal"
    / "config.schema.yaml"
)


def test_default_config_matches_schema() -> None:
    """Validate the default user configuration against its schema."""
    with CONFIG_PATH.open(encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)

    with SCHEMA_PATH.open(encoding="utf-8") as schema_file:
        schema = yaml.safe_load(schema_file)

    validator = Draft202012Validator(schema)
    errors = sorted(
        validator.iter_errors(config),
        key=lambda error: list(error.absolute_path),
    )

    assert not errors, "\n".join(
        _format_validation_error(error)
        for error in errors
    )


def _format_validation_error(
    error: ValidationError,
) -> str:
    """Format one schema-validation error with its config location."""
    path = ".".join(
        str(part)
        for part in error.absolute_path
    )

    return f"{path or '<root>'}: {error.message}"

def test_advanced_auxiliary_basic_cleaning_can_be_disabled() -> None:
    """Allow auxiliary basic cleaning to be disabled."""
    with SCHEMA_PATH.open(encoding="utf-8") as schema_file:
        schema = yaml.safe_load(schema_file)

    config = {
        "temporal_scope": {
            "start": "2021-01-01",
            "end": "2022-01-01",
        },
        "load_sources": [
            "entsoe_api",
        ],
        "gap_filling": {
            "mode": "advanced",
            "basic": {
                "rules": [],
            },
            "advanced": {
                "auxiliary_data": {
                    "basic_cleaning": {
                        "enabled": False,
                    },
                },
                "overrides": {},
            },
        },
    }

    validator = Draft202012Validator(schema)
    errors = list(
        validator.iter_errors(config)
    )

    assert not errors, "\n".join(
        _format_validation_error(error)
        for error in errors
    )

def test_advanced_mode_allows_no_rules_or_overrides() -> None:
    """Allow advanced mode to run for diagnosis only."""
    with SCHEMA_PATH.open(encoding="utf-8") as schema_file:
        schema = yaml.safe_load(schema_file)

    config = {
        "temporal_scope": {
            "start": "2021-01-01",
            "end": "2022-01-01",
        },
        "load_sources": [
            "entsoe_api",
        ],
        "gap_filling": {
            "mode": "advanced",
            "basic": {
                "rules": [],
            },
            "advanced": {
                "auxiliary_data": {
                    "basic_cleaning": {
                        "enabled": True,
                    },
                },
                "overrides": {},
            },
        },
    }

    validator = Draft202012Validator(schema)
    errors = list(
        validator.iter_errors(config)
    )

    assert not errors, "\n".join(
        _format_validation_error(error)
        for error in errors
    )
