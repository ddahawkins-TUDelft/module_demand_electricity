"""Shared test fixtures."""

import os
import sys
from pathlib import Path
from urllib.request import urlretrieve

import pytest

MODULE_PATH = Path(__file__).resolve().parent.parent
WORKFLOW_SCRIPTS = MODULE_PATH / "workflow" / "scripts"

sys.path.insert(0, str(WORKFLOW_SCRIPTS))


TEST_FILES = {
    "EUROPE_S_C1_ADM1": "https://zenodo.org/records/20765043/files/EUROPE_S_C1_ADM1.parquet?download=1",
    "EUROPE_L_C34_ADM1": "https://zenodo.org/records/20765043/files/EUROPE_L_C34_ADM1.parquet?download=1",
}

TOKEN_ENTSOE = os.getenv("TOKEN_ENTSOE")
TOKEN_FILE = Path("resources/user/token_entsoe.txt")


@pytest.fixture(scope="module")
def module_path():
    """Parent directory of the project."""
    # If your module needs files in resources/user/, place automated downloads here.
    return MODULE_PATH


@pytest.fixture(scope="session")
def user_path() -> Path:
    """Download and unzip test files."""
    user_dir = Path("resources/user/")
    # If test file have been downloaded, assume everything is OK.
    # Otherwise, re-download.
    for name, file_url in TEST_FILES.items():
        file_path = user_dir / name / "shapes.parquet"
        if not file_path.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)
            urlretrieve(file_url, file_path)
    return user_dir


@pytest.fixture(scope="session")
def token_entsoe() -> Path:
    """Fixture to get token_entsoe.txt in CI.

    If an environment variable `TOKEN_ENTSOE` is set,
    and if token_entsoe.txt is not present or empty,
    write the token to the file.
    """
    if TOKEN_FILE.exists():
        if not TOKEN_FILE.read_text().strip() == "":
            return TOKEN_FILE
    elif TOKEN_ENTSOE:
        TOKEN_FILE.write_text(TOKEN_ENTSOE)
    else:
        raise ValueError(
            "`token_entsoe.txt` is missing or empty, and the environment variable TOKEN_ENTSOE is not set."
        )
    return TOKEN_FILE
