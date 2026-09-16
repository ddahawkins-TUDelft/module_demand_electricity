"""Shared test fixtures."""

import os
from pathlib import Path
from urllib.request import urlretrieve

import pytest

MODULE_PATH = Path(__file__).resolve().parent.parent

TEST_FILES = {
    "EUROPE_S_C1_ADM1": "https://zenodo.org/records/20765043/files/EUROPE_S_C1_ADM1.parquet?download=1",
    "EUROPE_L_C34_ADM1": "https://zenodo.org/records/20765043/files/EUROPE_L_C34_ADM1.parquet?download=1",
}


@pytest.fixture(scope="module")
def module_path():
    """Parent directory of the project."""
    # If your module needs files in resources/user/, place automated downloads here.
    return MODULE_PATH


def _download_test_file(user_path: Path, name: str) -> Path:
    """Download a test shapes file if it is not already available."""
    file_path = user_path / name / "shapes.parquet"

    if file_path.exists():
        return file_path

    file_path.parent.mkdir(parents=True, exist_ok=True)

    partial_path = file_path.with_suffix(".parquet.part")
    partial_path.unlink(missing_ok=True)

    try:
        urlretrieve(TEST_FILES[name], partial_path)
        partial_path.replace(file_path)
    except Exception:
        partial_path.unlink(missing_ok=True)
        raise

    return file_path


@pytest.fixture(scope="session")
def user_path() -> Path:
    """Path to user resources used during testing."""
    user_dir = Path("resources/user/")
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


@pytest.fixture(scope="session")
def europe_small_shapes(user_path: Path) -> Path:
    """Small European shapes file used by the integration test."""
    return _download_test_file(user_path, "EUROPE_S_C1_ADM1")


@pytest.fixture(scope="session")
def europe_large_shapes(user_path: Path) -> Path:
    """Large European shapes file used by the local end-to-end test."""
    return _download_test_file(user_path, "EUROPE_L_C34_ADM1")


@pytest.fixture(scope="session")
def token_entsoe() -> Path:
    """Fixture to get token_entsoe.txt in CI.

    If an environment variable `TOKEN_ENTSOE` is set,
    and if token_entsoe.txt is not present or empty,
    write the token to the file.
    """
    token_entsoe = os.getenv("TOKEN_ENTSOE")
    token_file = Path("resources/user/token_entsoe.txt")

    if token_file.exists() and token_file.read_text().strip():
        return token_file

    if token_entsoe:
        token_file.parent.mkdir(parents=True, exist_ok=True)
        token_file.write_text(token_entsoe)
        return token_file

    raise ValueError(
        "`token_entsoe.txt` is missing or empty, and the environment variable "
        "`TOKEN_ENTSOE` is not set."
    )
