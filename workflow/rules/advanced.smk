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