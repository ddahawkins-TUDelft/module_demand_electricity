"""Tests for applying advanced auxiliary-fill rules."""

import pandas as pd
import pytest

from cleaning.advanced.apply import (
    apply_auxiliary_fill_rule,
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
            rule_name="external_albania",
            rule=rule,
        )


def test_construct_from_sources_dispatches_to_placeholder() -> None:
    rule = {
        "method": "construct_from_sources",
    }

    with pytest.raises(
        NotImplementedError,
        match="construct_from_sources",
    ):
        apply_auxiliary_fill_rule(
            _load(),
            rule_name="construct_albania",
            rule=rule,
        )


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
            rule_name="review_albania",
            rule=rule,
        )


def test_leave_missing_returns_unchanged_copy() -> None:
    load = _load()

    result = apply_auxiliary_fill_rule(
        load,
        rule_name="leave_albania_missing",
        rule={
            "method": "leave_missing",
        },
    )

    pd.testing.assert_frame_equal(
        result,
        load,
    )

    assert result is not load


def test_rejects_unsupported_method() -> None:
    with pytest.raises(
        ValueError,
        match="Unsupported advanced-fill method",
    ):
        apply_auxiliary_fill_rule(
            _load(),
            rule_name="invalid_rule",
            rule={
                "method": "unknown",
            },
        )
