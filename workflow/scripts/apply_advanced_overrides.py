from pathlib import Path

import pandas as pd
from cleaning.advanced.apply import apply_auxiliary_fill_rules
from cleaning.advanced.planning.manifest import (
    get_active_overrides,
    load_execution_plan,
)

load = pd.read_parquet(
    snakemake.input.demand
)

cleaning_method = pd.read_parquet(
    snakemake.input.cleaning_method
)

plan = load_execution_plan(
    snakemake.input.plan
)

active_overrides = get_active_overrides(
    plan
)

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
