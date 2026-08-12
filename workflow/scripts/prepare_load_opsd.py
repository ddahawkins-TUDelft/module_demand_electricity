"""Prepare electricity-demand data downloaded from OPSD."""

import sys
from time import perf_counter
from typing import TYPE_CHECKING, Any
from warnings import warn

import pandas as pd
import pycountry
from cleaning.advanced.planning.manifest import get_batch, load_execution_plan
from common.schemas import LoadENTSOE
from common.time import as_utc_timestamp, build_hourly_index

if TYPE_CHECKING:
    snakemake: Any


def get_map_alpha2_to_alpha3(
    countries_alpha_2,
) -> dict[str, str]:
    """Map ISO alpha-2 country codes to alpha-3 codes."""
    mapping = {}

    for alpha2 in countries_alpha_2:
        country = pycountry.countries.get(alpha_2=alpha2)

        if country is not None:
            mapping[alpha2] = country.alpha_3
        else:
            warn(
                f"Country with alpha-2 code '{alpha2}' "
                "not found in pycountry."
            )

    return mapping


def main(
    path_raw_load,
    output_load,
    start,
    end,
    country_codes,
):
    """Prepare OPSD demand for the configured scope."""
    load = pd.read_csv(path_raw_load)
    load = LoadENTSOE.validate(load)

    load = load.loc[load["variable"] == "load"]
    load = load.loc[
        load["attribute"]
        == "actual_entsoe_power_statistics"
    ].copy()

    start = as_utc_timestamp(start)
    end = as_utc_timestamp(end)

    load["utc_timestamp"] = pd.to_datetime(
        load["utc_timestamp"],
        utc=True,
    )

    # Filter the large long-format table before pivoting.
    load = load.loc[
        (load["utc_timestamp"] >= start)
        & (load["utc_timestamp"] < end)
    ].copy()

    country_mapping = get_map_alpha2_to_alpha3(
        load["region"].unique()
    )

    load = load.loc[
        load["region"].isin(country_mapping)
    ].copy()

    load.loc[:, "region"] = load["region"].map(
        country_mapping
    )

    # Keep only countries required by this module run.
    load = load.loc[
        load["region"].isin(country_codes)
    ].copy()

    load.loc[:, "data"] = pd.to_numeric(
        load["data"],
        errors="raise",
    )

    prepared = pd.pivot(
        load,
        index="utc_timestamp",
        columns="region",
        values="data",
    )

    target_index = build_hourly_index(
        start=start,
        end=end,
    )

    prepared = prepared.reindex(
        index=target_index,
        columns=country_codes,
    )

    prepared = prepared.astype(float)

    prepared.to_parquet(output_load)

if __name__ == "__main__":
    sys.stderr = open(
        snakemake.log[0],
        "w",
        buffering=1,
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
            source="opsd_api",
        )
        start = batch["start"]
        end = batch["end"]
        country_codes = batch["countries"]
    else:
        start = snakemake.params.start
        end = snakemake.params.end
        country_codes = list(
            snakemake.params.country_codes
        )

    main(
        path_raw_load=snakemake.input.load,
        output_load=snakemake.output.load,
        start=start,
        end=end,
        country_codes=country_codes,
    )
