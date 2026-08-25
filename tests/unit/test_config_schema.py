"""Tests for the module configuration schema."""

from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPOSITORY_ROOT / "config" / "config.yaml"
SCHEMA_PATH = REPOSITORY_ROOT / "workflow" / "internal" / "config.schema.yaml"


def _format_validation_error(error: ValidationError) -> str:
    path = ".".join(str(part) for part in error.absolute_path)
    return f"{path or '<root>'}: {error.message}"


def _validate(config: dict) -> list[ValidationError]:
    with SCHEMA_PATH.open(encoding="utf-8") as schema_file:
        schema = yaml.safe_load(schema_file)
    return list(Draft202012Validator(schema).iter_errors(config))


def test_default_config_matches_schema() -> None:
    with CONFIG_PATH.open(encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)
    errors = _validate(config)
    assert not errors, "\n".join(_format_validation_error(error) for error in errors)


def test_advanced_mode_allows_no_sources_or_rules() -> None:
    config = {
        "temporal_scope": {
            "start": "2021-01-01",
            "end": "2022-01-01",
            "frequency": "1h",
        },
        "load_sources": ["entsoe"],
        "gap_filling": {
            "mode": "advanced",
            "basic": {"rules": []},
            "advanced": {
                "auxiliary_data": {"basic_cleaning": {"enabled": True}},
                "sources": {},
                "rules": [],
            },
        },
    }
    errors = _validate(config)
    assert not errors, "\n".join(_format_validation_error(error) for error in errors)
