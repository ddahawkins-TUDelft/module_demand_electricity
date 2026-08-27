"""Snakemake entry point for downloading ENTSO-E load data."""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from _advanced_execution import get_batch, load_execution_plan
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
    formatter = logging.Formatter(
        "%(levelname)s: %(message)s"
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    log_path = Path(snakemake.log[0])
    log_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_handler = logging.FileHandler(
        log_path,
        mode="w",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[
            console_handler,
            file_handler,
        ],
    )

    main(snakemake)
