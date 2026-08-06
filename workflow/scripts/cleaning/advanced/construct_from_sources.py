"""Construct an auxiliary demand profile from configured source periods."""

from collections.abc import Mapping
from typing import Any

import pandas as pd

METHOD_NAME = "construct_from_sources"


def construct_from_sources(
    load: pd.DataFrame,
    *,
    rule_name: str,
    rule: Mapping[str, Any],
) -> pd.DataFrame:
    """Construct a target profile from configured country-period sources."""
    raise NotImplementedError(
        "Advanced-fill method 'construct_from_sources' "
        "has not yet been implemented."
    )