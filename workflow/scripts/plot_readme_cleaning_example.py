"""Create a curated cleaning-timeline figure for the README.

Temporary development utility. Run from tests/integration/.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from _plot_timeline import (
    _add_mean_load_labels,
    _add_normalised_demand_traces,
    _build_cleaning_method_metadata,
    _build_legend_handles,
    _build_rank_colours,
    _encode_rank_background,
    _plot_cleaning_background,
    _validate_alignment,
)

DEMAND_PATH = Path("resources/module/resources/automatic/load_cleaned.parquet")

CLEANING_METHOD_PATH = Path(
    "resources/module/resources/automatic/load_final_cleaning_method.parquet"
)

CLEANING_METHOD_RANK_PATH = Path(
    "resources/module/resources/automatic/load_final_cleaning_method_rank.parquet"
)

OUTPUT_PATH = Path("tmp/readme_cleaning_timeline.png")

# Curated subset for the README figure.
COUNTRIES = ["ALB", "GBR", "IRL", "MKD", "DEU"]

START = "2021-05-01"
END = "2021-11-01"

# Must correspond to the configuration used for the long run.
SOURCE_NAMES = ["entsoe", "neso", "opsd"]

GAP_FILLING_CONFIG = {
    "mode": "basic",
    "basic": {
        "rules": [
            {
                "name": "interpolate_short_gaps",
                "method": "linear_interpolation",
                "max_gap": "3h",
            },
            {
                "name": "average_adjacent_weeks",
                "method": "average_periods",
                "max_gap": "326h",
                "source_offsets": ["-7d", "7d"],
            },
            {
                "name": "copy_previous_week",
                "method": "copy_periods",
                "max_gap": "168h",
                "source_offset": "-168h",
            },
            {
                "name": "copy_following_week",
                "method": "copy_periods",
                "max_gap": "168h",
                "source_offset": "168h",
            },
        ]
    },
}


def main() -> None:
    """Main function for generating README figure."""
    demand = pd.read_parquet(DEMAND_PATH)
    cleaning_method = pd.read_parquet(CLEANING_METHOD_PATH)
    cleaning_method_rank = pd.read_parquet(CLEANING_METHOD_RANK_PATH)

    print("Available period:", demand.index.min(), "to", demand.index.max())
    print("Available countries:", ", ".join(demand.columns))

    missing_countries = [
        country for country in COUNTRIES if country not in demand.columns
    ]

    if missing_countries:
        raise ValueError(
            "Requested README countries are unavailable: "
            + ", ".join(missing_countries)
        )

    start = pd.Timestamp(START, tz="UTC")
    end = pd.Timestamp(END, tz="UTC")

    mask = (demand.index >= start) & (demand.index < end)

    demand = demand.loc[mask, COUNTRIES]
    cleaning_method = cleaning_method.loc[mask, COUNTRIES]
    cleaning_method_rank = cleaning_method_rank.loc[mask, COUNTRIES]

    if len(demand) < 2:
        raise ValueError(f"No usable data found between {START} and {END}.")

    print(f"Plotting {len(demand):,} hourly timestamps for {len(COUNTRIES)} countries.")

    # Useful while choosing the README window/countries.
    print("\nCleaning-method counts:")
    for country in COUNTRIES:
        counts = cleaning_method[country].value_counts(dropna=False)
        print(f"\n{country}")
        print(counts.to_string())

    _validate_alignment(
        demand=demand,
        cleaning_method=cleaning_method,
        cleaning_method_rank=cleaning_method_rank,
    )

    metadata = _build_cleaning_method_metadata(
        source_names=SOURCE_NAMES, gap_filling_config=GAP_FILLING_CONFIG
    )

    rank_colours = _build_rank_colours(metadata)

    background, background_cmap = _encode_rank_background(
        cleaning_method_rank=cleaning_method_rank,
        metadata=metadata,
        rank_colours=rank_colours,
    )

    figure, axis = _plot_cleaning_background(
        demand=demand, background=background, background_cmap=background_cmap
    )

    mean_load_gw = _add_normalised_demand_traces(axis=axis, demand=demand)

    _add_mean_load_labels(
        axis=axis, mean_load_gw=mean_load_gw, countries=demand.columns
    )

    legend_handles = _build_legend_handles(metadata, rank_colours)

    figure.legend(
        handles=legend_handles,
        loc="center left",
        bbox_to_anchor=(1.01, 0.5),
        frameon=False,
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    figure.savefig(OUTPUT_PATH, dpi=200, bbox_inches="tight")

    plt.close(figure)

    print(f"\nSaved README figure to: {OUTPUT_PATH.resolve()}")


if __name__ == "__main__":
    main()
