"""The pipeline coordinates the gap-filling rules and ensures each receives the necessary parameters."""
from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd

from cleaning.advanced.gap_report import build_gap_report
from cleaning.advanced.plan import build_auxiliary_fill_plan
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
    pd.DataFrame, #auxiliary_fill_plan
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

    basic_config = {
        "mode": gap_filling_config["mode"],
        "rules": gap_filling_config["basic"]["rules"],
    }

    cleaned, cleaning_method = fill_basic_gaps(
        combined,
        cleaning_method=cleaning_method,
        config=basic_config,
    )

    basic_rules = gap_filling_config["basic"]["rules"]

    cleaning_method_ranks = build_cleaning_method_ranks(
        source_priority=source_priority,
        rules=basic_rules,
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
        advanced_overrides = gap_filling_config["advanced"]["overrides"]
        auxiliary_fill_plan = build_auxiliary_fill_plan(
            advanced_overrides
        )

        logger.info(
            "Advanced gap diagnosis found %s unresolved gaps "
            "covering %s values.",
            len(gap_report),
            int(gap_report["gap_hours"].sum()),
        )

        logger.info(
            "Advanced auxiliary-fill plan contains %s configured "
            "instructions.",
            len(auxiliary_fill_plan),
        )
    else:
        auxiliary_fill_plan = build_auxiliary_fill_plan({})

    return (
        cleaned,
        data_source,
        cleaning_method,
        cleaning_method_rank,
        gap_report,
        auxiliary_fill_plan,
    )

