"""Tests for applying advanced auxiliary-fill rules."""

import pandas as pd
import pytest
from cleaning.advanced.apply import (
    apply_auxiliary_fill_rule,
    apply_auxiliary_fill_rules,
)


def _load() -> pd.DataFrame:
    index = pd.date_range("2021-01-01", periods=3, freq="h", tz="UTC")

    return pd.DataFrame({"ALB": [1.0, pd.NA, 3.0]}, index=index, dtype="Float64")


def _cleaning_method() -> pd.DataFrame:
    index = pd.date_range("2021-01-01", periods=3, freq="h", tz="UTC")

    return pd.DataFrame(
        {"ALB": ["observed_entsoe_api", "missing", "observed_entsoe_api"]}, index=index
    )


def test_construct_from_sources_requires_profile() -> None:
    """Test construct from sources requires profile."""
    rule = {"method": "construct_from_sources"}

    with pytest.raises(ValueError, match="requires a constructed auxiliary profile"):
        apply_auxiliary_fill_rule(
            _load(), _cleaning_method(), rule_name="construct_albania", rule=rule
        )


def test_construct_from_sources_fills_gaps() -> None:
    """Test construct from sources fills gaps."""
    load = _load()
    cleaning_method = _cleaning_method()

    profile = pd.Series([10.0, 20.0, 30.0], index=load.index)

    rule = {
        "method": "construct_from_sources",
        "country": "ALB",
        "start": "2021-01-01T00:00:00+00:00",
        "end": "2021-01-01T03:00:00+00:00",
        "scope": "fill_gaps",
    }

    filled, methods = apply_auxiliary_fill_rule(
        load, cleaning_method, rule_name="construct_albania", rule=rule, profile=profile
    )

    assert filled["ALB"].tolist() == [1.0, 20.0, 3.0]

    assert methods["ALB"].tolist() == [
        "observed_entsoe_api",
        "construct_albania",
        "observed_entsoe_api",
    ]


def test_construct_from_sources_overwrites_entire_period() -> None:
    """Test construct from sources overwrites entire period."""
    load = _load()
    cleaning_method = _cleaning_method()

    profile = pd.Series([10.0, 20.0, 30.0], index=load.index)

    rule = {
        "method": "construct_from_sources",
        "country": "ALB",
        "start": "2021-01-01T00:00:00+00:00",
        "end": "2021-01-01T03:00:00+00:00",
        "scope": "overwrite",
    }

    filled, methods = apply_auxiliary_fill_rule(
        load, cleaning_method, rule_name="construct_albania", rule=rule, profile=profile
    )

    assert filled["ALB"].tolist() == [10.0, 20.0, 30.0]

    assert methods["ALB"].tolist() == [
        "construct_albania",
        "construct_albania",
        "construct_albania",
    ]


def test_leave_missing_returns_unchanged_copies() -> None:
    """Test leaving missing does nothing."""
    load = _load()
    cleaning_method = _cleaning_method()

    result_load, result_method = apply_auxiliary_fill_rule(
        load,
        cleaning_method,
        rule_name="leave_albania_missing",
        rule={"method": "leave_missing"},
    )

    pd.testing.assert_frame_equal(result_load, load)
    pd.testing.assert_frame_equal(result_method, cleaning_method)

    assert result_load is not load
    assert result_method is not cleaning_method


def test_rejects_unsupported_method() -> None:
    """Test unsupported methods."""
    with pytest.raises(ValueError, match="Unsupported advanced-fill method"):
        apply_auxiliary_fill_rule(
            _load(),
            _cleaning_method(),
            rule_name="invalid_rule",
            rule={"method": "unknown"},
        )


def test_apply_auxiliary_fill_rules_applies_rules_in_order() -> None:
    """Test order."""
    load = _load()
    cleaning_method = _cleaning_method()

    first_profile = pd.Series([10.0, 20.0, 30.0], index=load.index)

    second_profile = pd.Series([100.0, 200.0, 300.0], index=load.index)

    overrides = {
        "fill_gaps": {
            "method": "construct_from_sources",
            "country": "ALB",
            "start": "2021-01-01T00:00:00+00:00",
            "end": "2021-01-01T03:00:00+00:00",
            "scope": "fill_gaps",
        },
        "overwrite": {
            "method": "construct_from_sources",
            "country": "ALB",
            "start": "2021-01-01T00:00:00+00:00",
            "end": "2021-01-01T03:00:00+00:00",
            "scope": "overwrite",
        },
    }

    profiles = {"fill_gaps": first_profile, "overwrite": second_profile}

    filled, methods = apply_auxiliary_fill_rules(
        load,
        cleaning_method,
        overrides=overrides,
        constructed_profiles=profiles,
        external_profiles={},
    )

    assert filled["ALB"].tolist() == [100.0, 200.0, 300.0]

    assert methods["ALB"].tolist() == ["overwrite", "overwrite", "overwrite"]


