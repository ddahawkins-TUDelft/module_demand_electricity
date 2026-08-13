import pandas as pd
from cleaning.advanced.methods.construct_from_sources import construct_from_sources
from cleaning.advanced.planning.manifest import get_rule_override, load_execution_plan
from common.time import build_hourly_index

loads = [pd.read_parquet(path) for path in snakemake.input.sources]

if not loads:
    raise ValueError("No cleaned auxiliary data were supplied.")

auxiliary = loads[0].copy()

for load in loads[1:]:
    auxiliary = auxiliary.combine_first(load)

plan = load_execution_plan(snakemake.input.plan)

override = get_rule_override(plan, rule_name=snakemake.wildcards.rule_name)

target_index = build_hourly_index(start=override["start"], end=override["end"])

profile = construct_from_sources(
    auxiliary,
    target_index=target_index,
    sources=override["sources"],
    scaling=override.get("scaling"),
)

profile.to_frame(name=override["country"]).to_parquet(snakemake.output.profile)
