"""Plot electricity demand and cleaning-method provenance through time."""

import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from _tclean_config import build_advanced_rules, build_basic_rules
from cmap import Colormap
from matplotlib.colors import ListedColormap, to_rgba
from matplotlib.patches import Patch

logger = logging.getLogger(__name__)

FIGURE_SIZE_INCHES = (7.5, 9.8)


def main(
    *,
    demand_path: str | Path,
    basic_cleaning_method_path: str | Path,
    cleaning_method_path: str | Path,
    cleaning_method_rank_path: str | Path,
    output_path: str | Path,
    summary_output_path: str | Path,
    source_names: list[str],
    gap_filling_config: dict[str, Any],
    source_registry: Mapping[str, Mapping[str, Any]],
) -> None:
    """Create the electricity-demand cleaning diagnostic and summary."""
    demand = pd.read_parquet(demand_path)
    basic_cleaning_method = pd.read_parquet(basic_cleaning_method_path)
    cleaning_method = pd.read_parquet(cleaning_method_path)
    cleaning_method_rank = pd.read_parquet(cleaning_method_rank_path)

    _validate_alignment(
        demand=demand,
        basic_cleaning_method=basic_cleaning_method,
        cleaning_method=cleaning_method,
        cleaning_method_rank=cleaning_method_rank,
    )

    metadata = _build_cleaning_method_metadata(
        source_names=source_names,
        source_registry=source_registry,
        gap_filling_config=gap_filling_config,
    )

    rank_colours = _build_rank_colours(metadata)

    background, background_cmap = _encode_rank_background(
        cleaning_method_rank=cleaning_method_rank,
        metadata=metadata,
        rank_colours=rank_colours,
    )

    summary = _build_country_summary(
        demand=demand,
        basic_cleaning_method=basic_cleaning_method,
        cleaning_method=cleaning_method,
        gap_filling_config=gap_filling_config,
    )

    logger.info(
        "Loaded %s timestamps for %s countries.",
        len(demand),
        len(demand.columns),
    )

    logger.info("Cleaning-method ranks:\n%s", metadata.to_string(index=False))

    figure, axis, summary_axis, legend_axis = _plot_cleaning_background(
        demand=demand,
        background=background,
        background_cmap=background_cmap,
    )

    _add_normalised_demand_traces(
        axis=axis,
        demand=demand,
    )

    _add_summary_panel(
        axis=summary_axis,
        summary=summary,
        gap_filling_config=gap_filling_config,
    )

    legend_handles = _build_legend_handles(metadata, rank_colours)

    legend_axis.legend(
        handles=legend_handles,
        loc="center",
        frameon=False,
        ncol=min(3, max(1, len(legend_handles))),
        fontsize=6.5,
        handlelength=1.5,
        handletextpad=0.5,
        columnspacing=0.8,
    )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Do not use bbox_inches="tight": preserving the fixed portrait figure
    # dimensions makes the PDF predictable when placed in a manuscript.
    figure.savefig(output_path)

    plt.close(figure)

    _write_summary_html(
        summary=summary,
        output_path=summary_output_path,
        gap_filling_config=gap_filling_config,
    )

    logger.info("Saved cleaning timeline to %s.", output_path)
    logger.info("Saved cleaning summary to %s.", summary_output_path)


def _build_legend_handles(
    metadata: pd.DataFrame,
    rank_colours: dict[int, tuple[float, float, float, float]],
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
    basic_cleaning_method: pd.DataFrame,
    cleaning_method: pd.DataFrame,
    cleaning_method_rank: pd.DataFrame,
) -> None:
    """Require all diagnostic inputs to use the same time-country grid."""
    for name, frame in {
        "basic_cleaning_method": basic_cleaning_method,
        "cleaning_method": cleaning_method,
        "cleaning_method_rank": cleaning_method_rank,
    }.items():
        if not frame.index.equals(demand.index):
            raise ValueError(f"{name} does not use the same time index as demand.")

        if not frame.columns.equals(demand.columns):
            raise ValueError(f"{name} does not use the same country columns as demand.")


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
    *,
    demand: pd.DataFrame,
    background: np.ndarray,
    background_cmap: ListedColormap,
) -> tuple[plt.Figure, plt.Axes, plt.Axes, plt.Axes]:
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

    figure = plt.figure(figsize=FIGURE_SIZE_INCHES)

    grid = figure.add_gridspec(
        nrows=2,
        ncols=2,
        width_ratios=(3.9, 2.5),
        height_ratios=(8.6, 1.25),
        left=0.09,
        right=0.95,
        bottom=0.06,
        top=0.89,
        wspace=0.04,
        hspace=0.12,
    )

    axis = figure.add_subplot(grid[0, 0])
    summary_axis = figure.add_subplot(grid[0, 1], sharey=axis)
    legend_axis = figure.add_subplot(grid[1, :])
    legend_axis.axis("off")

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
    axis.set_yticklabels(demand.columns, fontsize=7)

    axis.set_xlim(start, end)
    axis.set_ylim(country_count - 0.5, -0.5)

    # Light boundaries make individual country strips clear
    # without obscuring the provenance colours.
    row_boundaries = np.arange(-0.5, country_count, 1)

    axis.set_yticks(row_boundaries, minor=True)
    axis.grid(axis="y", which="minor", linewidth=0.4, alpha=0.35)
    axis.tick_params(axis="y", which="minor", left=False)

    axis.set_xlabel("Date-Time")
    axis.set_ylabel("Country")

    date_locator = mdates.AutoDateLocator(minticks=4, maxticks=8)

    axis.xaxis.set_major_locator(date_locator)
    axis.xaxis.set_major_formatter(
        mdates.ConciseDateFormatter(
            date_locator,
            show_offset=False,
        )
    )
    axis.tick_params(axis="x", labelsize=7)

    summary_axis.set_xlim(0, 1)
    summary_axis.tick_params(
        axis="both",
        which="both",
        left=False,
        bottom=False,
        labelleft=False,
        labelbottom=False,
    )

    for spine in summary_axis.spines.values():
        spine.set_visible(False)

    for boundary in row_boundaries:
        summary_axis.axhline(
            boundary,
            linewidth=0.4,
            alpha=0.35,
            color="0.5",
            zorder=0,
        )

    summary_axis.axvline(
        0.0,
        linewidth=0.6,
        color="0.7",
    )

    figure.suptitle(
        "Electricity demand and cleaning provenance",
        fontsize=11,
        y=0.965,
    )

    return figure, axis, summary_axis, legend_axis


