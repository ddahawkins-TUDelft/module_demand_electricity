"""Snakemake entry point for downloading ENTSO-E load data."""

import logging
from typing import TYPE_CHECKING, Any

from cleaning.advanced.planning.manifest import get_batch, load_execution_plan
from sources.entsoe.download import download_entsoe
from tclean import TimeGrid

if TYPE_CHECKING:
    snakemake: Any


def main(snakemake: Any) -> None:
    """Download ENTSO-E data for the requested workflow period."""
    plan_path = getattr(
        snakemake.input,
        "plan",
        None,
    )

    if plan_path is not None:
        plan = load_execution_plan(plan_path)

        batch = get_batch(
            plan,
            batch_id=snakemake.wildcards.batch_id,
            source="entsoe",
        )

        start = batch["start"]
        end = batch["end"]
        country_codes = list(batch["countries"])

    else:
        start = snakemake.params.temporal_start
        end = snakemake.params.temporal_end
        country_codes = list(
            snakemake.params.country_codes
        )

    grid = TimeGrid(
        start=start,
        end=end,
        frequency=snakemake.params.frequency,
    )

    download_entsoe(
        start=grid.start,
        end=grid.end,
        country_codes=country_codes,
        token_path=snakemake.input.token_entsoe,
        output_path=snakemake.output.raw_load,
        workers=snakemake.threads,
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    main(snakemake)
