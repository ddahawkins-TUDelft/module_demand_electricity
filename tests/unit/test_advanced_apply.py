"""Tests for applying advanced auxiliary-fill rules."""

import pandas as pd
import pytest
from cleaning.advanced.apply import (
    apply_auxiliary_fill_rule,
    apply_auxiliary_fill_rules,
)


def _load() -> pd.DataFrame:
    index = pd.date_range(
        "2021-01-01",
        periods=3,
        freq="h",
        tz="UTC",
    )

    return pd.DataFrame(
        {
            "ALB": [
                1.0,
                pd.NA,
                3.0,
            ],
        },
        index=index,
        dtype="Float64",
    )


def _cleaning_method() -> pd.DataFrame:
    index = pd.date_range(
        "2021-01-01",
        periods=3,
        freq="h",
        tz="UTC",
    )

    return pd.DataFrame(
        {
            "ALB": [
                "observed_entsoe_api",
                "missing",
                "observed_entsoe_api",
            ],
        },
        index=index,
    )



def test_external_profile_execution_is_not_implemented() -> None:
    rule = {
        "method": "external_profile",
    }

    with pytest.raises(
        NotImplementedError,
        match="external_profile",
    ):
        apply_auxiliary_fill_rule(
            _load(),
            _cleaning_method(),
            rule_name="external_albania",
            rule=rule,
        )


def test_construct_from_sources_requires_profile() -> None:
    rule = {
        "method": "construct_from_sources",
    }

    with pytest.raises(
        ValueError,
        match="requires a constructed auxiliary profile",
    ):
        apply_auxiliary_fill_rule(
            _load(),
            _cleaning_method(),
            rule_name="construct_albania",
            rule=rule,
        )


def test_construct_from_sources_fills_gaps() -> None:
    load = _load()
    cleaning_method = _cleaning_method()

    profile = pd.Series(
        [
            10.0,
            20.0,
            30.0,
        ],
        index=load.index,
    )

    rule = {
        "method": "construct_from_sources",
        "country": "ALB",
        "start": "2021-01-01T00:00:00+00:00",
        "end": "2021-01-01T03:00:00+00:00",
        "scope": "fill_gaps_within_period",
    }

    filled, methods = apply_auxiliary_fill_rule(
        load,
        cleaning_method,
        rule_name="construct_albania",
        rule=rule,
        profile=profile,
    )

    assert filled["ALB"].tolist() == [
        1.0,
        20.0,
        3.0,
    ]

    assert methods["ALB"].tolist() == [
        "observed_entsoe_api",
        "construct_albania",
        "observed_entsoe_api",
    ]


def test_construct_from_sources_overwrites_entire_period() -> None:
    load = _load()
    cleaning_method = _cleaning_method()

    profile = pd.Series(
        [
            10.0,
            20.0,
            30.0,
        ],
        index=load.index,
    )

    rule = {
        "method": "construct_from_sources",
        "country": "ALB",
        "start": "2021-01-01T00:00:00+00:00",
        "end": "2021-01-01T03:00:00+00:00",
        "scope": "overwrite_entire_period",
    }

    filled, methods = apply_auxiliary_fill_rule(
        load,
        cleaning_method,
        rule_name="construct_albania",
        rule=rule,
        profile=profile,
    )

    assert filled["ALB"].tolist() == [
        10.0,
        20.0,
        30.0,
    ]

    assert methods["ALB"].tolist() == [
        "construct_albania",
        "construct_albania",
        "construct_albania",
    ]


def test_manual_review_cannot_be_applied_automatically() -> None:
    rule = {
        "method": "manual_review",
    }

    with pytest.raises(
        ValueError,
        match="requires manual review",
    ):
        apply_auxiliary_fill_rule(
            _load(),
            _cleaning_method(),
            rule_name="review_albania",
            rule=rule,
        )


def test_leave_missing_returns_unchanged_copies() -> None:
    load = _load()
    cleaning_method = _cleaning_method()

    result_load, result_method = apply_auxiliary_fill_rule(
        load,
        cleaning_method,
        rule_name="leave_albania_missing",
        rule={
            "method": "leave_missing",
        },
    )

    pd.testing.assert_frame_equal(
        result_load,
        load,
    )
    pd.testing.assert_frame_equal(
        result_method,
        cleaning_method,
    )

    assert result_load is not load
    assert result_method is not cleaning_method


def test_rejects_unsupported_method() -> None:
    with pytest.raises(
        ValueError,
        match="Unsupported advanced-fill method",
    ):
        apply_auxiliary_fill_rule(
            _load(),
            _cleaning_method(),
            rule_name="invalid_rule",
            rule={
                "method": "unknown",
            },
        )


def test_apply_auxiliary_fill_rules_applies_rules_in_order() -> None:
    load = _load()
    cleaning_method = _cleaning_method()

    first_profile = pd.Series(
        [
            10.0,
            20.0,
            30.0,
        ],
        index=load.index,
    )

    second_profile = pd.Series(
        [
            100.0,
            200.0,
            300.0,
        ],
        index=load.index,
    )

    overrides = {
        "fill_gaps": {
            "method": "construct_from_sources",
            "country": "ALB",
            "start": "2021-01-01T00:00:00+00:00",
            "end": "2021-01-01T03:00:00+00:00",
            "scope": "fill_gaps_within_period",
        },
        "overwrite": {
            "method": "construct_from_sources",
            "country": "ALB",
            "start": "2021-01-01T00:00:00+00:00",
            "end": "2021-01-01T03:00:00+00:00",
            "scope": "overwrite_entire_period",
        },
    }

    profiles = {
        "fill_gaps": first_profile,
        "overwrite": second_profile,
    }

    filled, methods = apply_auxiliary_fill_rules(
        load,
        cleaning_method,
        overrides=overrides,
        profiles=profiles,
    )

    assert filled["ALB"].tolist() == [
        100.0,
        200.0,
        300.0,
    ]

    assert methods["ALB"].tolist() == [
        "overwrite",
        "overwrite",
        "overwrite",
    ]

def test_apply_auxiliary_fill_rules_with_no_overrides_returns_copies() -> None:
    load = _load()
    cleaning_method = _cleaning_method()

    filled, methods = apply_auxiliary_fill_rules(
        load,
        cleaning_method,
        overrides={},
        profiles={},
    )

    pd.testing.assert_frame_equal(
        filled,
        load,
    )
    pd.testing.assert_frame_equal(
        methods,
        cleaning_method,
    )

    assert filled is not load
    assert methods is not cleaning_method