def _add_normalised_demand_traces(
    *,
    axis: plt.Axes,
    demand: pd.DataFrame,
    half_height: float = 0.35,
    quantile: float = 0.99,
) -> None:
    """Overlay mean-normalised demand traces."""
    for row_index, country in enumerate(demand.columns):
        series = demand[country].astype(float)

        mean_load = series.mean(skipna=True)

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
            series.index,
            plotted_y,
            color="black",
            linewidth=0.55,
            alpha=0.9,
            zorder=3,
        )


def _build_country_summary(
    *,
    demand: pd.DataFrame,
    basic_cleaning_method: pd.DataFrame,
    cleaning_method: pd.DataFrame,
    gap_filling_config: dict[str, Any],
) -> pd.DataFrame:
    """Summarise load and completion at each cleaning stage."""
    summary = pd.DataFrame(index=demand.columns)

    summary.index.name = "country"

    summary["mean_load_gw"] = (
        demand.mean(axis=0, skipna=True) / 1000
    )

    raw_present = basic_cleaning_method.apply(
        lambda column: column.str.startswith(
            "observed_",
            na=False,
        )
    )

    basic_present = (
        basic_cleaning_method.notna()
        & basic_cleaning_method.ne("missing")
    )

    final_present = (
        cleaning_method.notna()
        & cleaning_method.ne("missing")
    )

    summary["raw_completion"] = raw_present.mean(axis=0)

    mode = gap_filling_config["mode"]

    if mode in {"basic", "advanced"}:
        summary["basic_completion"] = (
            basic_present.mean(axis=0)
        )

    if mode == "advanced":
        summary["advanced_completion"] = (
            final_present.mean(axis=0)
        )

    summary["final_complete"] = final_present.all(axis=0)

    return summary


def _add_summary_panel(
    *,
    axis: plt.Axes,
    summary: pd.DataFrame,
    gap_filling_config: dict[str, Any],
) -> None:
    """Add paper-friendly completeness columns beside the timeline."""
    columns: list[tuple[str, str, str]] = [
        ("Mean\n(GW)", "mean_load_gw", "mean"),
        ("Raw\n(%)", "raw_completion", "completion"),
    ]

    mode = gap_filling_config["mode"]

    if mode in {"basic", "advanced"}:
        columns.append(
            ("Basic\n(%)", "basic_completion", "completion")
        )

    if mode == "advanced":
        columns.append(
            ("Advanced\n(%)", "advanced_completion", "completion")
        )

    columns.append(("Status", "final_complete", "status"))

    x_positions = np.linspace(
        0.08,
        0.92,
        len(columns),
    )

    for x_position, (header, _, _) in zip(
        x_positions,
        columns,
        strict=True,
    ):
        axis.text(
            x_position,
            1.01,
            header,
            transform=axis.transAxes,
            ha="center",
            va="bottom",
            fontsize=7,
            fontweight="bold",
        )

    for row_index, (_, row) in enumerate(summary.iterrows()):
        for x_position, (_, field, kind) in zip(
            x_positions,
            columns,
            strict=True,
        ):
            if kind == "mean":
                value = row[field]

                label = (
                    "—"
                    if pd.isna(value)
                    else f"{float(value):.1f}"
                )

                axis.text(
                    x_position,
                    row_index,
                    label,
                    ha="center",
                    va="center",
                    fontsize=7,
                )

            elif kind == "completion":
                axis.text(
                    x_position,
                    row_index,
                    _format_completion(row[field]),
                    ha="center",
                    va="center",
                    fontsize=7,
                )

            else:
                complete = bool(row[field])

                axis.text(
                    x_position,
                    row_index,
                    "✓" if complete else "✗",
                    ha="center",
                    va="center",
                    fontsize=9,
                    fontweight="bold",
                    color=(
                        "#2e7d32"
                        if complete
                        else "#c62828"
                    ),
                )


