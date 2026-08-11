import json

from cleaning.advanced.planning.selection import (
    get_auxiliary_batch,
    get_auxiliary_group_batches,
    get_auxiliary_group_ids,
    get_required_auxiliary_group_ids,
    get_source_batch_ids,
)


def _read_plan_file(plan_path):
    with open(plan_path, encoding="utf-8") as file:
        return json.load(file)


def _read_auxiliary_plan(_wildcards=None):
    """Read the resolved auxiliary acquisition plan."""
    plan_path = (
        checkpoints
        .plan_auxiliary_data
        .get()
        .output
        .plan
    )

    return _read_plan_file(plan_path)


def auxiliary_acquisition_plan(_wildcards):
    """Return the acquisition plan after the checkpoint completes."""
    return (
        checkpoints
        .plan_auxiliary_data
        .get()
        .output
        .plan
    )


def get_auxiliary_entsoe_batch(
    wildcards,
    input,
) -> dict:
    """Return the ENTSO-E batch for this job."""
    return get_auxiliary_batch(
        _read_plan_file(input.plan),
        batch_id=wildcards.batch_id,
        source="entsoe_api",
    )


def auxiliary_entsoe_outputs(wildcards):
    """Return all ENTSO-E outputs required by the acquisition plan."""
    plan = _read_auxiliary_plan(wildcards)

    batch_ids = get_source_batch_ids(
        plan,
        source="entsoe_api",
    )

    return [
        (
            "<resources>/automatic/"
            "auxiliary/entsoe_api/"
            f"{batch_id}.parquet"
        )
        for batch_id in batch_ids
    ]


def get_auxiliary_opsd_batch(
    wildcards,
    input,
) -> dict:
    """Return the OPSD batch for this job."""
    return get_auxiliary_batch(
        _read_plan_file(input.plan),
        batch_id=wildcards.batch_id,
        source="opsd_api",
    )


def auxiliary_opsd_outputs(wildcards):
    """Return all OPSD outputs required by the acquisition plan."""
    plan = _read_auxiliary_plan(wildcards)

    batch_ids = get_source_batch_ids(
        plan,
        source="opsd_api",
    )

    return [
        (
            "<resources>/automatic/"
            "auxiliary/opsd_api/"
            f"{batch_id}.parquet"
        )
        for batch_id in batch_ids
    ]


def get_auxiliary_neso_batch(
    wildcards,
    input,
) -> dict:
    """Return the NESO batch for this job."""
    return get_auxiliary_batch(
        _read_plan_file(input.plan),
        batch_id=wildcards.batch_id,
        source="neso",
    )


def auxiliary_neso_raw_files(wildcards):
    """Return annual NESO files required by one auxiliary batch."""
    plan = _read_auxiliary_plan(wildcards)

    batch = get_auxiliary_batch(
        plan,
        batch_id=wildcards.batch_id,
        source="neso",
    )

    years = _years_in_period(
        batch["start"],
        batch["end"],
    )

    return [
        (
            "<resources>/automatic/neso/"
            f"historic_demand_{year}.csv"
        )
        for year in years
    ]


def auxiliary_neso_outputs(wildcards):
    """Return all NESO outputs required by the acquisition plan."""
    plan = _read_auxiliary_plan(wildcards)

    batch_ids = get_source_batch_ids(
        plan,
        source="neso",
    )

    return [
        (
            "<resources>/automatic/"
            "auxiliary/neso/"
            f"{batch_id}.parquet"
        )
        for batch_id in batch_ids
    ]


def auxiliary_group_source_files(wildcards):
    """Return prepared source files for one auxiliary group."""
    plan = _read_auxiliary_plan(wildcards)

    batches = get_auxiliary_group_batches(
        plan,
        group_id=wildcards.group_id,
    )

    return [
        (
            "<resources>/automatic/"
            f"auxiliary/{batch['source']}/"
            f"{batch['batch_id']}.parquet"
        )
        for batch in batches
    ]


def auxiliary_combined_outputs(wildcards):
    """Return all combined auxiliary group outputs."""
    plan = _read_auxiliary_plan(wildcards)

    group_ids = get_auxiliary_group_ids(plan)

    return [
        (
            "<resources>/automatic/"
            "auxiliary/combined/"
            f"{group_id}.parquet"
        )
        for group_id in group_ids
    ]


