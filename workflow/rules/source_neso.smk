"""Rules for the NESO historic demand source."""


def neso_annual_files(years):
    """Return reusable annual NESO raw-file paths for the requested years."""
    return [
        "<resources>/automatic/neso/" f"historic_demand_{int(year)}.csv"
        for year in years
    ]


def neso_raw_files(_wildcards):
    """Return annual NESO input files for the configured period."""
    years = years_for_period(
        config["temporal_scope"]["start"],
        config["temporal_scope"]["end"],
    )

    return neso_annual_files(years)


def auxiliary_neso_raw_files(wildcards):
    """Return annual NESO files required by one auxiliary batch."""
    plan = _read_auxiliary_plan()

    batch = next(
        batch
        for batch in plan["batches"]
        if (batch["batch_id"] == wildcards.batch_id and batch["source"] == "neso")
    )

    return neso_annual_files(batch["years"])


rule download_load_neso_year:
    output:
        annual_file=("<resources>/automatic/neso/" "historic_demand_{year}.csv"),
    log:
        "<logs>/download_load_neso_{year}.log",
    localrule: True
    conda:
        "../envs/module.yaml"
    threads: 1
    resources:
        neso_download=1,
    params:
        year=lambda wildcards: int(wildcards.year),
    message:
        "Download NESO historic electricity demand for {wildcards.year}."
    script:
        "../scripts/download_load_neso.py"


rule prepare_load_neso:
    input:
        validation="<resources>/automatic/temporal_config_validation.json",
        annual_files=neso_raw_files,
    output:
        load="<resources>/automatic/load_neso.parquet",
    log:
        "<logs>/prepare_load_neso.log",
    conda:
        "../envs/module.yaml"
    params:
        start=config["temporal_scope"]["start"],
        end=config["temporal_scope"]["end"],
        country_codes=internal["load_entsoe"]["countries"],
        frequency=config["temporal_scope"]["frequency"],
    message:
        "Prepare electricity-demand data from NESO."
    script:
        "../scripts/prepare_load_neso.py"


rule prepare_auxiliary_load_neso:
    input:
        plan=auxiliary_acquisition_plan,
        annual_files=auxiliary_neso_raw_files,
    output:
        load=("<resources>/automatic/" "auxiliary/neso/" "{batch_id}.parquet"),
    log:
        "<logs>/auxiliary/neso/{batch_id}.log",
    conda:
        "../envs/module.yaml"
    params:
        frequency=config["temporal_scope"]["frequency"],
    message:
        "Prepare auxiliary electricity-demand data from NESO."
    script:
        "../scripts/prepare_load_neso.py"
