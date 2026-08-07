"""Download electricity load data from ENTSO-E using the entsoe-py library."""

import sys
from typing import TYPE_CHECKING, Any
from warnings import warn

import pandas as pd
import pycountry
import yaml
from entsoe import EntsoePandasClient
from entsoe.exceptions import NoMatchingDataError

if TYPE_CHECKING:
    snakemake: Any


def load_txt(filepath):
    """Load text file."""
    with open(filepath) as file:
        data = file.read()
    return data


def load_yaml(path):
    """Load a YAML file."""
    with open(path) as file:
        return yaml.safe_load(file)


def main(start, end, country_codes, token, output_load):
    """Download load in MW via the ENTSO-E API."""
    start = pd.Timestamp(start, tz="UTC")
    end = pd.Timestamp(end, tz="UTC")
    token = load_txt(token).strip()
    client = EntsoePandasClient(api_key=token)

    data = []
    for country_alpha_3 in country_codes:
        country_alpha_2 = pycountry.countries.get(alpha_3=country_alpha_3).alpha_2

        try:
            df_country = client.query_load(
                country_code=country_alpha_2, start=start, end=end
            )
            df_country = df_country["Actual Load"]
            df_country.name = country_alpha_3

        except NoMatchingDataError:
            warn(
                f"No data found for {country_alpha_2}/{country_alpha_3} in the given period: {start} to {end}"
            )
            df_country = pd.Series(name=country_alpha_3)

        data.append(df_country)

    df = pd.concat(data, axis=1)

    df.index = pd.to_datetime(df.index, utc=True)

    df = df.resample("1h").mean()

    # reindexing to add some security to the entsoe download
    target_index = pd.date_range(
        start=start,
        end=end,
        freq="h",
        inclusive="left",
    )

    df = df.reindex(
        index=target_index,
        columns=country_codes,
    )

    non_numeric_columns = df.select_dtypes(
        exclude="number"
    ).columns

    invalid = {
        column: df[column].dropna().head().tolist()
        for column in non_numeric_columns
        if not df[column].dropna().empty
    }

    if invalid:
        raise TypeError(
            "ENTSO-E load contains non-numeric values: "
            f"{invalid}"
        )

    #Pre-cleaning. Replaces empty object columns with NaN columns to allow for data-source combining
    df = df.astype(float)

    df.to_parquet(output_load)


if __name__ == "__main__":
    sys.stderr = open(snakemake.log[0], "w", buffering=1)
    main(
        start=snakemake.params.temporal_start,
        end=snakemake.params.temporal_end,
        country_codes=snakemake.params.country_codes,
        token=snakemake.input.token_entsoe,
        output_load=snakemake.output.load,
    )
