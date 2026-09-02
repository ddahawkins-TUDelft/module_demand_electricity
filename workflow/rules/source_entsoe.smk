"""Rules for the ENTSO-E Transparency Platform demand source."""


def entsoe_annual_files(countries, years):
    """Return reusable ENTSO-E country-year raw-file paths."""
    return [
        "<resources>/automatic/entsoe/raw/" f"{country}/{int(year)}.parquet"
        for country in countries
        for year in years
    ]


def entsoe_raw_files(wildcards):
    """Return ENTSO-E country-year files required for one target shape."""
    plan = read_target_data_plan(wildcards)

    countries = plan["source_contexts"].get("entsoe", [])

    years = years_for_period(
        config["temporal_scope"]["start"],
        config["temporal_scope"]["end"],
    )

    return entsoe_annual_files(countries, years)


def target_entsoe_countries(wildcards):
    """Return ENTSO-E target countries for one shape."""
    return target_source_contexts(wildcards, "entsoe")


def auxiliary_entsoe_raw_files(wildcards):
    """Return ENTSO-E country-year files required by one auxiliary batch."""
    plan = _read_auxiliary_plan(wildcards)

    batch = next(
        batch
        for batch in plan["batches"]
        if (batch["batch_id"] == wildcards.batch_id and batch["source"] == "entsoe")
    )

    return entsoe_annual_files(batch["countries"], batch["years"])


rule download_load_entsoe_country_year:
    input:
        token_entsoe="<token_entsoe>",
    output:
        annual_file=("<resources>/automatic/entsoe/raw/" "{country}/{year}.parquet"),
    log:
        "<logs>/download_load_entsoe_{country}_{year}.log",
    wildcard_constraints:
        country="[A-Z]{3}",
        year="[0-9]{4}",
    localrule: True
    conda:
        "../envs/module.yaml"
    threads: 1
    resources:
        entsoe_download=1,
    params:
        country_code=lambda wildcards: wildcards.country,
        year=lambda wildcards: int(wildcards.year),
    message:
        (
            "Download ENTSO-E electricity load for "
            "{wildcards.country} in {wildcards.year}."
        )
    script:
        "../scripts/download_load_entsoe.py"


rule prepare_load_entsoe:
    input:
        validation="<resources>/automatic/temporal_config_validation.json",
        target_plan=target_data_plan,
        annual_files=entsoe_raw_files,
    output:
        load="<resources>/automatic/{shape}/load_entsoe.parquet",
    log:
        "<logs>/{shape}/prepare_load_entsoe.log",
    localrule: True
    conda:
        "../envs/module.yaml"
    params:
        temporal_start=config["temporal_scope"]["start"],
        temporal_end=config["temporal_scope"]["end"],
        frequency=config["temporal_scope"]["frequency"],
        country_codes=target_entsoe_countries,
    message:
        "Prepare electricity load from ENTSOE."
    script:
        "../scripts/prepare_load_entsoe.py"


rule prepare_auxiliary_load_entsoe:
    input:
        plan=auxiliary_acquisition_plan,
        annual_files=auxiliary_entsoe_raw_files,
    output:
        load=(
            "<resources>/automatic/{shape}/"
            "auxiliary/entsoe/"
            "{batch_id}.parquet"
        ),
    log:
        "<logs>/{shape}/auxiliary/entsoe/prepare_{batch_id}.log",
    conda:
        "../envs/module.yaml"
    params:
        frequency=config["temporal_scope"]["frequency"],
    message:
        "Prepare auxiliary electricity-demand data from ENTSO-E."
    script:
        "../scripts/prepare_load_entsoe.py"
