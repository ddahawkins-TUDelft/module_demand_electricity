"""Aggregates auxiliary data into one source."""

from pathlib import Path

import pandas as pd
from cleaning.combine_sources import combine_auxiliary_sources


def _source_name(path: str | Path) -> str:
    """Return source name from auxiliary source path."""
    return Path(path).parent.name


loads = {_source_name(path): pd.read_parquet(path) for path in snakemake.input.sources}

combined, data_source, cleaning_method = combine_auxiliary_sources(
    loads, priority=snakemake.params.source_priority
)

combined.to_parquet(snakemake.output.demand)
data_source.to_parquet(snakemake.output.data_source)
cleaning_method.to_parquet(snakemake.output.cleaning_method)
