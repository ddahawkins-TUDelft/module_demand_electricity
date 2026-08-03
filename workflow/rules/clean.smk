rule clean_load_entsoe_opsd:
    input:
        load="<resources>/automatic/load_entsoe_opsd.csv",
    output:
        load="<resources>/automatic/load_entsoe_opsd.parquet",
    params:
        gap_filling=config["gap_filling"],
    log:
        "<logs>/clean_load_entsoe_opsd.log",
    conda:
        "../envs/module.yaml"
    script:
        "../scripts/clean_load_entsoe_opsd.py"


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
