from datetime import datetime, timedelta


def neso_raw_files(_wildcards):
    """Return annual NESO input files for the configured period."""
    start = datetime.fromisoformat(config["temporal_scope"]["start"])
    end = datetime.fromisoformat(config["temporal_scope"]["end"])

    final_included_time = end - timedelta(microseconds=1)

    years = range(
        start.year,
        final_included_time.year + 1,
    )

    return [
        ("<resources>/automatic/neso/" f"historic_demand_{year}.csv") for year in years
    ]


rule prepare_load_opsd:
    input:
        validation="<resources>/automatic/config_validation.json",
        load="<resources>/automatic/load_opsd.csv",
    output:
        load="<resources>/automatic/load_opsd_api.parquet",
    log:
        "<logs>/prepare_load_opsd.log",
    conda:
        "../envs/module.yaml"
    params:
        start=config["temporal_scope"]["start"],
        end=config["temporal_scope"]["end"],
        country_codes=internal["load_entsoe_api"]["countries"],
    message:
        "Prepare electricity-demand data from OPSD."
    script:
        "../scripts/prepare_load_opsd.py"


rule prepare_load_neso:
    input:
        validation="<resources>/automatic/config_validation.json",
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
        country_codes=internal["load_entsoe_api"]["countries"],
    message:
        "Prepare electricity-demand data from NESO."
    script:
        "../scripts/prepare_load_neso.py"


LOAD_SOURCE_PATHS = {
    "entsoe_api": ("<resources>/automatic/" "load_entsoe_api.parquet"),
    "neso": ("<resources>/automatic/" "load_neso.parquet"),
    "opsd_api": ("<resources>/automatic/" "load_opsd_api.parquet"),
}


def configured_load_inputs(_wildcards):
    return [LOAD_SOURCE_PATHS[source_name] for source_name in config["load_sources"]]


rule clean_demand:
    input:
        configured_load_inputs,
    output:
        demand=("<resources>/automatic/" "load_basic_cleaned.parquet"),
        data_source=("<resources>/automatic/" "load_data_source.parquet"),
        cleaning_method=("<resources>/automatic/" "load_cleaning_method.parquet"),
        cleaning_method_rank=(
            "<resources>/automatic/" "load_cleaning_method_rank.parquet"
        ),
        gap_report=("<resources>/automatic/" "load_gap_report.parquet"),
        auxiliary_fill_plan=(
            "<resources>/automatic/" "load_auxiliary_fill_plan.parquet"
        ),
    log:
        "<logs>/clean_demand.log",
    conda:
        "../envs/module.yaml"
    params:
        source_names=config["load_sources"],
        gap_filling=config["gap_filling"],
    message:
        "Combine and clean electricity-demand sources."
    script:
        "../scripts/clean_demand.py"


rule plot_cleaning_timeline:
    input:
        demand=("<resources>/automatic/" "load_cleaned.parquet"),
        cleaning_method=("<resources>/automatic/" "load_final_cleaning_method.parquet"),
        cleaning_method_rank=(
            "<resources>/automatic/" "load_final_cleaning_method_rank.parquet"
        ),
    output:
        plot=("<results>/{shape}/" "load_cleaning_timeline.pdf"),
    log:
        "<logs>/{shape}/plot_cleaning_timeline.log",
    conda:
        "../envs/module.yaml"
    params:
        source_names=config["load_sources"],
        gap_filling=config["gap_filling"],
    message:
        "Plot electricity-demand cleaning provenance."
    script:
        "../scripts/plot_cleaning_timeline.py"


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
