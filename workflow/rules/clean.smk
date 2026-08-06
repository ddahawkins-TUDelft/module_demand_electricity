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


rule prepare_load_neso:
    input:
        annual_files=rules.download_load_neso.output.annual_files,
    output:
        load="<resources>/automatic/load_neso.parquet",
    params:
        start=config["temporal_scope"]["start"],
        end=config["temporal_scope"]["end"],
        country_codes=internal["load_entsoe_api"]["countries"],
    log:
        "<logs>/prepare_load_neso.log",
    conda:
        "../envs/module.yaml"
    message:
        "Prepare electricity-demand data from NESO."
    script:
        "../scripts/prepare_load_neso.py"

rule prepare_synthetic_electricity_demand:
    input:
        csv=rules.download_synthetic_electricity_demand.output.csv,
    output:
        load=(
            "<resources>/automatic/"
            "load_synthetic_electricity_demand.parquet"
        ),
    params:
        start=config["temporal_scope"]["start"],
        end=config["temporal_scope"]["end"],
        country_codes=internal["load_entsoe_api"]["countries"],
    log:
        "<logs>/prepare_load_synthetic.log",
    conda:
        "../envs/module.yaml"
    message:
        "Prepare electricity-demand data from PyPSA synthetic profile."
    script:
        "../scripts/prepare_load_synthetic.py"
        

LOAD_SOURCE_PATHS = {
    "entsoe_api": (
        "<resources>/automatic/"
        "load_entsoe_api.parquet"
    ),
    "neso": (
        "<resources>/automatic/"
        "load_neso.parquet"
    ),
    "opsd_api": (
        "<resources>/automatic/"
        "load_opsd_api.parquet"
    ),
}


def configured_load_inputs(_wildcards):
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
        cleaning_method=(
            "<resources>/automatic/"
            "load_cleaning_method.parquet"
        ),
        cleaning_method_rank=(
            "<resources>/automatic/"
            "load_cleaning_method_rank.parquet"
        ),
        gap_report=(
            "<resources>/automatic/"
            "load_gap_report.parquet"
        ),
        auxiliary_fill_plan=(
            "<resources>/automatic/"
            "load_auxiliary_fill_plan.parquet"
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


rule plot_cleaning_timeline:
    input:
        demand=(
            "<resources>/automatic/"
            "load_cleaned.parquet"
        ),
        cleaning_method=(
            "<resources>/automatic/"
            "load_cleaning_method.parquet"
        ),
        cleaning_method_rank=(
            "<resources>/automatic/"
            "load_cleaning_method_rank.parquet"
        ),
    output:
        plot=(
            "<results>/{shape}/"
            "load_cleaning_timeline.pdf"
        ),
    params:
        source_names=config["load_sources"],
        gap_filling=config["gap_filling"],
    log:
        "<logs>/{shape}/plot_cleaning_timeline.log",
    conda:
        "../envs/module.yaml"
    message:
        "Plot electricity-demand cleaning provenance."
    script:
        "../scripts/cleaning/plot_cleaning_timeline.py"

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

