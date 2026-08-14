"""Plot electricity demand and cleaning-method provenance through time."""

import logging
from pathlib import Path
from typing import Any

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from cmap import Colormap
from matplotlib.colors import ListedColormap, to_rgba
from matplotlib.patches import Patch

from cleaning.provenance import build_final_cleaning_rules

logger = logging.getLogger(__name__)


def main(
    *,
    demand_path: str | Path,
    cleaning_method_path: str | Path,
    cleaning_method_rank_path: str | Path,
    output_path: str | Path,
    source_names: list[str],
    gap_filling_config: dict[str, Any],
) -> None:
    """Create the electricity-demand cleaning diagnostic."""
    demand = pd.read_parquet(demand_path)
    cleaning_method = pd.read_parquet(cleaning_method_path)
    cleaning_method_rank = pd.read_parquet(cleaning_method_rank_path)

    _validate_alignment(
        demand=demand,
        cleaning_method=cleaning_method,
        cleaning_method_rank=cleaning_method_rank,
    )

    metadata = _build_cleaning_method_metadata(
        source_names=source_names, gap_filling_config=gap_filling_config
    )

    rank_colours = _build_rank_colours(metadata)

    background, background_cmap = _encode_rank_background(
        cleaning_method_rank=cleaning_method_rank,
        metadata=metadata,
        rank_colours=rank_colours,
    )

    logger.info(
        "Loaded %s timestamps for %s countries.", len(demand), len(demand.columns)
    )

    logger.info("Cleaning-method ranks:\n%s", metadata.to_string(index=False))

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

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    figure.savefig(output_path, bbox_inches="tight")

    plt.close(figure)

    logger.info("Saved cleaning timeline to %s.", output_path)


def _build_legend_handles(
    metadata: pd.DataFrame, rank_colours: dict[int, tuple[float, float, float, float]]
) -> list[Patch]:
    """Create handles for every configured rank."""
    handles: list[Patch] = []

    ordered = metadata.sort_values("cleaning_method_rank")

    for row in ordered.itertuples(index=False):
        rank = int(row.cleaning_method_rank)

        handles.append(
            Patch(
                facecolor=rank_colours[rank],
                edgecolor="0.65",
                linewidth=0.8,
                label=str(row.label),
            )
        )

    return handles


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
            raise ValueError(f"{name} does not use the same time index as demand.")

        if not frame.columns.equals(demand.columns):
            raise ValueError(
                f"{name} does not use the same country columns as demand."
            )


def _build_rank_colours(
    metadata: pd.DataFrame,
) -> dict[int, tuple[float, float, float, float]]:
    """Assign colours by provenance category."""
    colours: dict[int, tuple[float, float, float, float]] = {}

    ordered = metadata.sort_values("cleaning_method_rank")

    observed = ordered.loc[ordered["category"] == "observed"]

    imputed = ordered.loc[ordered["category"] == "imputed"]

    missing = ordered.loc[ordered["category"] == "missing"]

    # Primary source is white. Subsequent observed sources
    # become gradually darker, but remain very light so that
    # the black demand trace stays clearly visible.
    observed_shades = np.linspace(1.0, 0.60, len(observed))

    for (_, row), shade in zip(observed.iterrows(), observed_shades, strict=True):
        rank = int(row["cleaning_method_rank"])

        colours[rank] = (float(shade), float(shade), float(shade), 1.0)

    if not imputed.empty:
        colourtheme = Colormap("bids:viridis").to_mpl()

        positions = np.linspace(0.05, 0.95, len(imputed))

        for (_, row), position in zip(imputed.iterrows(), positions, strict=True):
            rank = int(row["cleaning_method_rank"])
            colours[rank] = colourtheme(position)

    for _, row in missing.iterrows():
        rank = int(row["cleaning_method_rank"])
        colours[rank] = to_rgba("#ff0000")

    expected_ranks = set(metadata["cleaning_method_rank"].astype(int))

    missing_colours = expected_ranks - set(colours)

    if missing_colours:
        raise ValueError(f"No colour was assigned to ranks: {sorted(missing_colours)}")

    return colours


def _encode_rank_background(
    *,
    cleaning_method_rank: pd.DataFrame,
    metadata: pd.DataFrame,
    rank_colours: dict[int, tuple[float, float, float, float]],
) -> tuple[np.ndarray, ListedColormap]:
    """Encode ranks as contiguous plotting codes."""
    rank_order = metadata["cleaning_method_rank"].astype(int).tolist()

    rank_to_code = {rank: code for code, rank in enumerate(rank_order)}

    encoded = cleaning_method_rank.apply(lambda column: column.map(rank_to_code))

    colour_list = [rank_colours[rank] for rank in rank_order]

    # Input frames are time × country, whereas imshow expects
    # country × time for this figure orientation.
    background = encoded.to_numpy(dtype=int).T

    return (background, ListedColormap(colour_list))


