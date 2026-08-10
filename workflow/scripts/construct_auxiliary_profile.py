import pandas as pd
from cleaning.advanced.methods.construct_from_sources import construct_from_sources
from common.time import build_hourly_index

loads = [
    pd.read_parquet(path)
    for path in snakemake.input.sources
]

if not loads:
    raise ValueError(
        "No cleaned auxiliary data were supplied."
    )

auxiliary = loads[0].copy()

for load in loads[1:]:
    auxiliary = auxiliary.combine_first(load)

override = snakemake.params.override

target_index = build_hourly_index(
    start=override["start"],
    end=override["end"],
)

profile = construct_from_sources(
    auxiliary,
    target_index=target_index,
    sources=override["sources"],
)

profile.to_frame(
    name=override["country"]
).to_parquet(
    snakemake.output.profile
)
