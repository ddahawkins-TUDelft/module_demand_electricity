"""Write the compiled advanced electricity-demand execution plan."""

from typing import TYPE_CHECKING, Any

import pandas as pd
from cleaning.advanced.planning.execution import build_advanced_execution_plan
from cleaning.advanced.planning.manifest import write_execution_plan
from tclean import TimeGrid

if TYPE_CHECKING:
    snakemake: Any


if __name__ == "__main__":
    fill_plan = pd.read_parquet(snakemake.input.fill_plan)

    grid = TimeGrid(
        start=snakemake.params.start,
        end=snakemake.params.end,
        frequency=snakemake.params.frequency,
    )

    plan = build_advanced_execution_plan(
        fill_plan=fill_plan,
        gap_filling_config=snakemake.params.gap_filling,
        source_names=snakemake.params.source_names,
        grid=grid,
    )

    write_execution_plan(
        plan,
        snakemake.output.plan,
    )
