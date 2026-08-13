import pandas as pd
from cleaning.basic.apply import fill_basic_gaps

load = pd.read_parquet(snakemake.input.demand)

cleaning_method = pd.read_parquet(snakemake.input.cleaning_method)

cleaned, cleaning_method = fill_basic_gaps(
    load,
    cleaning_method=cleaning_method,
    rules=snakemake.params.basic_rules,
    enabled=snakemake.params.enabled,
)

cleaned.to_parquet(snakemake.output.demand)

cleaning_method.to_parquet(snakemake.output.cleaning_method)