def _plot_cleaning_background(
    *, demand: pd.DataFrame, background: np.ndarray, background_cmap: ListedColormap
) -> tuple[plt.Figure, plt.Axes]:
    """Plot cleaning-method ranks over time by country."""
    country_count = len(demand.columns)

    if len(demand.index) < 2:
        raise ValueError(
            "At least two timestamps are required to plot the cleaning timeline."
        )

    time_step = demand.index.to_series().diff().dropna().median()

    if pd.isna(time_step) or time_step <= pd.Timedelta(0):
        raise ValueError("Could not determine a valid temporal resolution.")

    start = demand.index[0]
    end = demand.index[-1] + time_step

    figure_height = max(6.0, country_count * 0.3)

    figure, axis = plt.subplots(figsize=(16, figure_height), constrained_layout=True)

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
    axis.set_ylim(country_count - 0.5, -0.5)

    # Light boundaries make individual country strips clear
    # without obscuring the provenance colours.
    axis.set_yticks(np.arange(-0.5, country_count, 1), minor=True)

    axis.grid(axis="y", which="minor", linewidth=0.4, alpha=0.35)

    axis.tick_params(axis="y", which="minor", left=False)

    axis.set_xlabel("Time")
    axis.set_ylabel("Country")

    date_locator = mdates.AutoDateLocator(minticks=4, maxticks=12)

    axis.xaxis.set_major_locator(date_locator)
    axis.xaxis.set_major_formatter(mdates.ConciseDateFormatter(date_locator))

    axis.set_title("Electricity demand and cleaning provenance")

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

    for row_index, country in enumerate(demand.columns):
        series = demand[country].astype(float)

        mean_load = series.mean(skipna=True)
        mean_load_gw[country] = mean_load / 1000

        if pd.isna(mean_load) or mean_load == 0:
            continue

        relative = (series / mean_load) - 1

        scale = relative.abs().quantile(quantile)

        if pd.isna(scale) or scale == 0:
            plotted_y = pd.Series(row_index, index=series.index, dtype=float)
        else:
            scaled = relative.clip(lower=-scale, upper=scale) / scale

            # The y-axis is inverted, so subtracting makes
            # above-average demand appear visually upward.
            plotted_y = row_index - scaled * half_height

        axis.plot(
            series.index, plotted_y, color="black", linewidth=0.6, alpha=0.9, zorder=3
        )

    return mean_load_gw


def _add_mean_load_labels(
    *, axis: plt.Axes, mean_load_gw: dict[str, float], countries: pd.Index
) -> None:
    """Annotate country rows with mean load in GW."""
    for row_index, country in enumerate(countries):
        mean_value = mean_load_gw[country]

        label = "—" if pd.isna(mean_value) else f"{mean_value:.1f}"

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


def _build_cleaning_method_metadata(
    *, source_names: list[str], gap_filling_config: dict[str, Any]
) -> pd.DataFrame:
    """Build complete method metadata in configured rank order."""
    rows: list[dict[str, Any]] = []
    rank = 0

    for source_name in source_names:
        rows.append(
            {
                "cleaning_method": (f"observed_{source_name}"),
                "cleaning_method_rank": rank,
                "label": (
                    f"Rank {rank}: Observed ({_format_source_name(source_name)})"
                ),
                "category": "observed",
            }
        )
        rank += 1

    rules = build_final_cleaning_rules(gap_filling_config)

    for rule in rules:
        rule_name = rule["name"]

        rows.append(
            {
                "cleaning_method": rule_name,
                "cleaning_method_rank": rank,
                "label": (f"Rank {rank}: {_format_rule_name(rule_name)}"),
                "category": "imputed",
            }
        )
        rank += 1

    rows.append(
        {
            "cleaning_method": "missing",
            "cleaning_method_rank": rank,
            "label": f"Rank {rank}: Missing",
            "category": "missing",
        }
    )

    return pd.DataFrame(rows)


def _format_source_name(source_name: str) -> str:
    mapping = {"entsoe_api": "ENTSO-E", "neso": "NESO", "opsd_api": "OPSD"}
    return mapping.get(source_name, source_name)


def _format_rule_name(name: str) -> str:
    return name.replace("_", " ").capitalize()
