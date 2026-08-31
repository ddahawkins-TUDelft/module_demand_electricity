"""Plots the diagnostic figure."""

import logging
import sys

from _plot_timeline import main

sys.stderr = open(snakemake.log[0], "w", buffering=1)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

main(
    demand_path=snakemake.input.demand,
    cleaning_method_path=snakemake.input.cleaning_method,
    cleaning_method_rank_path=(nakemake.input.cleaning_method_rank),
    output_path=snakemake.output.plot,
    source_names=snakemake.params.source_names,
    source_registry=snakemake.params.source_registry,
    gap_filling_config=snakemake.params.gap_filling,
)