def auxiliary_rule_cleaned_files(wildcards):
    """Return cleaned auxiliary files required by one advanced override."""
    plan = _read_auxiliary_plan(wildcards)

    override = config["gap_filling"]["advanced"]["overrides"][
        wildcards.rule_name
    ]

    group_ids = get_required_auxiliary_group_ids(
        plan,
        override=override,
    )

    return [
        (
            "<resources>/automatic/"
            "auxiliary/cleaned/"
            f"{group_id}.parquet"
        )
        for group_id in group_ids
    ]


def advanced_constructed_profiles(wildcards):
    """Return constructed profiles required by active advanced overrides."""
    plan = _read_auxiliary_plan(wildcards)

    active_rule_names = set(
        plan["active_rule_names"]
    )

    overrides = (
        config["gap_filling"]
        ["advanced"]
        ["overrides"]
    )

    return [
        (
            "<resources>/automatic/"
            "auxiliary/constructed/"
            f"{rule_name}.parquet"
        )
        for rule_name, override in overrides.items()
        if (
            rule_name in active_rule_names
            and override["method"] == "construct_from_sources"
        )
    ]


def final_clean_demand_input(_wildcards):
    """Return the cleaned demand appropriate for the configured mode."""
    if config["gap_filling"]["mode"] == "advanced":
        return (
            "<resources>/automatic/"
            "load_advanced_cleaned.parquet"
        )

    return rules.clean_demand.output.demand


def final_cleaning_method_input(_wildcards):
    """Return cleaning provenance appropriate for the configured mode."""
    if config["gap_filling"]["mode"] == "advanced":
        return (
            "<resources>/automatic/"
            "load_advanced_cleaning_method.parquet"
        )

    return rules.clean_demand.output.cleaning_method


checkpoint plan_auxiliary_data:
    input:
        fill_plan=rules.clean_demand.output.auxiliary_fill_plan,
    output:
        plan=(
            "<resources>/automatic/"
            "auxiliary/acquisition_plan.json"
        ),
    params:
        gap_filling=config["gap_filling"],
        source_names=config["load_sources"],
    conda:
        "../envs/module.yaml"
    message:
        "Plan auxiliary electricity-demand acquisition."
    script:
        "../scripts/plan_auxiliary_data.py"


rule finalise_clean_demand:
    input:
        demand=final_clean_demand_input,
        cleaning_method=final_cleaning_method_input,
    output:
        demand=(
            "<resources>/automatic/"
            "load_cleaned.parquet"
        ),
        cleaning_method=(
            "<resources>/automatic/"
            "load_final_cleaning_method.parquet"
        ),
        cleaning_method_rank=(
            "<resources>/automatic/"
            "load_final_cleaning_method_rank.parquet"
        ),
    params:
        source_names=config["load_sources"],
        gap_filling=config["gap_filling"],
    conda:
        "../envs/module.yaml"
    message:
        "Finalise cleaned electricity demand and provenance."
    script:
        "../scripts/finalise_clean_demand.py"


rule download_auxiliary_load_entsoe_api:
    input:
        token_entsoe="<token_entsoe>",
        plan=auxiliary_acquisition_plan,
    output:
        load=(
            "<resources>/automatic/"
            "auxiliary/entsoe_api/"
            "{batch_id}.parquet"
        ),
    params:
        temporal_start=lambda wildcards, input: (
            get_auxiliary_entsoe_batch(
                wildcards,
                input,
            )["start"]
        ),
        temporal_end=lambda wildcards, input: (
            get_auxiliary_entsoe_batch(
                wildcards,
                input,
            )["end"]
        ),
        country_codes=lambda wildcards, input: (
            get_auxiliary_entsoe_batch(
                wildcards,
                input,
            )["countries"]
        ),
    log:
        (
            "<logs>/auxiliary/"
            "entsoe_api/{batch_id}.log"
        ),
    localrule: True
    conda:
        "../envs/module.yaml"
    message:
        "Download auxiliary electricity load from ENTSO-E."
    script:
        "../scripts/download_load_entsoe_api.py"


