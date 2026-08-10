from pathlib import Path

import pandas as pd
from cleaning.advanced.apply import apply_auxiliary_fill_rules

load = pd.read_parquet(
    snakemake.input.demand
)

cleaning_method = pd.read_parquet(
    snakemake.input.cleaning_method
)

profiles = {
    Path(path).stem: pd.read_parquet(path).iloc[:, 0]
    for path in snakemake.input.profiles
}

filled, cleaning_method = apply_auxiliary_fill_rules(
    load,
    cleaning_method,
    overrides=snakemake.params.overrides,
    profiles=profiles,
)

filled.to_parquet(
    snakemake.output.demand
)

cleaning_method.to_parquet(
    snakemake.output.cleaning_method
)
