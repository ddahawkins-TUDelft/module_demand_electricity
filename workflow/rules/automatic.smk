"""Rules used to download automatic resource files."""

from _time import years_in_period
from cleaning.advanced.requirements import (
    build_auxiliary_acquisition_requirements,
)
from cleaning.advanced.source_requests import (
    build_auxiliary_source_batches,
    build_auxiliary_source_requests,
)


NESO_YEARS = years_in_period(
    start=config["temporal_scope"]["start"],
    end=config["temporal_scope"]["end"],
)

NESO_RAW_FILES = expand(
    "<resources>/automatic/neso/"
    "historic_demand_{year}.csv",
    year=NESO_YEARS,
)

def _build_auxiliary_source_batches():
    """Build source-specific acquisition batches for advanced gap filling."""
    gap_filling = config["gap_filling"]

    if gap_filling["mode"] != "advanced":
        return []

    advanced = gap_filling["advanced"]

    requirements = build_auxiliary_acquisition_requirements(
        overrides=advanced["overrides"],
        basic_rules=gap_filling["basic"]["rules"],
        basic_cleaning_enabled=(
            advanced["auxiliary_data"]
            ["basic_cleaning"]
            ["enabled"]
        ),
    )

    requests = build_auxiliary_source_requests(
        requirements,
        source_names=config["load_sources"],
    )

    return build_auxiliary_source_batches(
        requests
    )


AUXILIARY_SOURCE_BATCHES = (
    _build_auxiliary_source_batches()
)

def _index_auxiliary_batches(
    source_name: str,
) -> dict[str, dict]:
    """Index auxiliary batches belonging to one source."""
    source_batches = [
        batch
        for batch in AUXILIARY_SOURCE_BATCHES
        if batch["source"] == source_name
    ]

    return {
        str(index): batch
        for index, batch in enumerate(source_batches)
    }


AUXILIARY_ENTSOE_BATCHES = (
    _index_auxiliary_batches("entsoe_api")
)

AUXILIARY_OPSD_BATCHES = (
    _index_auxiliary_batches("opsd")
)

AUXILIARY_NESO_BATCHES = (
    _index_auxiliary_batches("neso")
)

rule download_load_entsoe_api:
    input:
        token_entsoe="<token_entsoe>",
    output:
        load="<resources>/automatic/load_entsoe_api.parquet",
    log:
        "<logs>/download_load_entsoe_api.log",
    localrule: True
    conda:
        "../envs/module.yaml"
    params:
        country_codes=internal["load_entsoe_api"]["countries"],
        temporal_start=config["temporal_scope"]["start"],
        temporal_end=config["temporal_scope"]["end"],
    message:
        "Download electricity load from ENTSOE."
    script:
        "../scripts/download_load_entsoe_api.py"


rule download_load_entsoe_opsd:
    output:
        load="<resources>/automatic/load_entsoe_opsd.csv",
    log:
        "<logs>/download_load_entsoe_opsd.log",
    localrule: True
    conda:
        "../envs/module.yaml"
    params:
        url_load=internal["resources"]["automatic"]["load_entsoe_opsd"],
    message:
        "Download load profiles from Open Power System Data (OPSD)."
    shell:
        """
        curl -sSLo {output.load:q} {params.url_load:q}
        """

rule download_load_neso:
    output:
        annual_files=NESO_RAW_FILES,
    params:
        years=NESO_YEARS,
    log:
        "<logs>/download_load_neso.log",
    localrule: True
    conda:
        "../envs/module.yaml"
    message:
        "Download historic electricity demand from NESO."
    script:
        "../scripts/download_load_neso.py"


rule download_synthetic_electricity_demand:
    output:
        csv=(
            "<resources>/automatic/"
            "synthetic_electricity_demand/"
            "demand_hourly.csv"
        ),
    params:
        url=...,
        md5="a9b59e5a32ad422bcd9e12fea5dc291a",
    log:
        "<logs>/download_synthetic_electricity_demand.log",
    conda:
        "../envs/module.yaml"
    script:
        "../scripts/download_synthetic_electricity_demand.py"


rule download_population:
    output:
        population="<resources>/automatic/population.zip",
    log:
        "<logs>/download_population.log",
    localrule: True
    conda:
        "../envs/module.yaml"
    params:
        url_population=internal["resources"]["automatic"]["population"],
    message:
        "Download population data."
    shell:
        """
        curl -sSLo {output.population:q} {params.url_population:q}
        """


rule unzip_population:
    input:
        "<resources>/automatic/population.zip",
    output:
        "<resources>/automatic/population_raw.tif",
    log:
        "<logs>/unzip.log",
    localrule: True
    params:
        internal_paths=internal["resources"]["automatic"]["population_tif"],
    message:
        "Unzip population data."
    wrapper:
        "v9.8.0/utils/libarchive/extract"
