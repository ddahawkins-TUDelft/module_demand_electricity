"""Rules used to download automatic resource files."""


rule validate_temporal_config_semantics:
    output:
        "<resources>/automatic/temporal_config_validation.json",
    conda:
        "../envs/module.yaml"
    params:
        validation_kind="temporal",
        validation_config={
            "temporal_scope": config["temporal_scope"],
        },
    message:
        "Validate temporal configuration semantics."
    script:
        "../scripts/validate_config.py"


rule validate_gap_filling_config_semantics:
    output:
        "<resources>/automatic/gap_filling_config_validation.json",
    conda:
        "../envs/module.yaml"
    params:
        validation_kind="gap_filling",
        validation_config={
            "temporal_scope": config["temporal_scope"],
            "gap_filling": config["gap_filling"],
        },
    message:
        "Validate gap-filling configuration semantics."
    script:
        "../scripts/validate_config.py"


rule download_load_entsoe_country_year:
    input:
        token_entsoe="<token_entsoe>",
    output:
        annual_file=(
            "<resources>/automatic/entsoe/raw/"
            "{country}/{year}.parquet"
        ),
    log:
        "<logs>/download_load_entsoe_{country}_{year}.log",
    wildcard_constraints:
        country="[A-Z]{3}",
        year="[0-9]{4}",
    localrule: True
    conda:
        "../envs/module.yaml"
    threads: 1
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


rule download_load_opsd:
    output:
        load=update("<resources>/automatic/opsd/raw_load.parquet"),
    log:
        "<logs>/download_load_opsd.log",
    localrule: True
    conda:
        "../envs/module.yaml"
    params:
        url=internal["resources"]["automatic"]["load_opsd"],
    message:
        "Download load profiles from Open Power System Data (OPSD)."
    script:
        "../scripts/download_load_opsd.py"


rule download_load_neso_year:
    output:
        annual_file=("<resources>/automatic/neso/" "historic_demand_{year}.csv"),
    log:
        "<logs>/download_load_neso_{year}.log",
    localrule: True
    conda:
        "../envs/module.yaml"
    params:
        year=lambda wildcards: int(wildcards.year),
    message:
        "Download NESO historic electricity demand for {wildcards.year}."
    script:
        "../scripts/download_load_neso.py"


rule download_population:
    output:
        population=update("<resources>/automatic/population.zip"),
    log:
        "<logs>/download_population.log",
    localrule: True
    conda:
        "../envs/module.yaml"
    params:
        url=internal["resources"]["automatic"]["population"],
        expected_member=internal["resources"]["automatic"]["population_tif"],
    message:
        "Download population data."
    script:
        "../scripts/download_population.py"


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
