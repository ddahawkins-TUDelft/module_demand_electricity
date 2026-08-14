"""Apply validated advanced auxiliary-fill rules."""

from collections.abc import Mapping
from typing import Any

import pandas as pd
from common.time import as_utc_timestamp

from cleaning.advanced.methods.construct_from_sources import (
    METHOD_NAME as CONSTRUCT_FROM_SOURCES,
)
from cleaning.advanced.methods.external_profile import METHOD_NAME as EXTERNAL_PROFILE

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
        if profile is None:
            raise ValueError(
                f"Advanced-fill rule {rule_name!r} requires an external profile."
            )

        return apply_external_profile(
            load,
            cleaning_method,
            profile,
            country=rule["country"],
            start=as_utc_timestamp(rule["start"]),
            end=as_utc_timestamp(rule["end"]),
            scope=rule["scope"],
            rule_name=rule_name,
        )

    if method == LEAVE_MISSING:
        return load.copy(), cleaning_method.copy()

    # Cautionary in case of edge cases making is this far.
    raise ValueError(f"Unsupported advanced-fill method {method!r}.")


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

    target_index = filled.index[(filled.index >= start) & (filled.index < end)]

    if not profile.index.equals(target_index):
        raise ValueError(
            "Constructed profile index must exactly match the target period."
        )

    if scope == "fill_gaps":
        replace_mask = filled.loc[target_index, country].isna()

    elif scope == "overwrite":
        replace_mask = pd.Series(True, index=target_index)

    else:
        # Redundant but elifs are preferred so this stays.
        raise ValueError(f"Unsupported advanced fill scope: {scope!r}")

    replacement_index = target_index[replace_mask.to_numpy()]

    filled.loc[replacement_index, country] = profile.loc[replacement_index]

    methods.loc[replacement_index, country] = rule_name

    return filled, methods


def apply_auxiliary_fill_rules(
    load: pd.DataFrame,
    cleaning_method: pd.DataFrame,
    *,
    overrides: Mapping[str, Mapping[str, Any]],
    constructed_profiles: Mapping[str, pd.Series],
    external_profiles: Mapping[str, pd.Series],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply validated advanced-fill rules in configuration order."""
    filled = load.copy()
    methods = cleaning_method.copy()

    for rule_name, rule in overrides.items():
        method = rule["method"]

        if method == CONSTRUCT_FROM_SOURCES:
            profile = constructed_profiles.get(rule_name)

        elif method == EXTERNAL_PROFILE:
            profile = external_profiles.get(rule_name)

        else:
            profile = None

        filled, methods = apply_auxiliary_fill_rule(
            filled, methods, rule_name=rule_name, rule=rule, profile=profile
        )

    return filled, methods


def apply_external_profile(
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
    """Apply supplied external values to target demand."""
    filled = load.copy()
    methods = cleaning_method.copy()

    if country not in filled.columns:
        raise ValueError(f"Target country {country!r} is not present in load data.")

    candidate = profile.loc[(profile.index >= start) & (profile.index < end)]

    candidate = candidate.loc[candidate.index.intersection(filled.index)]

    if scope == "fill_gaps":
        replace_index = candidate.index[filled.loc[candidate.index, country].isna()]

    elif scope == "overwrite":
        replace_index = candidate.index

    else:
        # Redundant but elifs are preferred so this stays.
        raise ValueError(f"Unsupported advanced fill scope: {scope!r}")

    filled.loc[replace_index, country] = candidate.loc[replace_index]

    methods.loc[replace_index, country] = rule_name

    return filled, methods
