"""Validate and build advanced auxiliary-fill plans."""

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd

from cleaning.advanced.construct_from_sources import (
    METHOD_NAME as CONSTRUCT_FROM_SOURCES,
)
from cleaning.advanced.external_profile import METHOD_NAME as EXTERNAL_PROFILE

FILL_GAPS_WITHIN_PERIOD = "fill_gaps_within_period"
OVERWRITE_ENTIRE_PERIOD = "overwrite_entire_period"

MANUAL_REVIEW = "manual_review"
LEAVE_MISSING = "leave_missing"


def validate_auxiliary_fill_rule(
    rule_name: str,
    rule: Mapping[str, Any],
) -> None:
    """Validate one configured advanced-fill rule."""
    if not isinstance(rule_name, str):
        raise TypeError(
            "Advanced-fill rule name must be a string."
        )

    if not rule_name:
        raise ValueError(
            "Advanced-fill rule name must not be empty."
        )

    if not isinstance(rule, Mapping):
        raise TypeError(
            f"Advanced-fill rule {rule_name!r} must be a mapping."
        )

    country = _get_required_string(
        rule,
        key="country",
        rule_name=rule_name,
    )
    start = _get_required_timestamp(
        rule,
        key="start",
        rule_name=rule_name,
    )
    end = _get_required_timestamp(
        rule,
        key="end",
        rule_name=rule_name,
    )

    if end < start:
        raise ValueError(
            f"Advanced-fill rule {rule_name!r} has an end "
            "timestamp before its start timestamp."
        )

    scope = _get_required_string(
        rule,
        key="scope",
        rule_name=rule_name,
    )
    method = _get_required_string(
        rule,
        key="method",
        rule_name=rule_name,
    )

    supported_scopes = {
        FILL_GAPS_WITHIN_PERIOD,
        OVERWRITE_ENTIRE_PERIOD,
    }

    if scope not in supported_scopes:
        raise ValueError(
            f"Unsupported scope {scope!r} in advanced-fill rule "
            f"{rule_name!r}. Expected one of "
            f"{sorted(supported_scopes)}."
        )

    supported_methods = {
        CONSTRUCT_FROM_SOURCES,
        EXTERNAL_PROFILE,
        MANUAL_REVIEW,
        LEAVE_MISSING,
    }

    if method not in supported_methods:
        raise ValueError(
            f"Unsupported method {method!r} in advanced-fill rule "
            f"{rule_name!r}. Expected one of "
            f"{sorted(supported_methods)}."
        )

    if method == CONSTRUCT_FROM_SOURCES:
        _validate_sources(
            rule,
            rule_name=rule_name,
        )

        if "scaling" in rule:
            _validate_scaling(
                rule["scaling"],
                rule_name=rule_name,
            )

    elif method in {
        MANUAL_REVIEW,
        LEAVE_MISSING,
    }:
        if "sources" in rule:
            raise ValueError(
                f"Advanced-fill rule {rule_name!r} uses method "
                f"{method!r} and must not define 'sources'."
            )

    # External-profile-specific configuration will be added when
    # acquisition of external profiles is implemented.

def _validate_sources(
    rule: Mapping[str, Any],
    *,
    rule_name: str,
) -> None:
    """Validate source references for source-based construction."""
    if "sources" not in rule:
        raise ValueError(
            f"Advanced-fill rule {rule_name!r} using method "
            f"{CONSTRUCT_FROM_SOURCES!r} must define 'sources'."
        )

    sources = rule["sources"]

    if not isinstance(sources, Sequence) or isinstance(
        sources,
        (str, bytes),
    ):
        raise TypeError(
            f"'sources' in advanced-fill rule {rule_name!r} "
            "must be an ordered sequence."
        )

    if not sources:
        raise ValueError(
            f"'sources' in advanced-fill rule {rule_name!r} "
            "must contain at least one source."
        )

    for position, source in enumerate(sources):
        _validate_source(
            source,
            rule_name=rule_name,
            position=position,
        )


def _validate_source(
    source: object,
    *,
    rule_name: str,
    position: int,
    context: str = "source",
) -> None:
    """Validate one country-period source reference."""
    if not isinstance(source, Mapping):
        raise TypeError(
            f"{context.capitalize()} {position} in advanced-fill rule "
            f"{rule_name!r} must be a mapping."
        )

    _get_required_string(
        source,
        key="country",
        rule_name=rule_name,
        context=f"{context} {position}",
    )

    start = _get_required_timestamp(
        source,
        key="start",
        rule_name=rule_name,
        context=f"{context} {position}",
    )
    end = _get_required_timestamp(
        source,
        key="end",
        rule_name=rule_name,
        context=f"{context} {position}",
    )

    if end < start:
        raise ValueError(
            f"{context.capitalize()} {position} in advanced-fill rule "
            f"{rule_name!r} has an end timestamp before its "
            "start timestamp."
        )

    weight = source.get("weight", 1.0)

    if not isinstance(weight, int | float):
        raise TypeError(
            f"Weight for {context} {position} in advanced-fill rule "
            f"{rule_name!r} must be numeric."
        )

    if weight <= 0:
        raise ValueError(
            f"Weight for {context} {position} in advanced-fill rule "
            f"{rule_name!r} must be greater than zero."
        )


