def entsoe_raw_files(_wildcards):
    """Return ENTSO-E country-year files required by the configured period."""
    years = years_for_period(
        config["temporal_scope"]["start"],
        config["temporal_scope"]["end"],
    )

    return entsoe_annual_files(internal["load_entsoe"]["countries"], years)


def neso_raw_files(_wildcards):
    """Return annual NESO input files for the configured period."""
    years = years_for_period(
        config["temporal_scope"]["start"],
        config["temporal_scope"]["end"],
    )

    return neso_annual_files(years)


def entsoe_power_statistics_raw_files(_wildcards):
    """Return Power Statistics annual files required by the target period."""
    years = years_for_period(
        config["temporal_scope"]["start"],
        config["temporal_scope"]["end"],
    )

    return entsoe_power_statistics_annual_files(
        years
    )

rule prepare_load_entsoe:
    input:
        validation="<resources>/automatic/temporal_config_validation.json",
        annual_files=entsoe_raw_files,
    output:
        load="<resources>/automatic/load_entsoe.parquet",
    log:
        "<logs>/prepare_load_entsoe.log",
    localrule: True
    conda:
        "../envs/module.yaml"
    params:
        temporal_start=config["temporal_scope"]["start"],
        temporal_end=config["temporal_scope"]["end"],
        frequency=config["temporal_scope"]["frequency"],
        country_codes=internal["load_entsoe"]["countries"],
    message:
        "Prepare electricity load from ENTSOE."
    script:
        "../scripts/prepare_load_entsoe.py"


rule prepare_load_opsd:
    input:
        validation="<resources>/automatic/temporal_config_validation.json",
        load="<resources>/automatic/opsd/raw_load.parquet",
    output:
        load="<resources>/automatic/load_opsd.parquet",
    log:
        "<logs>/prepare_load_opsd.log",
    conda:
        "../envs/module.yaml"
    params:
        start=config["temporal_scope"]["start"],
        end=config["temporal_scope"]["end"],
        frequency=config["temporal_scope"]["frequency"],
        country_codes=internal["load_entsoe"]["countries"],
    message:
        "Prepare electricity-demand data from OPSD."
    script:
        "../scripts/prepare_load_opsd.py"


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


rule prepare_load_entsoe_power_statistics:
    input:
        validation=(
            "<resources>/automatic/"
            "temporal_config_validation.json"
        ),
        annual_files=entsoe_power_statistics_raw_files,
    output:
        load=(
            "<resources>/automatic/"
            "load_entsoe_power_statistics.parquet"
        ),
    params:
        temporal_start=config["temporal_scope"]["start"],
        temporal_end=config["temporal_scope"]["end"],
        frequency=config["temporal_scope"]["frequency"],
        country_codes=internal["load_entsoe"]["countries"],
    log:
        "<logs>/prepare_load_entsoe_power_statistics.log",
    conda:
        "../envs/module.yaml"
    message:
        "Prepare electricity-demand data from ENTSO-E Power Statistics."
    script:
        "../scripts/prepare_load_entsoe_power_statistics.py"



def configured_load_inputs(_wildcards):
    """Return prepared demand files for configured sources."""
    return [
        (
            "<resources>/automatic/"
            f"load_{source_name}.parquet"
        )
        for source_name in config["load_sources"]
    ]


rule clean_demand:
    input:
        load_inputs=configured_load_inputs,
        validation="<resources>/automatic/gap_filling_config_validation.json",
    output:
        demand=("<resources>/automatic/load_basic_cleaned.parquet"),
        data_source=("<resources>/automatic/load_data_source.parquet"),
        cleaning_method=("<resources>/automatic/load_cleaning_method.parquet"),
        cleaning_method_rank=("<resources>/automatic/load_cleaning_method_rank.parquet"),
        gap_report=("<resources>/automatic/load_gap_report.parquet"),
    log:
        "<logs>/clean_demand.log",
    conda:
        "../envs/module.yaml"
    params:
        source_names=config["load_sources"],
        temporal_scope=config["temporal_scope"],
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
        source_registry=SOURCE_REGISTRY,
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
