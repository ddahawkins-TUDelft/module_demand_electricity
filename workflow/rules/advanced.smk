import json


def _read_auxiliary_plan(wildcards):
    """Read the resolved advanced execution plan for one shape."""
    plan_file = checkpoints.plan_auxiliary_data.get(
        shape=wildcards.shape,
    ).output.plan

    with open(plan_file, encoding="utf-8") as file:
        return json.load(file)


def auxiliary_acquisition_plan(wildcards):
    """Return the execution plan after the checkpoint completes."""
    return checkpoints.plan_auxiliary_data.get(
        shape=wildcards.shape,
    ).output.plan


def auxiliary_group_source_files(wildcards):
    """Return prepared source files for one auxiliary group."""
    plan = _read_auxiliary_plan(wildcards)

    batch_ids = plan["groups"][wildcards.group_id]

    batches_by_id = {batch["batch_id"]: batch for batch in plan["batches"]}

    return [
        (
            "<resources>/automatic/"
            f"{wildcards.shape}/"
            f"auxiliary/{batches_by_id[batch_id]['source']}/"
            f"{batch_id}.parquet"
        )
        for batch_id in batch_ids
    ]


def auxiliary_rule_cleaned_files(wildcards):
    """Return cleaned auxiliary files required by one advanced override."""
    plan = _read_auxiliary_plan(wildcards)

    group_ids = plan["rules"][wildcards.rule_name]["required_group_ids"]

    return [
        (
            "<resources>/automatic/"
            f"{wildcards.shape}/"
            "auxiliary/cleaned/"
            f"{group_id}.parquet"
        )
        for group_id in group_ids
    ]


def advanced_constructed_profiles(wildcards):
    """Return constructed profiles required by active advanced overrides."""
    plan = _read_auxiliary_plan(wildcards)

    return [
        (
            "<resources>/automatic/"
            f"{wildcards.shape}/"
            "auxiliary/constructed/"
            f"{rule_name}.parquet"
        )
        for rule_name in plan["constructed_profile_rule_names"]
    ]


def final_clean_demand_input(wildcards):
    """Return the cleaned demand appropriate for the configured mode."""
    if config["gap_filling"]["mode"] == "advanced":
        return (
            "<resources>/automatic/"
            f"{wildcards.shape}/"
            "load_advanced_cleaned.parquet"
        )

    return rules.clean_demand.output.demand


def final_cleaning_method_input(wildcards):
    """Return cleaning provenance appropriate for the configured mode."""
    if config["gap_filling"]["mode"] == "advanced":
        return (
            "<resources>/automatic/"
            f"{wildcards.shape}/"
            "load_advanced_cleaning_method.parquet"
        )

    return rules.clean_demand.output.cleaning_method


def advanced_external_profile_files(wildcards):
    plan = _read_auxiliary_plan(wildcards)

    return [
        f"<external_profiles>/{filename}"
        for filename in dict.fromkeys(plan["external_profile_files"].values())
    ]


checkpoint plan_auxiliary_data:
    input:
        demand=rules.clean_demand.output.demand,
    output:
        plan=("<resources>/automatic/{shape}/" "auxiliary/advanced_execution_plan.json"),
    conda:
        "../envs/module.yaml"
    params:
        temporal_scope=config["temporal_scope"],
        gap_filling=config["gap_filling"],
        source_names=config["load_sources"],
        source_registry=SOURCE_REGISTRY,
    message:
        "Plan auxiliary electricity-demand acquisition."
    script:
        "../scripts/plan_auxiliary_data.py"


rule finalise_clean_demand:
    input:
        target_plan=target_data_plan,
        demand=final_clean_demand_input,
        cleaning_method=final_cleaning_method_input,
    output:
        demand=("<resources>/automatic/{shape}/" "load_cleaned.parquet"),
        cleaning_method=(
            "<resources>/automatic/{shape}/" "load_final_cleaning_method.parquet"
        ),
        cleaning_method_rank=(
            "<resources>/automatic/{shape}/" "load_final_cleaning_method_rank.parquet"
        ),
    conda:
        "../envs/module.yaml"
    params:
        source_names=active_load_sources,
        gap_filling=config["gap_filling"],
    message:
        "Finalise cleaned electricity demand and provenance."
    script:
        "../scripts/finalise_clean_demand.py"


rule clean_auxiliary_group:
    input:
        plan=auxiliary_acquisition_plan,
        sources=auxiliary_group_source_files,
    output:
        demand=(
            "<resources>/automatic/{shape}/" "auxiliary/cleaned/" "{group_id}.parquet"
        ),
        data_source=(
            "<resources>/automatic/{shape}/"
            "auxiliary/cleaned/"
            "{group_id}_data_source.parquet"
        ),
        cleaning_method=(
            "<resources>/automatic/{shape}/"
            "auxiliary/cleaned/"
            "{group_id}_cleaning_method.parquet"
        ),
    log:
        "<logs>/{shape}/auxiliary/clean_{group_id}.log",
    conda:
        "../envs/module.yaml"
    params:
        frequency=config["temporal_scope"]["frequency"],
        basic_rules=config["gap_filling"]["basic"]["rules"],
        basic_cleaning_enabled=(
            config["gap_filling"]["advanced"]["auxiliary_data"]["basic_cleaning"][
                "enabled"
            ]
        ),
    message:
        "Combine and clean auxiliary electricity-demand sources."
    script:
        "../scripts/clean_auxiliary_group.py"


rule construct_auxiliary_profile:
    input:
        plan=auxiliary_acquisition_plan,
        sources=auxiliary_rule_cleaned_files,
    output:
        profile=(
            "<resources>/automatic/{shape}/"
            "auxiliary/constructed/"
            "{rule_name}.parquet"
        ),
    conda:
        "../envs/module.yaml"
    params:
        frequency=config["temporal_scope"]["frequency"],
        advanced_sources=(config["gap_filling"]["advanced"]["sources"]),
    message:
        "Construct auxiliary demand profile for {wildcards.rule_name}."
    script:
        "../scripts/construct_auxiliary_profile.py"


rule apply_advanced_overrides:
    input:
        demand=rules.clean_demand.output.demand,
        data_source=rules.clean_demand.output.data_source,
        cleaning_method=rules.clean_demand.output.cleaning_method,
        plan=auxiliary_acquisition_plan,
        constructed_profiles=advanced_constructed_profiles,
        external_profiles=advanced_external_profile_files,
    output:
        demand=("<resources>/automatic/{shape}/" "load_advanced_cleaned.parquet"),
        cleaning_method=(
            "<resources>/automatic/{shape}/" "load_advanced_cleaning_method.parquet"
        ),
    conda:
        "../envs/module.yaml"
    params:
        temporal_scope=config["temporal_scope"],
    message:
        "Apply advanced electricity-demand overrides."
    script:
        "../scripts/apply_advanced_overrides.py"
