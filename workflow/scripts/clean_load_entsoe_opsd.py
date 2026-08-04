"""Clean load data from ENTSO-E."""

import logging
import sys
from typing import TYPE_CHECKING, Any
from warnings import warn

import pandas as pd
import pycountry
from _schemas import LoadENTSOE
from gap_filling.pipeline import fill_gaps

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    snakemake: Any


def get_map_alpha2_to_alpha3(countries_alpha_2):
    """Get mapping from alpha-2 to alpha-3 country codes."""
    map_alpha2_to_alpha3 = {}
    for alpha2 in countries_alpha_2:
        country = pycountry.countries.get(alpha_2=alpha2)
        if country is not None:
            map_alpha2_to_alpha3[alpha2] = country.alpha_3
        else:
            warn(f"Country with alpha-2 code '{alpha2}' not found in pycountry.")

    return map_alpha2_to_alpha3


def main(path_raw_load, output):
    """Clean ENTSO-E load data (units of MW), downloaded from open power system data (OPSD)."""
    load = pd.read_csv(path_raw_load)
    load = LoadENTSOE.validate(load)

    # filter the raw data
    load = load.loc[load["variable"] == "load"]
    load = load.loc[load["attribute"] == "actual_entsoe_power_statistics"]

    # map country codes from alpha-2 to alpha-3
    map_alpha2_to_alpha3 = get_map_alpha2_to_alpha3(load["region"].unique())

    load = load.loc[load["region"].isin(map_alpha2_to_alpha3.keys())]
    load.loc[:, "region"] = load.loc[:, "region"].map(map_alpha2_to_alpha3)

    # pivot the data to have one column per region
    load_pivot = pd.pivot(
        load, index=["utc_timestamp"], columns=["region"], values="data"
    )
    load_pivot.index = pd.to_datetime(load_pivot.index).tz_localize(None)

    #Fill data gaps
    load_pivot, value_source = fill_gaps(
        load_pivot,
        config=snakemake.params.gap_filling,
    )

    # save data and plots
    load_pivot.to_parquet(output.output_load)
    value_source.to_parquet(output.value_source)


if __name__ == "__main__":
    sys.stderr = open(snakemake.log[0], "w", buffering=1)
    main(path_raw_load=snakemake.input.load, output=snakemake.output)
