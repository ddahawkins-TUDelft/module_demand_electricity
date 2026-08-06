"""The pipeline coordinates the gap-filling rules and ensures each receives the necessary parameters."""
from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd

from cleaning.advanced.gap_report import build_gap_report
from cleaning.basic.pipeline import fill_basic_gaps
from cleaning.combine_sources import combine_sources
from cleaning.provenance import build_cleaning_method_ranks, derive_cleaning_method_rank

logger = logging.getLogger(__name__)


def clean_demand(
    sources: Mapping[str, pd.DataFrame],
    *,
    source_priority: Sequence[str],
    gap_filling_config: Mapping[str, Any],
) -> tuple[
    pd.DataFrame, #data
    pd.DataFrame, #sources
    pd.DataFrame, #method
    pd.DataFrame, #rank
    pd.DataFrame, #gap_report
]:
    """Combine observed sources and fill remaining gaps."""
    (
        combined,
        data_source,
        cleaning_method,
    ) = combine_sources(
        sources,
        priority=source_priority,
    )

    cleaned, cleaning_method = fill_basic_gaps(
        combined,
        cleaning_method=cleaning_method,
        config=gap_filling_config,
    )

    rules = gap_filling_config["rules"]

    cleaning_method_ranks = build_cleaning_method_ranks(
        source_priority=source_priority,
        rules=rules,
    )

    cleaning_method_rank = derive_cleaning_method_rank(
        cleaning_method=cleaning_method,
        ranks=cleaning_method_ranks,
    )

    gap_report = build_gap_report(
        cleaned,
        enabled=gap_filling_config["mode"] == "advanced",
    )

    if gap_filling_config["mode"] == "advanced":
        logger.info(
            "Advanced gap diagnosis found %s unresolved gaps "
            "covering %s values.",
            len(gap_report),
            int(gap_report["gap_hours"].sum()),
        )

    return (
        cleaned,
        data_source,
        cleaning_method,
        cleaning_method_rank,
        gap_report
    )
