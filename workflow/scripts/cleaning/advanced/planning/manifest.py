"""Read and query compiled advanced execution manifests."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

EXECUTION_PLAN_VERSION = 1


def write_execution_plan(plan: Mapping[str, Any], path: str | Path) -> None:
    """Write one compiled advanced execution plan."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(plan, file, indent=2)


def write_advanced_execution_plan(
    *, plan: dict[str, object], output_path: str | Path
) -> None:
    """Write the advanced execution plan as JSON."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(plan, file, indent=2)


def load_execution_plan(path: str | Path) -> dict[str, Any]:
    """Load one compiled advanced execution plan."""
    with open(path, encoding="utf-8") as file:
        plan = json.load(file)

    if not isinstance(plan, dict):
        raise TypeError("Advanced execution plan must contain a JSON object.")

    version = plan.get("version")

    if version != EXECUTION_PLAN_VERSION:
        raise ValueError(
            "Unsupported advanced execution plan version: "
            f"{version!r}. Expected {EXECUTION_PLAN_VERSION}."
        )

    return plan


def get_batch(
    plan: Mapping[str, Any], *, batch_id: str, source: str | None = None
) -> Mapping[str, Any]:
    """Return exactly one compiled auxiliary batch."""
    matches = [
        batch
        for batch in plan["batches"]
        if (
            batch["batch_id"] == batch_id
            and (source is None or batch["source"] == source)
        )
    ]

    if len(matches) != 1:
        source_text = f" for source {source!r}" if source is not None else ""
        raise ValueError(
            "Expected exactly one auxiliary batch "
            f"{batch_id!r}{source_text}, found {len(matches)}."
        )

    return matches[0]


def get_active_overrides(plan: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    """Return active overrides in compiled execution order."""
    rule_names = plan["active_rule_names"]
    rules = plan["rules"]

    unknown_rule_names = [
        rule_name for rule_name in rule_names if rule_name not in rules
    ]

    if unknown_rule_names:
        raise ValueError(
            "Advanced execution plan references unknown compiled "
            f"rules: {unknown_rule_names}."
        )

    return {rule_name: rules[rule_name]["override"] for rule_name in rule_names}


def get_rule_override(plan: Mapping[str, Any], *, rule_name: str) -> Mapping[str, Any]:
    """Return one active rule's compiled override definition."""
    try:
        rule = plan["rules"][rule_name]
    except KeyError as error:
        raise ValueError(
            f"Advanced execution plan does not contain active rule {rule_name!r}."
        ) from error

    return rule["override"]
