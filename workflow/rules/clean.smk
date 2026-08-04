rule prepare_load_opsd:
    input:
        load="<resources>/automatic/load_entsoe_opsd.csv",
    output:
        load="<resources>/automatic/load_opsd_api.parquet",
    params:
        start=config["temporal_scope"]["start"],
        end=config["temporal_scope"]["end"],
        country_codes=internal["load_entsoe_api"]["countries"],
    log:
        "<logs>/prepare_load_opsd.log",
    conda:
        "../envs/module.yaml"
    message:
        "Prepare electricity-demand data from OPSD."
    script:
        "../scripts/prepare_load_opsd.py"


LOAD_SOURCE_PATHS = {
    "entsoe_api": (
        "<resources>/automatic/"
        "load_entsoe_api.parquet"
    ),
    "opsd_api": (
        "<resources>/automatic/"
        "load_opsd_api.parquet"
    ),
}


def configured_load_inputs(wildcards):
    return [
        LOAD_SOURCE_PATHS[source_name]
        for source_name in config["load_sources"]
    ]


rule clean_demand:
    input:
        configured_load_inputs
    output:
        demand=(
            "<resources>/automatic/"
            "load_cleaned.parquet"
        ),
        data_source=(
            "<resources>/automatic/"
            "load_data_source.parquet"
        ),
        value_source=(
            "<resources>/automatic/"
            "load_value_source.parquet"
        ),
    params:
        source_names=config["load_sources"],
        gap_filling=config["gap_filling"],
    log:
        "<logs>/clean_demand.log",
    conda:
        "../envs/module.yaml"
    message:
        "Combine and clean electricity-demand sources."
    script:
        "../scripts/clean_demand.py"


rule clean_population:
    input:
        vector="<shapes>",
        raster=rules.unzip_population.output[0],
    output:
        path="<resources>/automatic/{shape}/population_clean.tif",
    log:
        "<logs>/{shape}/clean_population.log",
    wrapper:
        "v7.2.0/geo/rasterio/clip-geotiff"
