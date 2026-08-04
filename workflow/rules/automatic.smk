"""Rules to used to download automatic resource files."""


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
