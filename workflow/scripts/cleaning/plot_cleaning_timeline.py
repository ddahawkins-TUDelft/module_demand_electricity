"""Plot electricity demand and cleaning-method provenance through time."""

import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap, to_rgba
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

if TYPE_CHECKING:
    snakemake: Any

logger = logging.getLogger(__name__)


def main(
    *,
    demand_path: str | Path,
    cleaning_method_path: str | Path,
    cleaning_method_rank_path: str | Path,
    output_path: str | Path,
) -> None:
    """Create the electricity-demand cleaning diagnostic."""
    demand = pd.read_parquet(demand_path)
    cleaning_method = pd.read_parquet(cleaning_method_path)
    cleaning_method_rank = pd.read_parquet(
        cleaning_method_rank_path
    )

    _validate_alignment(
        demand=demand,
        cleaning_method=cleaning_method,
        cleaning_method_rank=cleaning_method_rank,
    )

    metadata = _build_rank_metadata(
        cleaning_method=cleaning_method,
        cleaning_method_rank=cleaning_method_rank,
    )

    rank_colours = _build_rank_colours(metadata)

    background, background_cmap = (
        _encode_rank_background(
            cleaning_method_rank=cleaning_method_rank,
            metadata=metadata,
            rank_colours=rank_colours,
        )
    )

    logger.info(
        "Loaded %s timestamps for %s countries.",
        len(demand),
        len(demand.columns),
    )

    logger.info(
        "Cleaning-method ranks:\n%s",
        metadata.to_string(index=False),
    )

    figure, axis = _plot_cleaning_background(
        demand=demand,
        background=background,
        background_cmap=background_cmap,
    )

    mean_load_gw = _add_normalised_demand_traces(
        axis=axis,
        demand=demand,
    )

    _add_mean_load_labels(
        axis=axis,
        mean_load_gw=mean_load_gw,
        countries=demand.columns,
    )

    _add_dynamic_legend(
        figure=figure,
        metadata=metadata,
        rank_colours=rank_colours,
    )

    output_path = Path(output_path)
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    figure.savefig(
        output_path,
        bbox_inches="tight",
    )

    plt.close(figure)

    logger.info(
        "Saved cleaning timeline to %s.",
        output_path,
    )


def _validate_alignment(
    *,
    demand: pd.DataFrame,
    cleaning_method: pd.DataFrame,
    cleaning_method_rank: pd.DataFrame,
) -> None:
    """Require all plot inputs to use the same time-country grid."""
    for name, frame in {
        "cleaning_method": cleaning_method,
        "cleaning_method_rank": cleaning_method_rank,
    }.items():
        if not frame.index.equals(demand.index):
            raise ValueError(
                f"{name} does not use the same time index "
                "as demand."
            )

        if not frame.columns.equals(demand.columns):
            raise ValueError(
                f"{name} does not use the same country columns "
                "as demand."
            )

    if not isinstance(demand.index, pd.DatetimeIndex):
        raise TypeError(
            "Demand must use a pandas DatetimeIndex."
        )

    if demand.index.has_duplicates:
        raise ValueError(
            "Demand timestamps must not contain duplicates."
        )

    if not demand.index.is_monotonic_increasing:
        raise ValueError(
            "Demand timestamps must be sorted."
        )

    if demand.columns.has_duplicates:
        raise ValueError(
            "Demand countries must not contain duplicates."
        )


