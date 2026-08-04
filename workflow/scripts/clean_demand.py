"""Combine and clean prepared electricity-demand sources."""

import logging
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd
from cleaning.pipeline import clean_demand

if TYPE_CHECKING:
    snakemake: Any

logger = logging.getLogger(__name__)


def main(
    *,
    input_paths: Sequence[str | Path],
    source_names: Sequence[str],
    gap_filling_config: Mapping[str, Any],
    output: Any,
) -> None:
    """Read prepared sources, clean demand, and write provenance."""
    if len(input_paths) != len(source_names):
        raise ValueError(
            "The number of input files must equal the number "
            "of configured load sources."
        )

    sources = {
        source_name: _read_prepared_source(path)
        for source_name, path in zip(
            source_names,
            input_paths,
            strict=True,
        )
    }

    cleaned, data_source, value_source = clean_demand(
        sources,
        source_priority=source_names,
        gap_filling_config=gap_filling_config,
    )

    cleaned.to_parquet(output.demand)
    data_source.to_parquet(output.data_source)
    value_source.to_parquet(output.value_source)

    _log_source_counts(data_source)


def _read_prepared_source(
    path: str | Path,
) -> pd.DataFrame:
    """Read and validate one prepared demand source."""
    demand = pd.read_parquet(path)

    if not isinstance(demand.index, pd.DatetimeIndex):
        demand.index = pd.to_datetime(
            demand.index,
            utc=True,
        )

    elif demand.index.tz is None:
        demand.index = demand.index.tz_localize("UTC")

    else:
        demand.index = demand.index.tz_convert("UTC")

    if demand.index.has_duplicates:
        raise ValueError(
            f"Demand source contains duplicate timestamps: {path}"
        )

    if demand.columns.has_duplicates:
        raise ValueError(
            f"Demand source contains duplicate columns: {path}"
        )

    return demand.sort_index()


def _log_source_counts(
    data_source: pd.DataFrame,
) -> None:
    """Log the number of cells supplied by each observed source."""
    counts = data_source.stack().value_counts()

    for source_name, count in counts.items():
        logger.info(
            "%s supplied %s observed values.",
            source_name,
            int(count),
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

    main(
        input_paths=list(snakemake.input),
        source_names=list(
            snakemake.params.source_names
        ),
        gap_filling_config=(
            snakemake.params.gap_filling
        ),
        output=snakemake.output,
    )
