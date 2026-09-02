"""Rules used for generic automatic resources and validation."""


import json


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


checkpoint plan_target_data:
    input:
        shapes="<shapes>",
        temporal_validation=(
            "<resources>/automatic/temporal_config_validation.json"
        ),
    output:
        plan=(
            "<resources>/automatic/{shape}/"
            "target_data_plan.json"
        ),
    conda:
        "../envs/module.yaml"
    params:
        source_names=config["load_sources"],
        source_registry=SOURCE_REGISTRY,
        temporal_scope=config["temporal_scope"],
    message:
        "Plan target electricity-demand data acquisition."
    script:
        "../scripts/plan_target_data.py"


def target_data_plan(wildcards):
    """Return the target-data plan after the checkpoint completes."""
    return checkpoints.plan_target_data.get(
        shape=wildcards.shape,
    ).output.plan


def read_target_data_plan(wildcards):
    """Read the resolved target-data plan for one shape."""
    plan_file = checkpoints.plan_target_data.get(
        shape=wildcards.shape,
    ).output.plan

    with open(plan_file, encoding="utf-8") as file:
        return json.load(file)


def target_source_contexts(wildcards, source_name):
    """Return target contexts assigned to one source for one shape."""
    plan = read_target_data_plan(wildcards)

    return plan["source_contexts"].get(source_name, [])


def target_source_temporal_scope(wildcards, source_name):
    """Return the planned target temporal scope for one source."""
    plan = read_target_data_plan(wildcards)

    temporal_scope = plan["source_temporal_scopes"].get(source_name)

    if temporal_scope is None:
        raise ValueError(
            f"Source {source_name!r} has no active target temporal scope."
        )

    return temporal_scope


def target_source_start(wildcards, source_name):
    """Return the planned target start timestamp for one source."""
    return target_source_temporal_scope(
        wildcards,
        source_name,
    )["start"]


def target_source_end(wildcards, source_name):
    """Return the planned target end timestamp for one source."""
    return target_source_temporal_scope(
        wildcards,
        source_name,
    )["end"]


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
