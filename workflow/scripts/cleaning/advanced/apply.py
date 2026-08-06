"""Apply validated advanced auxiliary-fill rules."""

from collections.abc import Mapping
from typing import Any

import pandas as pd

from cleaning.advanced.construct_from_sources import (
    METHOD_NAME as CONSTRUCT_FROM_SOURCES,
)
from cleaning.advanced.construct_from_sources import (
    construct_from_sources,
)
from cleaning.advanced.external_profile import (
    METHOD_NAME as EXTERNAL_PROFILE,
)

MANUAL_REVIEW = "manual_review"
LEAVE_MISSING = "leave_missing"


def apply_auxiliary_fill_rule(
    load: pd.DataFrame,
    *,
    rule_name: str,
    rule: Mapping[str, Any],
) -> pd.DataFrame:
    """Apply one validated advanced-fill rule."""
    method = rule["method"]

    if method == CONSTRUCT_FROM_SOURCES:
        return construct_from_sources(
            load,
            rule_name=rule_name,
            rule=rule,
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
        return load.copy()

    raise ValueError(
        f"Unsupported advanced-fill method {method!r}."
    )