def _format_completion(value: float) -> str:
    """Format completion without ever rounding incomplete data to 100.0."""
    if pd.isna(value):
        return "—"

    value = float(value)

    if value >= 1.0:
        return "100.0"

    percentage = np.floor(value * 1000) / 10
    percentage = min(percentage, 99.9)

    return f"{percentage:.1f}"


def _write_summary_html(
    *,
    summary: pd.DataFrame,
    output_path: str | Path,
    gap_filling_config: dict[str, Any],
) -> None:
    """Write a standalone, human-readable HTML completeness table."""
    table = pd.DataFrame(
        {
            "Country": summary.index,
            "Mean load (GW)": [
                "—" if pd.isna(value) else f"{float(value):.1f}"
                for value in summary["mean_load_gw"]
            ],
            "Raw completion": [
                f"{_format_completion(value)}%"
                for value in summary["raw_completion"]
            ],
        }
    )

    mode = gap_filling_config["mode"]

    if mode in {"basic", "advanced"}:
        table["Basic completion"] = [
            f"{_format_completion(value)}%"
            for value in summary["basic_completion"]
        ]

    if mode == "advanced":
        table["Advanced completion"] = [
            f"{_format_completion(value)}%"
            for value in summary["advanced_completion"]
        ]

    table["Status"] = [
        (
            '<span class="complete">✓ Complete</span>'
            if bool(complete)
            else '<span class="incomplete">✗ Incomplete</span>'
        )
        for complete in summary["final_complete"]
    ]

    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    table_html = table.to_html(
        index=False,
        border=0,
        escape=False,
        classes="summary-table",
    )

    document = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Electricity-demand cleaning summary</title>
<style>
body {{
    font-family: Arial, sans-serif;
    margin: 2rem;
    color: #222;
}}
h1 {{
    font-size: 1.35rem;
}}
.summary-table {{
    border-collapse: collapse;
    font-size: 0.95rem;
}}
.summary-table th,
.summary-table td {{
    border-bottom: 1px solid #ddd;
    padding: 0.45rem 0.75rem;
    text-align: right;
}}
.summary-table th:first-child,
.summary-table td:first-child {{
    text-align: left;
}}
.complete {{
    color: #2e7d32;
    font-weight: bold;
}}
.incomplete {{
    color: #c62828;
    font-weight: bold;
}}
.note {{
    max-width: 60rem;
    font-size: 0.9rem;
    color: #555;
}}
</style>
</head>
<body>
<h1>Electricity-demand cleaning summary</h1>
<p class="note">
Completion is measured against all expected periods on the configured time grid.
Incomplete percentages are floored to one decimal place, so an incomplete series
can never be displayed as 100.0%.
</p>
{table_html}
</body>
</html>
"""

    output_path.write_text(
        document,
        encoding="utf-8",
    )


def _build_cleaning_method_metadata(
    *,
    source_names: list[str],
    gap_filling_config: dict[str, Any],
    source_registry: Mapping[str, Mapping[str, Any]],
) -> pd.DataFrame:
    """Build complete method metadata in configured rank order."""
    rows: list[dict[str, Any]] = []
    rank = 0

    for source_name in source_names:
        rows.append(
            {
                "cleaning_method": f"observed_{source_name}",
                "cleaning_method_rank": rank,
                "label": (
                    "Rank "
                    f"{rank}: Observed "
                    f"({_format_source_name(source_name, source_registry)})"
                ),
                "category": "observed",
            }
        )

        rank += 1

    basic_rules = build_basic_rules(gap_filling_config)
    advanced_rules = build_advanced_rules(gap_filling_config)

    rule_names = [
        rule["name"]
        for rule in basic_rules
    ]

    if not advanced_rules.empty:
        rule_names.extend(
            advanced_rules["rule_name"].tolist()
        )

    for rule_name in rule_names:
        rows.append(
            {
                "cleaning_method": rule_name,
                "cleaning_method_rank": rank,
                "label": (
                    f"Rank {rank}: "
                    f"{_format_rule_name(rule_name)}"
                ),
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


def _format_source_name(
    source_name: str,
    source_registry: Mapping[str, Mapping[str, Any]],
) -> str:
    """Return the configured human-readable source name."""
    metadata = source_registry.get(
        source_name,
        {},
    )

    return str(
        metadata.get(
            "display_name",
            source_name,
        )
    )


def _format_rule_name(name: str) -> str:
    """Format one configured rule name for display."""
    return name.replace("_", " ").capitalize()
