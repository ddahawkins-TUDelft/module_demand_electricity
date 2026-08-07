"""Plan auxiliary electricity-demand acquisition."""

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd
from cleaning.advanced.requirements import build_auxiliary_acquisition_requirements
from cleaning.advanced.source_requests import (
    build_auxiliary_source_batches,
    build_auxiliary_source_requests,
)

if TYPE_CHECKING:
    snakemake: Any


def build_auxiliary_acquisition_plan(
    *,
    fill_plan: pd.DataFrame,
    gap_filling_config: Mapping[str, Any],
    source_names: Sequence[str],
) -> dict[str, list[dict[str, object]]]:
    """Build a JSON-serializable auxiliary acquisition plan."""
    if gap_filling_config["mode"] != "advanced":
        return {"batches": []}

    if fill_plan.empty:
        return {"batches": []}

    advanced = gap_filling_config["advanced"]

    requirements = build_auxiliary_acquisition_requirements(
        overrides=advanced["overrides"],
        basic_rules=gap_filling_config["basic"]["rules"],
        basic_cleaning_enabled=(
            advanced["auxiliary_data"]
            ["basic_cleaning"]
            ["enabled"]
        ),
    )

    requests = build_auxiliary_source_requests(
        requirements,
        source_names=source_names,
    )

    batches = build_auxiliary_source_batches(
        requests
    )

    return {
        "batches": [
            {
                **batch,
                "start": batch["start"].isoformat(),
                "end": batch["end"].isoformat(),
            }
            for batch in batches
        ]
    }


def write_auxiliary_acquisition_plan(
    *,
    plan: dict[str, list[dict[str, object]]],
    output_path: str | Path,
) -> None:
    """Write the auxiliary acquisition plan as JSON."""
    output_path = Path(output_path)
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            plan,
            file,
            indent=2,
        )


if __name__ == "__main__":
    fill_plan = pd.read_parquet(
        snakemake.input.fill_plan
    )

    plan = build_auxiliary_acquisition_plan(
        fill_plan=fill_plan,
        gap_filling_config=snakemake.params.gap_filling,
        source_names=snakemake.params.source_names,
    )

    write_auxiliary_acquisition_plan(
        plan=plan,
        output_path=snakemake.output.plan,
    )
