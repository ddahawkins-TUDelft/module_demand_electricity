"""Configuration for unit tests."""

import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parent.parent
WORKFLOW_SCRIPTS = MODULE_PATH / "workflow" / "scripts"

sys.path.insert(0, str(WORKFLOW_SCRIPTS))
