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