def _get_required_string(
    config: Mapping[str, Any],
    *,
    key: str,
    rule_name: str,
    context: str = "rule",
) -> str:
    """Return one required non-empty string field."""
    if key not in config:
        raise ValueError(
            f"Advanced-fill {context} in rule {rule_name!r} "
            f"must define {key!r}."
        )

    value = config[key]

    if not isinstance(value, str):
        raise TypeError(
            f"Advanced-fill {context} field {key!r} in rule "
            f"{rule_name!r} must be a string."
        )

    if not value:
        raise ValueError(
            f"Advanced-fill {context} field {key!r} in rule "
            f"{rule_name!r} must not be empty."
        )

    return value


def _get_required_timestamp(
    config: Mapping[str, Any],
    *,
    key: str,
    rule_name: str,
    context: str = "rule",
) -> pd.Timestamp:
    """Return one required timestamp as a UTC pandas timestamp."""
    if key not in config:
        raise ValueError(
            f"Advanced-fill {context} in rule {rule_name!r} "
            f"must define {key!r}."
        )

    try:
        timestamp = pd.Timestamp(config[key])
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"Advanced-fill {context} field {key!r} in rule "
            f"{rule_name!r} is not a valid timestamp."
        ) from error

    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    else:
        timestamp = timestamp.tz_convert("UTC")

    return timestamp


def _validate_scaling(
    scaling: object,
    *,
    rule_name: str,
) -> None:
    """Validate optional scaling configuration."""
    if not isinstance(scaling, Mapping):
        raise TypeError(
            f"'scaling' in advanced-fill rule {rule_name!r} "
            "must be a mapping."
        )

    method = _get_required_string(
        scaling,
        key="method",
        rule_name=rule_name,
        context="scaling",
    )

    supported_methods = {
        "match_energy",
    }

    if method not in supported_methods:
        raise ValueError(
            f"Unsupported scaling method {method!r} in "
            f"advanced-fill rule {rule_name!r}. Expected one of "
            f"{sorted(supported_methods)}."
        )

    if "target_sources" not in scaling:
        raise ValueError(
            f"Scaling configuration in advanced-fill rule "
            f"{rule_name!r} must define 'target_sources'."
        )

    target_sources = scaling["target_sources"]

    if not isinstance(target_sources, Sequence) or isinstance(
        target_sources,
        (str, bytes),
    ):
        raise TypeError(
            f"'target_sources' in advanced-fill rule "
            f"{rule_name!r} must be an ordered sequence."
        )

    if not target_sources:
        raise ValueError(
            f"'target_sources' in advanced-fill rule "
            f"{rule_name!r} must contain at least one source."
        )

    for position, source in enumerate(target_sources):
        _validate_source(
            source,
            rule_name=rule_name,
            position=position,
            context="scaling target source",
        )

def build_auxiliary_fill_plan(
    rules: Mapping[str, Mapping[str, Any]],
) -> pd.DataFrame:
    """Validate and normalize configured advanced-fill rules."""
    if not isinstance(rules, Mapping):
        raise TypeError(
            "Advanced-fill rules must be provided as a mapping."
        )

    records: list[dict[str, Any]] = []

    # TODO: Support reusable libraries of advanced overrides.
    # Before planning auxiliary acquisition, filter configured overrides
    # against the current model countries and temporal scope. Overrides
    # that do not intersect the current target scope should be ignored,
    # while applicable overrides should continue to be validated strictly.
    # This allows users to have a general overrides file for which they
    # need not retune the dates for each new run/horizon.

    for rule_name, rule in rules.items():
        validate_auxiliary_fill_rule(
            rule_name,
            rule,
        )

        method = rule["method"]

        if method == CONSTRUCT_FROM_SOURCES:
            status = "ready"
        elif method == EXTERNAL_PROFILE:
            status = "not_implemented"
        elif method == MANUAL_REVIEW:
            status = "manual_review"
        elif method == LEAVE_MISSING:
            status = "leave_missing"
        else:
            raise AssertionError(
                f"Unhandled advanced-fill method: {method!r}"
            )

        scaling = rule.get("scaling")

        records.append(
            {
                "rule_name": rule_name,
                "country": rule["country"],
                "target_start": _get_required_timestamp(
                    rule,
                    key="start",
                    rule_name=rule_name,
                ),
                "target_end": _get_required_timestamp(
                    rule,
                    key="end",
                    rule_name=rule_name,
                ),
                "scope": rule["scope"],
                "method": method,
                "status": status,
                "source_count": len(
                    rule.get("sources", [])
                ),
                "scaling_method": (
                    scaling["method"]
                    if scaling is not None
                    else None
                ),
            }
        )

    columns = [
        "rule_name",
        "country",
        "target_start",
        "target_end",
        "scope",
        "method",
        "status",
        "source_count",
        "scaling_method",
    ]

    plan = pd.DataFrame.from_records(
        records,
        columns=columns,
    )

    if plan.empty:
        return plan

    return plan.sort_values(
        [
            "country",
            "target_start",
            "rule_name",
        ]
    ).reset_index(drop=True)