def test_apply_auxiliary_fill_rules_with_no_overrides_returns_copies() -> None:
    """Test fill returns copy without overrides."""
    load = _load()
    cleaning_method = _cleaning_method()

    filled, methods = apply_auxiliary_fill_rules(
        load,
        cleaning_method,
        overrides={},
        constructed_profiles={},
        external_profiles={},
    )

    pd.testing.assert_frame_equal(filled, load)
    pd.testing.assert_frame_equal(methods, cleaning_method)

    assert filled is not load
    assert methods is not cleaning_method


def test_overwrite_replaces_existing_values() -> None:
    """Test overwrite."""
    index = pd.date_range("2022-01-01", periods=4, freq="h", tz="UTC")

    load = pd.DataFrame({"ALB": [10.0, 20.0, 30.0, 40.0]}, index=index)

    cleaning_method = pd.DataFrame({"ALB": ["observed_entsoe_api"] * 4}, index=index)

    profile = pd.Series([100.0, 200.0], index=index[1:3], name="ALB")

    overrides = {
        "replace_albania": {
            "country": "ALB",
            "start": index[1],
            "end": index[3],
            "scope": "overwrite",
            "method": "construct_from_sources",
            "sources": [
                {
                    "country": "GBR",
                    "start": "2024-01-01",
                    "end": "2024-01-01 02:00",
                    "weight": 1,
                }
            ],
        }
    }

    filled, methods = apply_auxiliary_fill_rules(
        load,
        cleaning_method,
        overrides=overrides,
        constructed_profiles={"replace_albania": profile},
        external_profiles={},
    )

    assert filled["ALB"].tolist() == [10.0, 100.0, 200.0, 40.0]

    assert methods["ALB"].tolist() == [
        "observed_entsoe_api",
        "replace_albania",
        "replace_albania",
        "observed_entsoe_api",
    ]


def test_fill_gaps_preserves_existing_values() -> None:
    """Test fill doesnt overwrite."""
    index = pd.date_range("2022-01-01", periods=4, freq="h", tz="UTC")

    load = pd.DataFrame({"ALB": [10.0, float("nan"), 30.0, 40.0]}, index=index)

    cleaning_method = pd.DataFrame(
        {
            "ALB": [
                "observed_entsoe_api",
                "missing",
                "observed_entsoe_api",
                "observed_entsoe_api",
            ]
        },
        index=index,
    )

    profile = pd.Series([100.0, 200.0], index=index[1:3], name="ALB")

    overrides = {
        "fill_albania": {
            "country": "ALB",
            "start": index[1],
            "end": index[3],
            "scope": "fill_gaps",
            "method": "construct_from_sources",
            "sources": [
                {
                    "country": "GBR",
                    "start": "2024-01-01",
                    "end": "2024-01-01 02:00",
                    "weight": 1,
                }
            ],
        }
    }

    filled, methods = apply_auxiliary_fill_rules(
        load,
        cleaning_method,
        overrides=overrides,
        constructed_profiles={"fill_albania": profile},
        external_profiles={},
    )

    assert filled["ALB"].tolist() == [10.0, 100.0, 30.0, 40.0]

    assert methods["ALB"].tolist() == [
        "observed_entsoe_api",
        "fill_albania",
        "observed_entsoe_api",
        "observed_entsoe_api",
    ]


def test_external_profile_fill_gaps_only_replaces_missing_values():
    """Test external profile fills gaps."""
    index = pd.date_range("2025-01-01", periods=4, freq="h", tz="UTC")

    load = pd.DataFrame({"ALB": [100.0, None, 300.0, None]}, index=index)

    cleaning_method = pd.DataFrame(None, index=index, columns=["ALB"], dtype=object)

    profile = pd.Series([110.0, 220.0, 330.0, 440.0], index=index)

    overrides = {
        "external_albania": {
            "method": "external_profile",
            "country": "ALB",
            "start": "2025-01-01T00:00:00Z",
            "end": "2025-01-01T04:00:00Z",
            "scope": "fill_gaps",
        }
    }

    filled, methods = apply_auxiliary_fill_rules(
        load,
        cleaning_method,
        overrides=overrides,
        constructed_profiles={},
        external_profiles={"external_albania": profile},
    )

    expected = pd.Series([100.0, 220.0, 300.0, 440.0], index=index, name="ALB")

    pd.testing.assert_series_equal(filled["ALB"], expected)

    assert pd.isna(methods.loc[index[0], "ALB"])
    assert methods.loc[index[1], "ALB"] == "external_albania"
    assert pd.isna(methods.loc[index[2], "ALB"])
    assert methods.loc[index[3], "ALB"] == "external_albania"


