"""Prepare NESO historic demand on the configured hourly target grid."""

import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable

import pandas as pd
from cleaning.advanced.planning.manifest import get_batch, load_execution_plan
from cleaning.sources.neso import add_utc_timestamps
from common.time import build_hourly_index

if TYPE_CHECKING:
    snakemake: Any


logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = [
    "SETTLEMENT_DATE",
    "SETTLEMENT_PERIOD",
    "ND",
]


def _read_neso_files(
    paths: Iterable[str | Path],
) -> pd.DataFrame:
    """Read and combine annual NESO historic-demand files."""
    frames: list[pd.DataFrame] = []

    for raw_path in paths:
        path = Path(raw_path)

        if not path.exists():
            raise FileNotFoundError(
                f"NESO input file does not exist: {path}"
            )

        logger.info(
            "Reading NESO historic demand from %s.",
            path,
        )

        try:
            frame = pd.read_csv(
                path,
                usecols=REQUIRED_COLUMNS,
            )
        except ValueError as error:
            available_columns = pd.read_csv(
                path,
                nrows=0,
            ).columns.tolist()

            raise ValueError(
                f"NESO file {path} does not contain the required "
                f"columns {REQUIRED_COLUMNS}. "
                f"Available columns: {available_columns}"
            ) from error

        frames.append(frame)

    if not frames:
        raise ValueError(
            "At least one NESO input file is required."
        )

    return pd.concat(
        frames,
        ignore_index=True,
    )


def _prepare_half_hourly_demand(
    raw: pd.DataFrame,
) -> pd.Series:
    """Convert raw NESO records to a UTC half-hourly demand series."""
    prepared = add_utc_timestamps(raw)

    prepared["ND"] = pd.to_numeric(
        prepared["ND"],
        errors="coerce",
    )

    invalid_demand_count = int(
        prepared["ND"].isna().sum()
    )

    if invalid_demand_count:
        logger.warning(
            "NESO contains %s missing or non-numeric ND values.",
            invalid_demand_count,
        )

    half_hourly = (
        prepared
        .set_index("timestamp")["ND"]
        .sort_index()
        .rename("GBR")
    )

    duplicate_mask = half_hourly.index.duplicated(
        keep=False
    )

    if duplicate_mask.any():
        duplicate_timestamps = (
            half_hourly.index[duplicate_mask]
            .unique()
            .astype(str)
            .tolist()
        )

        raise ValueError(
            "NESO data contain duplicate UTC timestamps: "
            f"{duplicate_timestamps[:10]}"
        )

    if not half_hourly.index.is_monotonic_increasing:
        raise ValueError(
            "Prepared NESO timestamps are not sorted."
        )

    return half_hourly


def _aggregate_hourly(
    half_hourly: pd.Series,
) -> pd.Series:
    """Aggregate half-hourly MW observations to hourly mean MW."""
    hourly_counts = half_hourly.resample("1h").count()

    incomplete_hours = hourly_counts.loc[
        hourly_counts.between(
            1,
            1,
            inclusive="both",
        )
    ]

    if not incomplete_hours.empty:
        logger.warning(
            "NESO contains %s hours with only one valid "
            "half-hourly ND observation.",
            len(incomplete_hours),
        )

    hourly = (
        half_hourly
        .resample("1h")
        .mean()
        .rename("GBR")
    )

    return hourly


def prepare_load_neso(
    *,
    input_paths: Iterable[str | Path],
    output_path: str | Path,
    temporal_start: str,
    temporal_end: str,
    countries: Iterable[str],
) -> None:
    """Prepare NESO demand on the common time-country target grid."""
    target_countries = list(countries)

    if len(target_countries) != len(
        set(target_countries)
    ):
        raise ValueError(
            "Target country codes must be unique."
        )

    target_index = build_hourly_index(
        start=temporal_start,
        end=temporal_end,
    )

    result = pd.DataFrame(
        index=target_index,
        columns=target_countries,
        dtype=float,
    )

    if "GBR" not in target_countries:
        logger.info(
            "GBR is not part of the configured country scope. "
            "Writing an empty NESO target-grid dataframe."
        )
    else:
        raw = _read_neso_files(input_paths)
        half_hourly = _prepare_half_hourly_demand(raw)
        hourly = _aggregate_hourly(half_hourly)

        result["GBR"] = hourly.reindex(
            target_index
        )

        supplied = int(
            result["GBR"].notna().sum()
        )

        missing = int(
            result["GBR"].isna().sum()
        )

        logger.info(
            "Prepared NESO GBR demand: %s supplied hourly "
            "values and %s missing values.",
            supplied,
            missing,
        )

    output_path = Path(output_path)
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result.to_parquet(output_path)

    logger.info(
        "Saved prepared NESO demand to %s with shape %s.",
        output_path,
        result.shape,
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
            source="neso",
        )
        temporal_start = batch["start"]
        temporal_end = batch["end"]
        countries = batch["countries"]
    else:
        temporal_start = snakemake.params.start
        temporal_end = snakemake.params.end
        countries = snakemake.params.country_codes

    prepare_load_neso(
        input_paths=[
            Path(path)
            for path in snakemake.input.annual_files
        ],
        output_path=snakemake.output.load,
        temporal_start=temporal_start,
        temporal_end=temporal_end,
        countries=countries,
    )
