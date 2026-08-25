import json


def _read_auxiliary_plan(_wildcards=None):
    """Read the resolved advanced execution plan."""
    plan_file = checkpoints.plan_auxiliary_data.get().output.plan

    with plan_file.open() as file:
        return json.load(file)


def auxiliary_acquisition_plan(_wildcards):
    """Return the execution plan after the checkpoint completes."""
    return checkpoints.plan_auxiliary_data.get().output.plan


def auxiliary_neso_raw_files(wildcards):
    """Return annual NESO files required by one auxiliary batch."""
    plan = _read_auxiliary_plan()

    batch = next(
        batch
        for batch in plan["batches"]
        if (batch["batch_id"] == wildcards.batch_id and batch["source"] == "neso")
    )

    return [
        ("<resources>/automatic/neso/" f"historic_demand_{year}.csv")
        for year in batch["years"]
    ]


def auxiliary_group_source_files(wildcards):
    """Return prepared source files for one auxiliary group."""
    plan = _read_auxiliary_plan()

    batch_ids = plan["groups"][wildcards.group_id]

    batches_by_id = {batch["batch_id"]: batch for batch in plan["batches"]}

    return [
        (
            "<resources>/automatic/"
            f"auxiliary/{batches_by_id[batch_id]['source']}/"
            f"{batch_id}.parquet"
        )
        for batch_id in batch_ids
    ]


def auxiliary_rule_cleaned_files(wildcards):
    """Return cleaned auxiliary files required by one advanced override."""
    plan = _read_auxiliary_plan()

    group_ids = plan["rules"][wildcards.rule_name]["required_group_ids"]

    return [
        ("<resources>/automatic/" "auxiliary/cleaned/" f"{group_id}.parquet")
        for group_id in group_ids
    ]


def advanced_constructed_profiles(_wildcards):
    """Return constructed profiles required by active advanced overrides."""
    plan = _read_auxiliary_plan()

    return [
        ("<resources>/automatic/" "auxiliary/constructed/" f"{rule_name}.parquet")
        for rule_name in plan["constructed_profile_rule_names"]
    ]


def final_clean_demand_input(_wildcards):
    """Return the cleaned demand appropriate for the configured mode."""
    if config["gap_filling"]["mode"] == "advanced":
        return "<resources>/automatic/" "load_advanced_cleaned.parquet"

    return rules.clean_demand.output.demand


def final_cleaning_method_input(_wildcards):
    """Return cleaning provenance appropriate for the configured mode."""
    if config["gap_filling"]["mode"] == "advanced":
        return "<resources>/automatic/" "load_advanced_cleaning_method.parquet"

    return rules.clean_demand.output.cleaning_method


def advanced_external_profile_files(_wildcards):
    plan = _read_auxiliary_plan()

    return list(dict.fromkeys(plan["external_profile_files"].values()))


def auxiliary_entsoe_threads(wildcards):
    """Return useful ENTSO-E threads for one auxiliary batch."""
    plan = _read_auxiliary_plan()

    batch = next(
        batch
        for batch in plan["batches"]
        if (batch["batch_id"] == wildcards.batch_id and batch["source"] == "entsoe")
    )

    return min(
        internal["load_entsoe"]["MAX_WORKERS"],
        len(batch["countries"]),
    )


checkpoint plan_auxiliary_data:
    input:
        fill_plan=rules.clean_demand.output.auxiliary_fill_plan,
    output:
        plan=("<resources>/automatic/" "auxiliary/advanced_execution_plan.json"),
    conda:
        "../envs/module.yaml"
    params:
        gap_filling=config["gap_filling"],
        source_names=config["load_sources"],
    message:
        "Plan auxiliary electricity-demand acquisition."
    script:
        "../scripts/plan_auxiliary_data.py"


rule finalise_clean_demand:
    input:
        demand=final_clean_demand_input,
        cleaning_method=final_cleaning_method_input,
    output:
        demand=("<resources>/automatic/" "load_cleaned.parquet"),
        cleaning_method=("<resources>/automatic/" "load_final_cleaning_method.parquet"),
        cleaning_method_rank=(
            "<resources>/automatic/" "load_final_cleaning_method_rank.parquet"
        ),
    conda:
        "../envs/module.yaml"
    params:
        source_names=config["load_sources"],
        gap_filling=config["gap_filling"],
    message:
        "Finalise cleaned electricity demand and provenance."
    script:
        "../scripts/finalise_clean_demand.py"


rule download_auxiliary_load_entsoe:
    input:
        token_entsoe="<token_entsoe>",
        plan=auxiliary_acquisition_plan,
    output:
        raw_load=(
            "<resources>/automatic/"
            "auxiliary/entsoe/raw/"
            "{batch_id}.parquet"
        ),
    log:
        (
            "<logs>/auxiliary/"
            "entsoe/download_{batch_id}.log"
        ),
    localrule: True
    conda:
        "../envs/module.yaml"
    threads:
        auxiliary_entsoe_threads
    params:
        frequency=config["temporal_scope"]["frequency"],
    message:
        "Download auxiliary electricity load from ENTSO-E."
    script:
        "../scripts/download_load_entsoe.py"


