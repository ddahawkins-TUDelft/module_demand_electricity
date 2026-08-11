import json
from pathlib import Path

import pandas as pd
from cleaning.advanced.apply import apply_auxiliary_fill_rules

load = pd.read_parquet(
    snakemake.input.demand
)

cleaning_method = pd.read_parquet(
    snakemake.input.cleaning_method
)

with open(
    snakemake.input.plan,
    encoding="utf-8",
) as file:
    plan = json.load(file)

active_rule_names = set(
    plan["active_rule_names"]
)

unknown_rule_names = (
    active_rule_names
    - set(snakemake.params.overrides)
)

if unknown_rule_names:
    raise ValueError(
        "Auxiliary acquisition plan references unknown advanced "
        f"overrides: {sorted(unknown_rule_names)}."
    )

active_overrides = {
    rule_name: override
    for rule_name, override in snakemake.params.overrides.items()
    if rule_name in active_rule_names
}

profiles = {
    Path(path).stem: pd.read_parquet(path).iloc[:, 0]
    for path in snakemake.input.profiles
}

filled, cleaning_method = apply_auxiliary_fill_rules(
    load,
    cleaning_method,
    overrides=active_overrides,
    profiles=profiles,
)

filled.to_parquet(
    snakemake.output.demand
)

cleaning_method.to_parquet(
    snakemake.output.cleaning_method
)
