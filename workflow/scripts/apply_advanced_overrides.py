"""Apply advanced T-Clean rules to basic-cleaned demand."""

import json
from pathlib import Path

import pandas as pd
from tclean import TimeGrid
from tclean.advanced import read_external_profile
from tclean.advanced.apply import apply_advanced_rules

with open(snakemake.input.plan, encoding="utf-8") as file:
    plan = json.load(file)

grid = TimeGrid(
    start=snakemake.params.temporal_scope["start"],
    end=snakemake.params.temporal_scope["end"],
    frequency=snakemake.params.temporal_scope["frequency"],
)

data = pd.read_parquet(snakemake.input.demand)
data_source = pd.read_parquet(snakemake.input.data_source)
cleaning_method = pd.read_parquet(snakemake.input.cleaning_method)

rules = pd.DataFrame(
    [
        {
            "rule_name": rule_name,
            "method": plan["rules"][rule_name]["method"],
            "source": plan["rules"][rule_name]["source"],
            "context": plan["rules"][rule_name]["context"],
            "start": plan["rules"][rule_name]["start"],
            "end": plan["rules"][rule_name]["end"],
            "scope": plan["rules"][rule_name]["scope"],
        }
        for rule_name in plan["active_rule_names"]
    ]
)

advanced_sources = {}

for path in snakemake.input.constructed_profiles:
    rule_name = Path(path).stem
    rule = plan["rules"][rule_name]
    source_name = rule["source"]

    profile = pd.read_parquet(path)

    if profile.shape[1] != 1:
        raise ValueError(
            f"Constructed profile for rule {rule_name!r} "
            "must contain exactly one column."
        )

    advanced_sources[source_name] = profile.iloc[:, 0]

for source_name, path in plan["external_profile_files"].items():
    advanced_sources[source_name] = read_external_profile(
        path,
        grid=grid,
    )

filled, _, cleaning_method = apply_advanced_rules(
    data,
    data_source,
    cleaning_method,
    rules=rules,
    advanced_sources=advanced_sources,
    grid=grid,
)

filled.to_parquet(snakemake.output.demand)
cleaning_method.to_parquet(snakemake.output.cleaning_method)
