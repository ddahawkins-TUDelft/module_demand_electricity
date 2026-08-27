"""Prepare downloaded ENTSO-E electricity-demand data."""

from pathlib import Path

import pandas as pd
from tclean import TimeGrid


def prepare_entsoe(
    *,
    input_path: str | Path,
    output_path: str | Path,
    grid: TimeGrid,
    country_codes: list[str],
) -> None:
    """Prepare ENTSO-E demand on the configured target grid."""
    data = pd.read_parquet(input_path)

    data.index = pd.to_datetime(data.index, utc=True)

    data = data.resample("1h").mean()

    data = data.reindex(index=grid.target_index, columns=country_codes)

    data = data.astype(float)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data.to_parquet(output_path)