def test_external_profile_overwrite_replaces_supplied_values():
    """Test external overwrites."""
    index = pd.date_range("2025-01-01", periods=4, freq="h", tz="UTC")

    load = pd.DataFrame({"ALB": [100.0, 200.0, 300.0, 400.0]}, index=index)

    cleaning_method = pd.DataFrame(None, index=index, columns=["ALB"], dtype=object)

    profile = pd.Series([110.0, 220.0, 330.0, 440.0], index=index)

    overrides = {
        "external_albania": {
            "method": "external_profile",
            "country": "ALB",
            "start": "2025-01-01T00:00:00Z",
            "end": "2025-01-01T04:00:00Z",
            "scope": "overwrite",
        }
    }

    filled, methods = apply_auxiliary_fill_rules(
        load,
        cleaning_method,
        overrides=overrides,
        constructed_profiles={},
        external_profiles={"external_albania": profile},
    )

    expected = pd.Series([110.0, 220.0, 330.0, 440.0], index=index, name="ALB")

    pd.testing.assert_series_equal(filled["ALB"], expected)

    assert (methods["ALB"] == "external_albania").all()


def test_external_profile_overwrite_only_replaces_supplied_timestamps():
    """Test overwrite domains."""
    index = pd.date_range("2025-01-01", periods=5, freq="h", tz="UTC")

    load = pd.DataFrame({"ALB": [100.0, 200.0, 300.0, 400.0, 500.0]}, index=index)

    cleaning_method = pd.DataFrame(None, index=index, columns=["ALB"], dtype=object)

    profile = pd.Series([2200.0, 4400.0], index=[index[1], index[3]])

    overrides = {
        "external_albania": {
            "method": "external_profile",
            "country": "ALB",
            "start": "2025-01-01T00:00:00Z",
            "end": "2025-01-01T05:00:00Z",
            "scope": "overwrite",
        }
    }

    filled, methods = apply_auxiliary_fill_rules(
        load,
        cleaning_method,
        overrides=overrides,
        constructed_profiles={},
        external_profiles={"external_albania": profile},
    )

    expected = pd.Series([100.0, 2200.0, 300.0, 4400.0, 500.0], index=index, name="ALB")

    pd.testing.assert_series_equal(filled["ALB"], expected)

    assert methods.loc[index[1], "ALB"] == "external_albania"
    assert methods.loc[index[3], "ALB"] == "external_albania"

    assert pd.isna(methods.loc[index[0], "ALB"])
    assert pd.isna(methods.loc[index[2], "ALB"])
    assert pd.isna(methods.loc[index[4], "ALB"])


def test_external_profile_ignores_values_outside_rule_period():
    """Test overwrite restricts domain."""
    index = pd.date_range("2025-01-01", periods=5, freq="h", tz="UTC")

    load = pd.DataFrame({"ALB": [100.0, 200.0, 300.0, 400.0, 500.0]}, index=index)

    cleaning_method = pd.DataFrame(None, index=index, columns=["ALB"], dtype=object)

    profile = pd.Series([1000.0, 2000.0, 3000.0, 4000.0, 5000.0], index=index)

    overrides = {
        "external_albania": {
            "method": "external_profile",
            "country": "ALB",
            "start": "2025-01-01T01:00:00Z",
            "end": "2025-01-01T04:00:00Z",
            "scope": "overwrite",
        }
    }

    filled, _ = apply_auxiliary_fill_rules(
        load,
        cleaning_method,
        overrides=overrides,
        constructed_profiles={},
        external_profiles={"external_albania": profile},
    )

    expected = pd.Series(
        [100.0, 2000.0, 3000.0, 4000.0, 500.0], index=index, name="ALB"
    )

    pd.testing.assert_series_equal(filled["ALB"], expected)


def test_external_profile_requires_profile():
    """Test external requires profile."""
    index = pd.date_range("2025-01-01", periods=2, freq="h", tz="UTC")

    load = pd.DataFrame({"ALB": [None, None]}, index=index)

    cleaning_method = pd.DataFrame(None, index=index, columns=["ALB"], dtype=object)

    overrides = {
        "external_albania": {
            "method": "external_profile",
            "country": "ALB",
            "start": "2025-01-01T00:00:00Z",
            "end": "2025-01-01T02:00:00Z",
            "scope": "fill_gaps",
        }
    }

    with pytest.raises(ValueError, match="requires an external profile"):
        apply_auxiliary_fill_rules(
            load,
            cleaning_method,
            overrides=overrides,
            constructed_profiles={},
            external_profiles={},
        )
