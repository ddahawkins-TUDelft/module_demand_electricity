"""Tests for externally supplied demand profiles."""

import pandas as pd
import pytest
from cleaning.advanced.methods.external_profile import read_external_profile


def test_read_external_profile_reads_valid_csv(tmp_path):
    path = tmp_path / "profile.csv"

    path.write_text(
        "timestamp,demand\n2025-01-01T00:00:00Z,100.0\n2025-01-01T01:00:00Z,110.0\n",
        encoding="utf-8",
    )

    result = read_external_profile(path)

    expected = pd.Series(
        [100.0, 110.0],
        index=pd.DatetimeIndex(
            ["2025-01-01T00:00:00Z", "2025-01-01T01:00:00Z"], name="timestamp"
        ),
    )

    pd.testing.assert_series_equal(result, expected)


def test_read_external_profile_allows_sparse_timestamps(tmp_path):
    path = tmp_path / "profile.csv"

    path.write_text(
        "timestamp,demand\n2025-01-01T00:00:00Z,100.0\n2025-01-03T12:00:00Z,200.0\n",
        encoding="utf-8",
    )

    result = read_external_profile(path)

    assert len(result) == 2

    assert result.loc[pd.Timestamp("2025-01-01T00:00:00Z")] == 100.0

    assert result.loc[pd.Timestamp("2025-01-03T12:00:00Z")] == 200.0


def test_read_external_profile_rejects_duplicate_timestamps(tmp_path):
    path = tmp_path / "profile.csv"

    path.write_text(
        "timestamp,demand\n2025-01-01T00:00:00Z,100.0\n2025-01-01T00:00:00Z,110.0\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="timestamps must be unique"):
        read_external_profile(path)


def test_read_external_profile_rejects_non_hourly_timestamps(tmp_path):
    path = tmp_path / "profile.csv"

    path.write_text("timestamp,demand\n2025-01-01T00:30:00Z,100.0\n", encoding="utf-8")

    with pytest.raises(ValueError, match="whole hours"):
        read_external_profile(path)


def test_read_external_profile_rejects_non_numeric_values(tmp_path):
    path = tmp_path / "profile.csv"

    path.write_text(
        "timestamp,demand\n2025-01-01T00:00:00Z,not-a-number\n", encoding="utf-8"
    )

    with pytest.raises(ValueError, match="Unable to parse string"):
        read_external_profile(path)


def test_read_external_profile_rejects_wrong_columns(tmp_path):
    path = tmp_path / "profile.csv"

    path.write_text("datetime,demand\n2025-01-01T00:00:00Z,100.0\n", encoding="utf-8")

    with pytest.raises(ValueError, match="must contain exactly the columns"):
        read_external_profile(path)


def test_read_external_profile_rejects_extra_columns(tmp_path):
    path = tmp_path / "profile.csv"

    path.write_text(
        "timestamp,demand,comment\n2025-01-01T00:00:00Z,100.0,test\n", encoding="utf-8"
    )

    with pytest.raises(ValueError, match="must contain exactly the columns"):
        read_external_profile(path)


def test_read_external_profile_rejects_missing_values(tmp_path):
    path = tmp_path / "profile.csv"

    path.write_text("timestamp,demand\n2025-01-01T00:00:00Z,\n", encoding="utf-8")

    with pytest.raises(ValueError, match="must not be missing"):
        read_external_profile(path)
