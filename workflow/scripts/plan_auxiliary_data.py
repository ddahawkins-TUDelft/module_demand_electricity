"""Write the compiled advanced electricity-demand execution plan."""

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd
from cleaning.advanced.planning.execution import build_advanced_execution_plan

if TYPE_CHECKING:
    snakemake: Any


def write_advanced_execution_plan(
    *,
    plan: dict[str, object],
    output_path: str | Path,
) -> None:
    """Write the advanced execution plan as JSON."""
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

    plan = build_advanced_execution_plan(
        fill_plan=fill_plan,
        gap_filling_config=snakemake.params.gap_filling,
        source_names=snakemake.params.source_names,
    )

    write_advanced_execution_plan(
        plan=plan,
        output_path=snakemake.output.plan,
    )
