"""Plan target electricity-demand data acquisition."""

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

import geopandas as gpd
import pandas as pd
from _schemas import Shapes

if TYPE_CHECKING:
    snakemake: Any


TARGET_DATA_PLAN_VERSION = 1


def _as_utc(value: object) -> pd.Timestamp:
    """Interpret naive timestamps as UTC and convert aware timestamps to UTC."""
    timestamp = pd.Timestamp(value)

    if timestamp.tzinfo is None:
        return timestamp.tz_localize("UTC")

    return timestamp.tz_convert("UTC")


def source_overlaps_period(
    metadata: Mapping[str, Any],
    *,
    start: object,
    end: object,
) -> bool:
    """Return whether a source can supply any part of the requested period."""
    temporal_scope = metadata.get("temporal_scope") or {}

    source_start = temporal_scope.get("start")
    source_end = temporal_scope.get("end")

    start = _as_utc(start)
    end = _as_utc(end)

    if source_start is not None:
        if end <= _as_utc(source_start):
            return False

    if source_end is not None:
        if start >= _as_utc(source_end):
            return False

    return True


def supported_target_contexts(
    target_contexts: Sequence[str],
    *,
    metadata: Mapping[str, Any],
) -> list[str]:
    """Return target contexts supported by one source."""
    contexts = metadata.get("contexts")

    # Missing or empty contexts means that the source declares
    # no geographic restriction.
    if not contexts:
        return list(target_contexts)

    supported = set(contexts)

    return [
        context
        for context in target_contexts
        if context in supported
    ]


def build_target_data_plan(
    *,
    target_contexts: Sequence[str],
    source_names: Sequence[str],
    source_registry: Mapping[str, Mapping[str, Any]],
    temporal_scope: Mapping[str, Any],
) -> dict[str, object]:
    """Build the target-data acquisition plan."""
    target_contexts = sorted(set(target_contexts))

    if not target_contexts:
        raise ValueError(
            "The supplied shapes contain no land-country contexts."
        )

    source_contexts: dict[str, list[str]] = {}
    active_sources: list[str] = []

    for source_name in source_names:
        if source_name not in source_registry:
            raise ValueError(
                f"Unsupported electricity-demand source: {source_name!r}."
            )

        metadata = source_registry[source_name]

        if not source_overlaps_period(
            metadata,
            start=temporal_scope["start"],
            end=temporal_scope["end"],
        ):
            source_contexts[source_name] = []
            continue

        contexts = supported_target_contexts(
            target_contexts,
            metadata=metadata,
        )

        source_contexts[source_name] = contexts

        if contexts:
            active_sources.append(source_name)

    covered_contexts = {
        context
        for contexts in source_contexts.values()
        for context in contexts
    }

    uncovered_contexts = sorted(
        set(target_contexts).difference(covered_contexts)
    )

    if uncovered_contexts:
        raise ValueError(
            "No configured electricity-demand source can supply "
            "the following target context(s) within the requested "
            f"temporal scope: {uncovered_contexts}. "
            f"Configured sources: {list(source_names)}."
        )

    return {
        "version": TARGET_DATA_PLAN_VERSION,
        "target_contexts": target_contexts,
        "active_sources": active_sources,
        "source_contexts": source_contexts,
    }


def write_target_data_plan(
    *,
    plan: Mapping[str, object],
    output_path: str | Path,
) -> None:
    """Write the target-data acquisition plan as JSON."""
    output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(plan, file, indent=2)


def main(snakemake: Any) -> None:
    """Build and write the target-data acquisition plan."""
    shapes = gpd.read_parquet(snakemake.input.shapes)
    shapes = Shapes.validate(shapes)

    land_shapes = shapes.loc[shapes["shape_class"] == "land"]

    target_contexts = (
        land_shapes["country_id"]
        .drop_duplicates()
        .tolist()
    )

    plan = build_target_data_plan(
        target_contexts=target_contexts,
        source_names=snakemake.params.source_names,
        source_registry=snakemake.params.source_registry,
        temporal_scope=snakemake.params.temporal_scope,
    )

    write_target_data_plan(
        plan=plan,
        output_path=snakemake.output.plan,
    )


if __name__ == "__main__":
    main(snakemake)