rule prepare_auxiliary_load_entsoe:
    input:
        plan=auxiliary_acquisition_plan,
        raw_load=rules.download_auxiliary_load_entsoe.output.raw_load,
    output:
        load=(
            "<resources>/automatic/"
            "auxiliary/entsoe/"
            "{batch_id}.parquet"
        ),
    log:
        (
            "<logs>/auxiliary/"
            "entsoe/prepare_{batch_id}.log"
        ),
    conda:
        "../envs/module.yaml"
    params:
        frequency=config["temporal_scope"]["frequency"],
    message:
        "Prepare auxiliary electricity-demand data from ENTSO-E."
    script:
        "../scripts/prepare_load_entsoe.py"


rule prepare_auxiliary_load_opsd:
    input:
        load=rules.download_load_opsd.output.load,
        plan=auxiliary_acquisition_plan,
    output:
        load=("<resources>/automatic/" "auxiliary/opsd/" "{batch_id}.parquet"),
    log:
        ("<logs>/auxiliary/" "opsd/{batch_id}.log"),
    conda:
        "../envs/module.yaml"
    params:
        frequency=config["temporal_scope"]["frequency"],
    message:
        "Prepare auxiliary electricity-demand data from OPSD."
    script:
        "../scripts/prepare_load_opsd.py"


rule prepare_auxiliary_load_neso:
    input:
        plan=auxiliary_acquisition_plan,
        annual_files=auxiliary_neso_raw_files,
    output:
        load=(
            "<resources>/automatic/"
            "auxiliary/neso/"
            "{batch_id}.parquet"
        ),
    log:
        "<logs>/auxiliary/neso/{batch_id}.log",
    conda:
        "../envs/module.yaml"
    params:
        frequency=config["temporal_scope"]["frequency"],
    message:
        "Prepare auxiliary electricity-demand data from NESO."
    script:
        "../scripts/prepare_load_neso.py"


rule combine_auxiliary_sources:
    input:
        plan=auxiliary_acquisition_plan,
        sources=auxiliary_group_source_files,
    output:
        demand=("<resources>/automatic/" "auxiliary/combined/" "{group_id}.parquet"),
        data_source=(
            "<resources>/automatic/"
            "auxiliary/combined/"
            "{group_id}_data_source.parquet"
        ),
        cleaning_method=(
            "<resources>/automatic/"
            "auxiliary/combined/"
            "{group_id}_cleaning_method.parquet"
        ),
    conda:
        "../envs/module.yaml"
    params:
        source_priority=config["load_sources"],
    message:
        "Combine auxiliary electricity-demand sources."
    script:
        "../scripts/combine_auxiliary_sources.py"


rule clean_auxiliary_data:
    input:
        demand=("<resources>/automatic/" "auxiliary/combined/" "{group_id}.parquet"),
        cleaning_method=(
            "<resources>/automatic/"
            "auxiliary/combined/"
            "{group_id}_cleaning_method.parquet"
        ),
    output:
        demand=("<resources>/automatic/" "auxiliary/cleaned/" "{group_id}.parquet"),
        cleaning_method=(
            "<resources>/automatic/"
            "auxiliary/cleaned/"
            "{group_id}_cleaning_method.parquet"
        ),
    conda:
        "../envs/module.yaml"
    params:
        basic_rules=config["gap_filling"]["basic"]["rules"],
        enabled=(
            config["gap_filling"]["advanced"]["auxiliary_data"]["basic_cleaning"][
                "enabled"
            ]
        ),
    message:
        "Apply basic cleaning to auxiliary electricity demand."
    script:
        "../scripts/clean_auxiliary_data.py"


rule construct_auxiliary_profile:
    input:
        plan=auxiliary_acquisition_plan,
        sources=auxiliary_rule_cleaned_files,
    output:
        profile=(
            "<resources>/automatic/" "auxiliary/constructed/" "{rule_name}.parquet"
        ),
    conda:
        "../envs/module.yaml"
    message:
        "Construct auxiliary demand profile for {wildcards.rule_name}."
    script:
        "../scripts/construct_auxiliary_profile.py"


rule apply_advanced_overrides:
    input:
        demand=("<resources>/automatic/" "load_basic_cleaned.parquet"),
        cleaning_method=("<resources>/automatic/" "load_cleaning_method.parquet"),
        plan=auxiliary_acquisition_plan,
        constructed_profiles=advanced_constructed_profiles,
        external_profiles=advanced_external_profile_files,
    output:
        demand=("<resources>/automatic/" "load_advanced_cleaned.parquet"),
        cleaning_method=(
            "<resources>/automatic/" "load_advanced_cleaning_method.parquet"
        ),
    conda:
        "../envs/module.yaml"
    message:
        "Apply advanced electricity-demand overrides."
    script:
        "../scripts/apply_advanced_overrides.py"
