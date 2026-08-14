"""Compile the execution manifest for advanced gap filling."""

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd
from common.time import as_utc_timestamp

from cleaning.advanced.methods.construct_from_sources import (
    METHOD_NAME as CONSTRUCT_FROM_SOURCES,
)
from cleaning.advanced.methods.external_profile import METHOD_NAME as EXTERNAL_PROFILE
from cleaning.advanced.planning.manifest import EXECUTION_PLAN_VERSION
from cleaning.advanced.planning.requirements import (
    build_auxiliary_acquisition_requirements,
)
from cleaning.advanced.planning.source_requests import (
    build_auxiliary_source_batches,
    build_auxiliary_source_requests,
)


def build_advanced_execution_plan(
    *,
    fill_plan: pd.DataFrame,
    gap_filling_config: Mapping[str, Any],
    source_names: Sequence[str],
) -> dict[str, object]:
    """Compile all domain-aware information needed by the advanced DAG."""
    if gap_filling_config["mode"] != "advanced" or fill_plan.empty:
        return _empty_execution_plan()

    overrides = gap_filling_config["advanced"]["overrides"]
    ordered_active_rule_names = _get_ordered_active_rule_names(
        fill_plan, overrides=overrides
    )
    active_overrides = {
        rule_name: overrides[rule_name] for rule_name in ordered_active_rule_names
    }

    requirements = build_auxiliary_acquisition_requirements(
        overrides=active_overrides,
        basic_rules=gap_filling_config["basic"]["rules"],
        basic_cleaning_enabled=(
            gap_filling_config["advanced"]["auxiliary_data"]["basic_cleaning"][
                "enabled"
            ]
        ),
    )
    requests = build_auxiliary_source_requests(requirements, source_names=source_names)
    batches = [
        _serialize_batch(batch) for batch in build_auxiliary_source_batches(requests)
    ]

    rules: dict[str, dict[str, object]] = {}
    constructed_profile_rule_names: list[str] = []
    external_profile_files: dict[str, str] = {}
    batch_plan = {"batches": batches}

    for rule_name in ordered_active_rule_names:
        override = active_overrides[rule_name]
        required_group_ids: list[str] = []

        if override["method"] == CONSTRUCT_FROM_SOURCES:
            required_group_ids = _get_required_auxiliary_group_ids(
                batch_plan, override=override
            )
            constructed_profile_rule_names.append(rule_name)

        elif override["method"] == EXTERNAL_PROFILE:
            external_profile_files[rule_name] = str(override["path"])

        rules[rule_name] = {
            "override": override,
            "required_group_ids": required_group_ids,
        }

    return {
        "version": EXECUTION_PLAN_VERSION,
        "active_rule_names": ordered_active_rule_names,
        "rules": rules,
        "batches": batches,
        "batch_ids_by_source": _index_batch_ids_by_source(batches),
        "groups": _index_batch_ids_by_group(batches),
        "constructed_profile_rule_names": constructed_profile_rule_names,
        "external_profile_files": external_profile_files,
    }


def _empty_execution_plan() -> dict[str, object]:
    """Return an empty plan with the complete manifest schema."""
    return {
        "version": EXECUTION_PLAN_VERSION,
        "active_rule_names": [],
        "rules": {},
        "batches": [],
        "batch_ids_by_source": {},
        "groups": {},
        "constructed_profile_rule_names": [],
        "external_profile_files": {},
    }


def _get_ordered_active_rule_names(
    fill_plan: pd.DataFrame,
    *,
    overrides: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    """Return active rule names in configured execution order."""
    active_rule_names = set(fill_plan["rule_name"])

    return [
        rule_name
        for rule_name in overrides
        if rule_name in active_rule_names
    ]


def _serialize_batch(batch: Mapping[str, object]) -> dict[str, object]:
    """Convert one planned batch to JSON-compatible values."""
    start = pd.Timestamp(batch["start"])
    end = pd.Timestamp(batch["end"])

    final_included_time = end - pd.Timedelta(nanoseconds=1)

    return {
        **batch,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "years": list(range(start.year, final_included_time.year + 1)),
    }


def _index_batch_ids_by_source(
    batches: Sequence[Mapping[str, object]],
) -> dict[str, list[str]]:
    """Index planned batch identifiers by source."""
    result: dict[str, list[str]] = {}

    for batch in batches:
        result.setdefault(str(batch["source"]), []).append(str(batch["batch_id"]))

    return result


def _index_batch_ids_by_group(
    batches: Sequence[Mapping[str, object]],
) -> dict[str, list[str]]:
    """Index planned batch identifiers by period group."""
    result: dict[str, list[str]] = {}

    for batch in batches:
        result.setdefault(str(batch["group_id"]), []).append(str(batch["batch_id"]))

    return result


def _get_required_auxiliary_sources(override: Mapping) -> list[Mapping]:
    """Return all auxiliary sources consumed by an override."""
    sources = list(override["sources"])

    scaling = override.get("scaling")
    if scaling is not None:
        sources.extend(scaling.get("target_sources", []))

    return sources


def _get_required_auxiliary_group_ids(plan: Mapping, *, override: Mapping) -> list[str]:
    """Return auxiliary groups required to execute one override."""
    group_ids: set[str] = set()

    for source in _get_required_auxiliary_sources(override):
        country = source["country"]
        start = as_utc_timestamp(source["start"])
        end = as_utc_timestamp(source["end"])

        matching_groups = {
            batch["group_id"]
            for batch in plan["batches"]
            if (
                country in batch["countries"]
                and as_utc_timestamp(batch["start"]) <= start
                and as_utc_timestamp(batch["end"]) >= end
            )
        }

        if len(matching_groups) != 1:
            raise ValueError(
                "Expected exactly one auxiliary group covering "
                f"{country!r} from {start} to {end}, "
                f"found {sorted(matching_groups)}."
            )

        group_ids.update(matching_groups)

    return sorted(group_ids)
