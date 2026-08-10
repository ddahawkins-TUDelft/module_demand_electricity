"""Apply validated advanced auxiliary-fill rules."""

from collections.abc import Mapping
from typing import Any

import pandas as pd
from common.time import as_utc_timestamp

from cleaning.advanced.methods.construct_from_sources import (
    METHOD_NAME as CONSTRUCT_FROM_SOURCES,
)
from cleaning.advanced.methods.external_profile import METHOD_NAME as EXTERNAL_PROFILE

MANUAL_REVIEW = "manual_review"
LEAVE_MISSING = "leave_missing"


def apply_auxiliary_fill_rule(
    load: pd.DataFrame,
    cleaning_method: pd.DataFrame,
    *,
    rule_name: str,
    rule: Mapping[str, Any],
    profile: pd.Series | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply one validated advanced-fill rule."""
    method = rule["method"]

    if method == CONSTRUCT_FROM_SOURCES:
        if profile is None:
            raise ValueError(
                f"Advanced-fill rule {rule_name!r} requires "
                "a constructed auxiliary profile."
            )

        return apply_constructed_profile(
            load,
            cleaning_method,
            profile,
            country=rule["country"],
            start=as_utc_timestamp(rule["start"]),
            end=as_utc_timestamp(rule["end"]),
            scope=rule["scope"],
            rule_name=rule_name,
        )

    if method == EXTERNAL_PROFILE:
        raise NotImplementedError(
            "Advanced-fill method 'external_profile' is recognized "
            "but has not yet been implemented."
        )

    if method == MANUAL_REVIEW:
        raise ValueError(
            f"Advanced-fill rule {rule_name!r} requires manual "
            "review and cannot be applied automatically."
        )

    if method == LEAVE_MISSING:
        return load.copy(), cleaning_method.copy()

    raise ValueError(
        f"Unsupported advanced-fill method {method!r}."
    )



def apply_constructed_profile(
    load: pd.DataFrame,
    cleaning_method: pd.DataFrame,
    profile: pd.Series,
    *,
    country: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
    scope: str,
    rule_name: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply a constructed auxiliary profile to the target demand."""
    filled = load.copy()
    methods = cleaning_method.copy()

    target_index = filled.index[
        (filled.index >= start)
        & (filled.index < end)
    ]

    if not profile.index.equals(target_index):
        raise ValueError(
            "Constructed profile index must exactly match "
            "the target period."
        )

    if country not in filled.columns:
        raise ValueError(
            f"Target country {country!r} is not present in load data."
        )

    if scope == "fill_gaps_within_period":
        replace_mask = filled.loc[
            target_index,
            country,
        ].isna()

    elif scope == "overwrite_entire_period":
        replace_mask = pd.Series(
            True,
            index=target_index,
        )

    else:
        raise ValueError(
            f"Unsupported advanced fill scope: {scope!r}"
        )

    replacement_index = target_index[
        replace_mask.to_numpy()
    ]

    filled.loc[
        replacement_index,
        country,
    ] = profile.loc[
        replacement_index
    ]

    methods.loc[
        replacement_index,
        country,
    ] = rule_name

    return filled, methods

def apply_auxiliary_fill_rules(
    load: pd.DataFrame,
    cleaning_method: pd.DataFrame,
    *,
    overrides: Mapping[str, Mapping[str, Any]],
    profiles: Mapping[str, pd.Series],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply validated advanced-fill rules in configuration order."""
    filled = load.copy()
    methods = cleaning_method.copy()

    for rule_name, rule in overrides.items():
        profile = profiles.get(rule_name)

        filled, methods = apply_auxiliary_fill_rule(
            filled,
            methods,
            rule_name=rule_name,
            rule=rule,
            profile=profile,
        )

    return filled, methods
