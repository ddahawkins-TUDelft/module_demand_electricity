"""Download electricity load data from ENTSO-E using the entsoe-py library."""

import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import perf_counter
from typing import TYPE_CHECKING, Any

import pandas as pd
import pycountry
from cleaning.advanced.planning.manifest import get_batch, load_execution_plan
from common.time import as_utc_timestamp, build_hourly_index
from entsoe.entsoe import EntsoePandasClient
from entsoe.exceptions import NoMatchingDataError

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    snakemake: Any


def configure_logging(log_path) -> None:
    """Log downloader progress to both the console and rule log."""
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(
        log_path,
        mode="w",
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)


def load_txt(filepath):
    """Load text file."""
    with open(filepath) as file:
        data = file.read()

    return data


def download_country(
    *,
    country_alpha_3: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
    token: str,
) -> tuple[str, pd.Series, float]:
    """Download ENTSO-E load for one country."""
    country = pycountry.countries.get(
        alpha_3=country_alpha_3
    )

    if country is None:
        raise ValueError(
            "Unknown ISO alpha-3 country code: "
            f"{country_alpha_3!r}."
        )

    country_alpha_2 = country.alpha_2

    client = EntsoePandasClient(
        api_key=token,
        timeout=60,
    )

    country_start = perf_counter()

    try:
        df_country = client.query_load(
            country_code=country_alpha_2,
            start=start,
            end=end,
        )

        df_country = df_country["Actual Load"]
        df_country.name = country_alpha_3

    except NoMatchingDataError:
        logger.warning(
            "No data found for %s/%s in the given period: %s to %s.",
            country_alpha_2,
            country_alpha_3,
            start,
            end,
        )

        df_country = pd.Series(
            name=country_alpha_3,
            dtype=float,
        )

    elapsed = perf_counter() - country_start

    return (
        country_alpha_3,
        df_country,
        elapsed,
    )


def main(
    start,
    end,
    country_codes,
    token,
    output_load,
    workers,
    ):
    """Download load in MW via the ENTSO-E API."""
    start = as_utc_timestamp(start)
    end = as_utc_timestamp(end)
    token = load_txt(token).strip()

    country_codes = list(country_codes)
    total_countries = len(country_codes)

    download_start = perf_counter()

    logger.info(
        "Downloading ENTSO-E load for %s countries "
        "from %s to %s using %s parallel workers.",
        total_countries,
        start,
        end,
        workers,
    )

    data_by_country = {}

    with ThreadPoolExecutor(
        max_workers=workers
    ) as executor:
        futures = {
            executor.submit(
                download_country,
                country_alpha_3=country_alpha_3,
                start=start,
                end=end,
                token=token,
            ): country_alpha_3
            for country_alpha_3 in country_codes
        }

        for completed, future in enumerate(
            as_completed(futures),
            start=1,
        ):
            country_alpha_3 = futures[future]

            try:
                (
                    country_alpha_3,
                    df_country,
                    elapsed,
                ) = future.result()

            except Exception as exc:
                raise RuntimeError(
                    "Failed to download ENTSO-E load for "
                    f"{country_alpha_3!r}."
                ) from exc

            data_by_country[
                country_alpha_3
            ] = df_country

            logger.info(
                "[%s/%s] Finished %s in %.1fs.",
                completed,
                total_countries,
                country_alpha_3,
                elapsed,
            )

    logger.info(
        "Finished ENTSO-E downloads in %.1fs.",
        perf_counter() - download_start,
    )

    # Restore configured country order because futures complete
    # in arbitrary order.
    data = [
        data_by_country[country_alpha_3]
        for country_alpha_3 in country_codes
    ]

    processing_start = perf_counter()

    df = pd.concat(
        data,
        axis=1,
    )

    df.index = pd.to_datetime(
        df.index,
        utc=True,
    )

    df = df.resample("1h").mean()

    # Reindexing adds security to the ENTSO-E download.
    target_index = build_hourly_index(
        start=start,
        end=end,
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

    # Pre-cleaning. Replace empty object columns with NaN
    # columns to allow data-source combining.
    df = df.astype(float)

    df.to_parquet(output_load)

    logger.info(
        "ENTSO-E processing and write completed in %.1fs.",
        perf_counter() - processing_start,
    )


if __name__ == "__main__":
    configure_logging(
        snakemake.log[0]
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
            source="entsoe_api",
        )
        start = batch["start"]
        end = batch["end"]
        country_codes = batch["countries"]
    else:
        start = snakemake.params.temporal_start
        end = snakemake.params.temporal_end
        country_codes = snakemake.params.country_codes

    main(
        start=start,
        end=end,
        country_codes=country_codes,
        token=snakemake.input.token_entsoe,
        output_load=snakemake.output.load,
        workers=snakemake.threads,
    )