rule prepare_auxiliary_load_opsd:
    input:
        load=rules.download_load_entsoe_opsd.output.load,
        plan=auxiliary_acquisition_plan,
    output:
        load=(
            "<resources>/automatic/"
            "auxiliary/opsd_api/"
            "{batch_id}.parquet"
        ),
    params:
        start=lambda wildcards, input: (
            get_auxiliary_opsd_batch(
                wildcards,
                input,
            )["start"]
        ),
        end=lambda wildcards, input: (
            get_auxiliary_opsd_batch(
                wildcards,
                input,
            )["end"]
        ),
        country_codes=lambda wildcards, input: (
            get_auxiliary_opsd_batch(
                wildcards,
                input,
            )["countries"]
        ),
    log:
        (
            "<logs>/auxiliary/"
            "opsd_api/{batch_id}.log"
        ),
    conda:
        "../envs/module.yaml"
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
    params:
        start=lambda wildcards, input: (
            get_auxiliary_neso_batch(
                wildcards,
                input,
            )["start"]
        ),
        end=lambda wildcards, input: (
            get_auxiliary_neso_batch(
                wildcards,
                input,
            )["end"]
        ),
        country_codes=lambda wildcards, input: (
            get_auxiliary_neso_batch(
                wildcards,
                input,
            )["countries"]
        ),
    log:
        (
            "<logs>/auxiliary/"
            "neso/{batch_id}.log"
        ),
    conda:
        "../envs/module.yaml"
    message:
        "Prepare auxiliary electricity-demand data from NESO."
    script:
        "../scripts/prepare_load_neso.py"


rule combine_auxiliary_sources:
    input:
        plan=auxiliary_acquisition_plan,
        sources=auxiliary_group_source_files,
    output:
        demand=(
            "<resources>/automatic/"
            "auxiliary/combined/"
            "{group_id}.parquet"
        ),
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
    params:
        source_priority=config["load_sources"],
    conda:
        "../envs/module.yaml"
    message:
        "Combine auxiliary electricity-demand sources."
    script:
        "../scripts/combine_auxiliary_sources.py"


rule clean_auxiliary_data:
    input:
        demand=(
            "<resources>/automatic/"
            "auxiliary/combined/"
            "{group_id}.parquet"
        ),
        cleaning_method=(
            "<resources>/automatic/"
            "auxiliary/combined/"
            "{group_id}_cleaning_method.parquet"
        ),
    output:
        demand=(
            "<resources>/automatic/"
            "auxiliary/cleaned/"
            "{group_id}.parquet"
        ),
        cleaning_method=(
            "<resources>/automatic/"
            "auxiliary/cleaned/"
            "{group_id}_cleaning_method.parquet"
        ),
    params:
        basic_rules=config["gap_filling"]["basic"]["rules"],
        enabled=(
            config["gap_filling"]
            ["advanced"]
            ["auxiliary_data"]
            ["basic_cleaning"]
            ["enabled"]
        ),
    conda:
        "../envs/module.yaml"
    message:
        "Apply basic cleaning to auxiliary electricity demand."
    script:
        "../scripts/clean_auxiliary_data.py"

rule construct_auxiliary_profile:
    input:
        sources=auxiliary_rule_cleaned_files,
    output:
        profile=(
            "<resources>/automatic/"
            "auxiliary/constructed/"
            "{rule_name}.parquet"
        ),
    params:
        override=lambda wildcards: (
            config["gap_filling"]
            ["advanced"]
            ["overrides"]
            [wildcards.rule_name]
        ),
    conda:
        "../envs/module.yaml"
    message:
        "Construct auxiliary demand profile for {wildcards.rule_name}."
    script:
        "../scripts/construct_auxiliary_profile.py"


rule apply_advanced_overrides:
    input:
        demand=(
            "<resources>/automatic/"
            "load_basic_cleaned.parquet"
        ),
        cleaning_method=(
            "<resources>/automatic/"
            "load_cleaning_method.parquet"
        ),
        plan=auxiliary_acquisition_plan,
        profiles=advanced_constructed_profiles,
    output:
        demand=(
            "<resources>/automatic/"
            "load_advanced_cleaned.parquet"
        ),
        cleaning_method=(
            "<resources>/automatic/"
            "load_advanced_cleaning_method.parquet"
        ),
    params:
        overrides=(
            config["gap_filling"]
            ["advanced"]
            ["overrides"]
        ),
    conda:
        "../envs/module.yaml"
    message:
        "Apply advanced electricity-demand overrides."
    script:
        "../scripts/apply_advanced_overrides.py"