import json
import pandas as pd

def auxiliary_acquisition_plan(_wildcards):
    """Return the acquisition plan after the checkpoint completes."""
    return (
        checkpoints
        .plan_auxiliary_data
        .get()
        .output
        .plan
    )


def get_auxiliary_batch(
    plan_path,
    *,
    batch_id: str,
    source: str,
) -> dict:
    """Return one source batch from the acquisition plan."""
    with open(
        plan_path,
        encoding="utf-8",
    ) as file:
        plan = json.load(file)

    matches = [
        batch
        for batch in plan["batches"]
        if (
            batch["batch_id"] == batch_id
            and batch["source"] == source
        )
    ]

    if len(matches) != 1:
        raise ValueError(
            "Expected exactly one auxiliary batch for "
            f"{source=} and {batch_id=}, found {len(matches)}."
        )

    return matches[0]


def get_auxiliary_entsoe_batch(
    wildcards,
    input,
) -> dict:
    """Return the ENTSO-E batch for this job."""
    return get_auxiliary_batch(
        input.plan,
        batch_id=wildcards.batch_id,
        source="entsoe_api",
    )


def auxiliary_entsoe_outputs(_wildcards):
    """Return all ENTSO-E outputs required by the acquisition plan."""
    plan_path = (
        checkpoints
        .plan_auxiliary_data
        .get()
        .output
        .plan
    )

    with open(
        plan_path,
        encoding="utf-8",
    ) as file:
        plan = json.load(file)

    batch_ids = [
        batch["batch_id"]
        for batch in plan["batches"]
        if batch["source"] == "entsoe_api"
    ]

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
        input.plan,
        batch_id=wildcards.batch_id,
        source="opsd_api",
    )


def auxiliary_opsd_outputs(_wildcards):
    """Return all OPSD outputs required by the acquisition plan."""
    plan_path = (
        checkpoints
        .plan_auxiliary_data
        .get()
        .output
        .plan
    )

    with open(
        plan_path,
        encoding="utf-8",
    ) as file:
        plan = json.load(file)

    batch_ids = [
        batch["batch_id"]
        for batch in plan["batches"]
        if batch["source"] == "opsd_api"
    ]

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
        input.plan,
        batch_id=wildcards.batch_id,
        source="neso",
    )


def auxiliary_neso_raw_files(wildcards):
    """Return annual NESO files required by one auxiliary batch."""
    plan_path = (
        checkpoints
        .plan_auxiliary_data
        .get()
        .output
        .plan
    )

    batch = get_auxiliary_batch(
        plan_path,
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


def auxiliary_neso_outputs(_wildcards):
    """Return all NESO outputs required by the acquisition plan."""
    plan_path = (
        checkpoints
        .plan_auxiliary_data
        .get()
        .output
        .plan
    )

    with open(
        plan_path,
        encoding="utf-8",
    ) as file:
        plan = json.load(file)

    batch_ids = [
        batch["batch_id"]
        for batch in plan["batches"]
        if batch["source"] == "neso"
    ]

    return [
        (
            "<resources>/automatic/"
            "auxiliary/neso/"
            f"{batch_id}.parquet"
        )
        for batch_id in batch_ids
    ]


def get_auxiliary_group_batches(
    plan_path,
    *,
    group_id: str,
) -> list[dict]:
    """Return all acquisition batches belonging to one auxiliary group."""
    with open(plan_path, encoding="utf-8") as file:
        plan = json.load(file)

    batches = [
        batch
        for batch in plan["batches"]
        if batch["group_id"] == group_id
    ]

    if not batches:
        raise ValueError(
            f"No auxiliary batches found for group {group_id!r}."
        )

    return batches


def auxiliary_group_source_files(wildcards):
    """Return prepared source files for one auxiliary group."""
    plan_path = (
        checkpoints
        .plan_auxiliary_data
        .get()
        .output
        .plan
    )

    batches = get_auxiliary_group_batches(
        plan_path,
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


def auxiliary_combined_outputs(_wildcards):
    """Return all combined auxiliary group outputs."""
    plan_path = (
        checkpoints
        .plan_auxiliary_data
        .get()
        .output
        .plan
    )

    with open(plan_path, encoding="utf-8") as file:
        plan = json.load(file)

    group_ids = sorted(
        {
            batch["group_id"]
            for batch in plan["batches"]
        }
    )

    return [
        (
            "<resources>/automatic/"
            "auxiliary/combined/"
            f"{group_id}.parquet"
        )
        for group_id in group_ids
    ]


def auxiliary_rule_cleaned_files(wildcards):
    plan_path = checkpoints.plan_auxiliary_data.get().output.plan

    with open(plan_path, encoding="utf-8") as file:
        plan = json.load(file)

    override = (
        config["gap_filling"]
        ["advanced"]
        ["overrides"]
        [wildcards.rule_name]
    )

    group_ids = set()

    for source in override["sources"]:
        country = source["country"]
        start = pd.Timestamp(source["start"])

        if start.tzinfo is None:
            start = start.tz_localize("UTC")
        else:
            start = start.tz_convert("UTC")

        end = pd.Timestamp(source["end"])

        if end.tzinfo is None:
            end = end.tz_localize("UTC")
        else:
            end = end.tz_convert("UTC")

        matching_groups = {
            batch["group_id"]
            for batch in plan["batches"]
            if (
                country in batch["countries"]
                and pd.Timestamp(batch["start"]) <= start
                and pd.Timestamp(batch["end"]) >= end
            )
        }

        if len(matching_groups) != 1:
            raise ValueError(
                "Expected exactly one cleaned auxiliary group "
                f"covering {country!r} from {start} to {end}, "
                f"found {sorted(matching_groups)}."
            )

        group_ids.update(matching_groups)

    return [
        (
            "<resources>/automatic/"
            "auxiliary/cleaned/"
            f"{group_id}.parquet"
        )
        for group_id in sorted(group_ids)
    ]




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
        demand=rules.clean_demand.output.demand,
    output:
        demand=(
            "<resources>/automatic/"
            "load_cleaned.parquet"
        ),
    conda:
        "../envs/module.yaml"
    message:
        "Finalise cleaned electricity demand."
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