def _build_rank_metadata(
    *,
    cleaning_method: pd.DataFrame,
    cleaning_method_rank: pd.DataFrame,
) -> pd.DataFrame:
    """Return one ordered record for each method and rank."""
    methods = cleaning_method.stack(
        future_stack=True
    ).rename("cleaning_method")

    ranks = cleaning_method_rank.stack(
        future_stack=True
    ).rename("cleaning_method_rank")

    metadata = (
        pd.concat(
            [methods, ranks],
            axis=1,
        )
        .dropna()
        .drop_duplicates()
    )

    if metadata.empty:
        raise ValueError(
            "No cleaning-method provenance was found."
        )

    metadata["cleaning_method_rank"] = metadata[
        "cleaning_method_rank"
    ].astype(int)

    rank_count_per_method = (
        metadata.groupby("cleaning_method")[
            "cleaning_method_rank"
        ]
        .nunique()
    )

    methods_with_multiple_ranks = (
        rank_count_per_method.loc[
            rank_count_per_method > 1
        ]
        .index
        .tolist()
    )

    if methods_with_multiple_ranks:
        raise ValueError(
            "Cleaning methods must map to exactly one rank. "
            "Methods with multiple ranks: "
            f"{methods_with_multiple_ranks}"
        )

    method_count_per_rank = (
        metadata.groupby("cleaning_method_rank")[
            "cleaning_method"
        ]
        .nunique()
    )

    ranks_with_multiple_methods = (
        method_count_per_rank.loc[
            method_count_per_rank > 1
        ]
        .index
        .tolist()
    )

    if ranks_with_multiple_methods:
        raise ValueError(
            "Cleaning-method ranks must map to exactly one "
            "method. Ranks with multiple methods: "
            f"{ranks_with_multiple_methods}"
        )

    metadata["category"] = metadata[
        "cleaning_method"
    ].map(_classify_method)

    return (
        metadata.sort_values("cleaning_method_rank")
        .reset_index(drop=True)
    )


def _classify_method(method: str) -> str:
    """Classify one method for semantic colour assignment."""
    if method == "missing":
        return "missing"

    if method.startswith("observed_"):
        return "observed"

    return "imputed"


def _build_rank_colours(
    metadata: pd.DataFrame,
) -> dict[int, tuple[float, float, float, float]]:
    """Assign colours according to method category and rank."""
    colours: dict[
        int,
        tuple[float, float, float, float],
    ] = {}

    observed = metadata.loc[
        metadata["category"] == "observed"
    ].sort_values("cleaning_method_rank")

    imputed = metadata.loc[
        metadata["category"] == "imputed"
    ].sort_values("cleaning_method_rank")

    missing = metadata.loc[
        metadata["category"] == "missing"
    ].sort_values("cleaning_method_rank")

    if not observed.empty:
        principal_rank = int(
            observed.iloc[0]["cleaning_method_rank"]
        )

        # The preferred observed source is visually neutral.
        colours[principal_rank] = to_rgba("white")

        fallback_observed = observed.iloc[1:]

        if not fallback_observed.empty:
            green_positions = np.linspace(
                0.3,
                0.6,
                len(fallback_observed),
            )

            for (_, row), position in zip(
                fallback_observed.iterrows(),
                green_positions,
                strict=True,
            ):
                rank = int(
                    row["cleaning_method_rank"]
                )

                colours[rank] = plt.colormaps[
                    "Greens"
                ](position)

    if not imputed.empty:
        imputation_positions = np.linspace(
            0.35,
            0.8,
            len(imputed),
        )

        for (_, row), position in zip(
            imputed.iterrows(),
            imputation_positions,
            strict=True,
        ):
            rank = int(
                row["cleaning_method_rank"]
            )

            colours[rank] = plt.colormaps[
                "YlOrBr"
            ](position)

    for _, row in missing.iterrows():
        rank = int(
            row["cleaning_method_rank"]
        )

        colours[rank] = plt.colormaps[
            "Reds"
        ](0.8)

    expected_ranks = set(
        metadata["cleaning_method_rank"]
    )

    unassigned_ranks = (
        expected_ranks - set(colours)
    )

    if unassigned_ranks:
        raise ValueError(
            "No colour was assigned to cleaning-method "
            "ranks: "
            f"{sorted(unassigned_ranks)}"
        )

    return colours


