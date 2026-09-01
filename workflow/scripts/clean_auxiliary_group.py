"""Combine and clean one auxiliary electricity-demand group."""

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd
from tclean import TCleanConfig, TimeGrid, clean

if TYPE_CHECKING:
    snakemake: Any


def main(snakemake: Any) -> None:
    """Combine and basic-clean one auxiliary source group."""
    plan = _read_plan(snakemake.input.plan)

    group_id = str(snakemake.wildcards.group_id)

    batch_ids = plan["groups"][group_id]

    batches_by_id = {batch["batch_id"]: batch for batch in plan["batches"]}

    batches = [batches_by_id[batch_id] for batch_id in batch_ids]

    if not batches:
        raise ValueError(f"Auxiliary group {group_id!r} contains no source batches.")

    starts = {pd.Timestamp(batch["start"]) for batch in batches}

    ends = {pd.Timestamp(batch["end"]) for batch in batches}

    if len(starts) != 1 or len(ends) != 1:
        raise ValueError(
            f"Auxiliary group {group_id!r} contains inconsistent batch periods."
        )

    group_start = next(iter(starts))
    group_end = next(iter(ends))

    grid = TimeGrid(
        start=group_start, end=group_end, frequency=(snakemake.params.frequency)
    )

    config = TCleanConfig(grid=grid)

    source_paths = list(snakemake.input.sources)

    if len(source_paths) != len(batches):
        raise ValueError(
            f"Auxiliary group {group_id!r} has "
            f"{len(batches)} planned batches but "
            f"{len(source_paths)} prepared inputs."
        )

    sources: dict[str, pd.DataFrame] = {}

    for batch, path in zip(batches, source_paths, strict=True):
        source_name = str(batch["source"])

        if source_name in sources:
            raise ValueError(
                f"Auxiliary group {group_id!r} "
                f"contains duplicate source "
                f"{source_name!r}."
            )

        sources[source_name] = _read_prepared_source(path)

    contexts = sorted(
        {
            context
            for data in sources.values()
            for context in data.columns
        }
    )

    sources = {
        source_name: data.reindex(columns=contexts)
        for source_name, data in sources.items()
    }

    basic_rules = (
        list(snakemake.params.basic_rules)
        if snakemake.params.basic_cleaning_enabled
        else []
    )

    (cleaned, data_source, cleaning_method) = clean(
        sources, config=config, basic_rules=basic_rules
    )

    cleaned.to_parquet(snakemake.output.demand)

    data_source.to_parquet(snakemake.output.data_source)

    cleaning_method.to_parquet(snakemake.output.cleaning_method)


def _read_plan(path: str | Path) -> dict[str, Any]:
    """Read the advanced execution manifest."""
    with Path(path).open(encoding="utf-8") as file:
        return json.load(file)


def _read_prepared_source(path: str | Path) -> pd.DataFrame:
    """Read one prepared auxiliary provider frame."""
    data = pd.read_parquet(path)

    if not isinstance(data.index, pd.DatetimeIndex):
        data.index = pd.to_datetime(data.index, utc=True)

    elif data.index.tz is None:
        data.index = data.index.tz_localize("UTC")

    else:
        data.index = data.index.tz_convert("UTC")

    data.index.name = "timestamp"

    return data


if __name__ == "__main__":
    main(snakemake)
