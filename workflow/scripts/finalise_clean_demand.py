"""Generates the final cleaned parquet."""
import shutil

import pandas as pd
from cleaning.provenance import (
    build_cleaning_method_ranks,
    build_final_cleaning_rules,
    derive_cleaning_method_rank,
)

shutil.copyfile(snakemake.input.demand, snakemake.output.demand)

cleaning_method = pd.read_parquet(snakemake.input.cleaning_method)

gap_filling = snakemake.params.gap_filling

rules = build_final_cleaning_rules(gap_filling)

ranks = build_cleaning_method_ranks(
    source_priority=snakemake.params.source_names, rules=rules
)

cleaning_method_rank = derive_cleaning_method_rank(
    cleaning_method=cleaning_method, ranks=ranks
)

cleaning_method.to_parquet(snakemake.output.cleaning_method)

cleaning_method_rank.to_parquet(snakemake.output.cleaning_method_rank)