def _encode_rank_background(
    *,
    cleaning_method_rank: pd.DataFrame,
    metadata: pd.DataFrame,
    rank_colours: dict[
        int,
        tuple[float, float, float, float],
    ],
) -> tuple[np.ndarray, ListedColormap]:
    """Encode ranks as contiguous plotting codes."""
    rank_order = (
        metadata["cleaning_method_rank"]
        .astype(int)
        .tolist()
    )

    rank_to_code = {
        rank: code
        for code, rank in enumerate(rank_order)
    }

    encoded = cleaning_method_rank.apply(
        lambda column: column.map(rank_to_code)
    )

    if encoded.isna().any().any():
        present_ranks = set(
            cleaning_method_rank.stack(
                future_stack=True
            )
            .dropna()
            .astype(int)
            .unique()
        )

        unknown_ranks = sorted(
            present_ranks - set(rank_to_code)
        )

        raise ValueError(
            "Cleaning-method rank matrix contains ranks "
            "without metadata: "
            f"{unknown_ranks}"
        )

    colour_list = [
        rank_colours[rank]
        for rank in rank_order
    ]

    # Input frames are time × country, whereas imshow expects
    # country × time for this figure orientation.
    background = encoded.to_numpy(
        dtype=int
    ).T

    return (
        background,
        ListedColormap(colour_list),
    )


def _plot_cleaning_background(
    *,
    demand: pd.DataFrame,
    background: np.ndarray,
    background_cmap: ListedColormap,
) -> tuple[plt.Figure, plt.Axes]:
    """Plot cleaning-method ranks over time by country."""
    country_count = len(demand.columns)

    if len(demand.index) < 2:
        raise ValueError(
            "At least two timestamps are required to plot "
            "the cleaning timeline."
        )

    time_step = (
        demand.index.to_series()
        .diff()
        .dropna()
        .median()
    )

    if (
        pd.isna(time_step)
        or time_step <= pd.Timedelta(0)
    ):
        raise ValueError(
            "Could not determine a valid temporal resolution."
        )

    start = demand.index[0]
    end = demand.index[-1] + time_step

    figure_height = max(
        6.0,
        country_count * 0.3,
    )

    figure, axis = plt.subplots(
        figsize=(16, figure_height),
        constrained_layout=True,
    )

    axis.imshow(
        background,
        aspect="auto",
        interpolation="nearest",
        cmap=background_cmap,
        extent=(
            mdates.date2num(start),
            mdates.date2num(end),
            country_count - 0.5,
            -0.5,
        ),
        rasterized=True,
        zorder=0,
    )

    row_centres = np.arange(country_count)

    axis.set_yticks(row_centres)
    axis.set_yticklabels(demand.columns)

    axis.set_xlim(start, end)
    axis.set_ylim(
        country_count - 0.5,
        -0.5,
    )

    # Light boundaries make individual country strips clear
    # without obscuring the provenance colours.
    axis.set_yticks(
        np.arange(-0.5, country_count, 1),
        minor=True,
    )

    axis.grid(
        axis="y",
        which="minor",
        linewidth=0.4,
        alpha=0.35,
    )

    axis.tick_params(
        axis="y",
        which="minor",
        left=False,
    )

    axis.set_xlabel("Time")
    axis.set_ylabel("Country")

    date_locator = mdates.AutoDateLocator(
        minticks=4,
        maxticks=12,
    )

    axis.xaxis.set_major_locator(date_locator)
    axis.xaxis.set_major_formatter(
        mdates.ConciseDateFormatter(
            date_locator
        )
    )

    axis.set_title(
        "Electricity demand and cleaning provenance"
    )

    return figure, axis


