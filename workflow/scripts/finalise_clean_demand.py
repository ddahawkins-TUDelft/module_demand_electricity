import shutil

import pandas as pd
from cleaning.provenance import build_cleaning_method_ranks, derive_cleaning_method_rank

shutil.copyfile(
    snakemake.input.demand,
    snakemake.output.demand,
)

cleaning_method = pd.read_parquet(
    snakemake.input.cleaning_method
)

gap_filling = snakemake.params.gap_filling

rules = list(
    gap_filling["basic"]["rules"]
)

if gap_filling["mode"] == "advanced":
    rules.extend(
        {
            "name": rule_name,
            **override,
        }
        for rule_name, override in (
            gap_filling["advanced"]["overrides"].items()
        )
    )

ranks = build_cleaning_method_ranks(
    source_priority=snakemake.params.source_names,
    rules=rules,
)

cleaning_method_rank = derive_cleaning_method_rank(
    cleaning_method=cleaning_method,
    ranks=ranks,
)

cleaning_method.to_parquet(
    snakemake.output.cleaning_method
)

cleaning_method_rank.to_parquet(
    snakemake.output.cleaning_method_rank
)