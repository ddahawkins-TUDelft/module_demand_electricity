"""Rules used to download automatic resource files."""


rule validate_config_semantics:
    output:
        "<resources>/automatic/config_validation.json",
    conda:
        "../envs/module.yaml"
    params:
        validation_config=config,
    message:
        "Validate module configuration semantics."
    script:
        "../scripts/validate_config.py"


rule download_load_entsoe_api:
    input:
        validation="<resources>/automatic/config_validation.json",
        token_entsoe="<token_entsoe>",
    output:
        load="<resources>/automatic/load_entsoe_api.parquet",
    log:
        "<logs>/download_load_entsoe_api.log",
    localrule: True
    conda:
        "../envs/module.yaml"
    threads:
        min(
            internal["load_entsoe_api"]["MAX_WORKERS"],
            len(internal["load_entsoe_api"]["countries"]),
        )
    params:
        country_codes=internal["load_entsoe_api"]["countries"],
        temporal_start=config["temporal_scope"]["start"],
        temporal_end=config["temporal_scope"]["end"],
    message:
        "Download electricity load from ENTSOE."
    script:
        "../scripts/download_load_entsoe_api.py"


rule download_load_opsd:
    output:
        load=update("<resources>/automatic/load_opsd.csv"),
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
    input:
        validation="<resources>/automatic/config_validation.json",
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