def _add_normalised_demand_traces(
    *,
    axis: plt.Axes,
    demand: pd.DataFrame,
    half_height: float = 0.35,
    quantile: float = 0.99,
) -> dict[str, float]:
    """Overlay mean-normalised hourly demand traces."""
    mean_load_gw: dict[str, float] = {}

    for row_index, country in enumerate(
        demand.columns
    ):
        series = demand[country].astype(float)

        mean_load = series.mean(skipna=True)
        mean_load_gw[country] = mean_load / 1000

        if pd.isna(mean_load) or mean_load == 0:
            continue

        relative = (series / mean_load) - 1

        scale = relative.abs().quantile(
            quantile
        )

        if pd.isna(scale) or scale == 0:
            plotted_y = pd.Series(
                row_index,
                index=series.index,
                dtype=float,
            )
        else:
            scaled = relative.clip(
                lower=-scale,
                upper=scale,
            ) / scale

            # The y-axis is inverted, so subtracting makes
            # above-average demand appear visually upward.
            plotted_y = (
                row_index
                - scaled * half_height
            )

        axis.plot(
            series.index,
            plotted_y,
            color="black",
            linewidth=0.6,
            alpha=0.9,
            zorder=3,
        )

    return mean_load_gw


def _add_mean_load_labels(
    *,
    axis: plt.Axes,
    mean_load_gw: dict[str, float],
    countries: pd.Index,
) -> None:
    """Annotate country rows with mean load in GW."""
    for row_index, country in enumerate(countries):
        mean_value = mean_load_gw[country]

        label = (
            "—"
            if pd.isna(mean_value)
            else f"{mean_value:.1f}"
        )

        axis.text(
            1.01,
            row_index,
            label,
            transform=axis.get_yaxis_transform(),
            ha="left",
            va="center",
            fontsize=8,
            clip_on=False,
        )

    axis.text(
        1.01,
        1.01,
        "Mean\n(GW)",
        transform=axis.transAxes,
        ha="left",
        va="bottom",
        fontsize=8,
    )


def _add_dynamic_legend(
    *,
    figure: plt.Figure,
    metadata: pd.DataFrame,
    rank_colours: dict[
        int,
        tuple[float, float, float, float],
    ],
) -> None:
    """Add a rank-ordered method legend."""
    handles: list[Patch | Line2D] = [
        Line2D(
            [0],
            [0],
            color="black",
            linewidth=1,
            label="Mean-normalised hourly demand",
        )
    ]

    for row in metadata.itertuples(
        index=False
    ):
        rank = int(
            row.cleaning_method_rank
        )
        method = str(
            row.cleaning_method
        )

        colour = rank_colours[rank]

        # A border keeps the white principal-source patch
        # visible in the legend.
        edge_colour = (
            "0.65"
            if row.category == "observed"
            and rank == metadata[
                "cleaning_method_rank"
            ].min()
            else "none"
        )

        handles.append(
            Patch(
                facecolor=colour,
                edgecolor=edge_colour,
                linewidth=0.8,
                label=(
                    f"Rank {rank}: "
                    f"{_format_method_label(method)}"
                ),
            )
        )

    figure.legend(
        handles=handles,
        loc="outside lower center",
        ncols=min(
            4,
            len(handles),
        ),
        frameon=True,
        fontsize=8,
    )


def _format_method_label(
    method: str,
) -> str:
    """Convert a method identifier into a legend label."""
    if method == "missing":
        return "Missing"

    if method.startswith("observed_"):
        source = method.removeprefix(
            "observed_"
        )

        source_labels = {
            "entsoe_api": "Observed: ENTSO-E API",
            "opsd_api": "Observed: OPSD API",
        }

        return source_labels.get(
            source,
            (
                "Observed: "
                + source.replace("_", " ").upper()
            ),
        )

    return method.replace(
        "_",
        " ",
    ).capitalize()


if __name__ == "__main__":
    sys.stderr = open(
        snakemake.log[0],
        "w",
        buffering=1,
    )

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    main(
        demand_path=snakemake.input.demand,
        cleaning_method_path=(
            snakemake.input.cleaning_method
        ),
        cleaning_method_rank_path=(
            snakemake.input.cleaning_method_rank
        ),
        output_path=snakemake.output.plot,
    )