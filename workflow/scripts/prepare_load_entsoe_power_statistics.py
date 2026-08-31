"""Snakemake entry point for preparing ENTSO-E Power Statistics load."""

import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sources.entsoe_power_statistics.prepare import prepare_entsoe_power_statistics
from tclean import TimeGrid

if TYPE_CHECKING:
    snakemake: Any


def main(snakemake: Any) -> None:
    """Prepare ENTSO-E Power Statistics for the configured scope."""
    grid = TimeGrid(
        start=snakemake.params.temporal_start,
        end=snakemake.params.temporal_end,
        frequency=snakemake.params.frequency,
    )

    prepare_entsoe_power_statistics(
        input_paths=[
            Path(path)
            for path in snakemake.input.annual_files
        ],
        output_path=snakemake.output.load,
        grid=grid,
        country_codes=list(
            snakemake.params.country_codes
        ),
    )


if __name__ == "__main__":
    sys.stderr = open(
        snakemake.log[0],
        "w",
        buffering=1,
    )

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    main(snakemake)
