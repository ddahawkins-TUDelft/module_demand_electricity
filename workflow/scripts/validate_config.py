"""Validate semantic constraints in the module configuration."""

import json
from pathlib import Path

from common.config_validation import validate_config_semantics

validation_config = snakemake.params.validation_config

validate_config_semantics(validation_config)

Path(snakemake.output[0]).write_text(
    json.dumps({"valid": True}, indent=2) + "\n",
    encoding="utf-8",
)