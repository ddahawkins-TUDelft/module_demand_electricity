import json

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