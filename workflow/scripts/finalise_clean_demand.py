import shutil
from pathlib import Path

source = Path(snakemake.input.demand)
target = Path(snakemake.output.demand)

target.parent.mkdir(
    parents=True,
    exist_ok=True,
)

shutil.copyfile(
    source,
    target,
)
