"""Plot electricity demand with data-quality failure annotations."""

import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from _tclean_config import CONSTRUCTED_SOURCE_NAME
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.lines import Line2D

logger = logging.getLogger(__name__)

FIGURE_DPI = 100

PAGE_WIDTH_PX = 750
CONTEXTS_PER_PAGE = 20

PAGE_LEFT_MARGIN_PX = 68
PAGE_RIGHT_MARGIN_PX = 38
OVERVIEW_PAGE_TOP_MARGIN_PX = 96
DETAIL_PAGE_TOP_MARGIN_PX = 72
PAGE_BOTTOM_MARGIN_PX = 42

PLOT_SUMMARY_GAP_PX = 8
SUMMARY_WIDTH_PX = 150

OVERVIEW_BASE_ROW_HEIGHT_PX = 32
OVERVIEW_TRACE_HALF_HEIGHT_PX = 10

DETAIL_BASE_ROW_HEIGHT_PX = 44
DETAIL_TRACE_HALF_HEIGHT_PX = 14
DETAIL_X_TICK_FOOTER_PX = 20

MARKER_GAP_PX = 3
MARKER_LEVEL_SPACING_PX = 4
MARKER_LINEWIDTH = 2.2

LEGEND_ROW_HEIGHT_PX = 13
LEGEND_VERTICAL_PADDING_PX = 12

USABLE_WIDTH_PX = PAGE_WIDTH_PX - PAGE_LEFT_MARGIN_PX - PAGE_RIGHT_MARGIN_PX
TIMELINE_WIDTH_PX = USABLE_WIDTH_PX - PLOT_SUMMARY_GAP_PX - SUMMARY_WIDTH_PX


def main(
    *,
    demand_path: str | Path,
    failures_path: str | Path,
    output_path: str | Path,
    data_quality_config: Mapping[str, Any],
    detail_years_per_row: int = 1,
) -> None:
    """Create overview and per-country electricity-demand quality diagnostics."""
    _validate_detail_years_per_row(detail_years_per_row)

    demand = pd.read_parquet(demand_path)
    failures = pd.read_parquet(failures_path)

    _validate_demand(demand)

    time_step = _infer_time_step(demand)
    plot_start = demand.index[0]
    plot_end = demand.index[-1] + time_step

    test_metadata = _build_test_metadata(data_quality_config)
    failures = _prepare_failures(
        failures,
        demand=demand,
        test_metadata=test_metadata,
        plot_start=plot_start,
        plot_end=plot_end,
    )

    test_colours = _build_test_colours(test_metadata)
    overview_summary = _build_context_summary(demand=demand, failures=failures)

    logger.info(
        "Plotting %s constructed-source data-quality failure periods "
        "across %s contexts.",
        len(failures),
        failures["context"].nunique() if not failures.empty else 0,
    )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    _write_pdf(
        demand=demand,
        failures=failures,
        test_metadata=test_metadata,
        test_colours=test_colours,
        overview_summary=overview_summary,
        plot_start=plot_start,
        plot_end=plot_end,
        time_step=time_step,
        detail_years_per_row=detail_years_per_row,
        output_path=output_path,
    )

    logger.info("Saved data-quality timeline to %s.", output_path)


def _validate_detail_years_per_row(value: int) -> None:
    """Require a positive whole-number detail horizon."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("detail_years_per_row must be an integer >= 1.")


def _validate_demand(demand: pd.DataFrame) -> None:
    """Require a plottable time-by-context demand frame."""
    if not isinstance(demand.index, pd.DatetimeIndex):
        raise ValueError("Demand must use a DatetimeIndex.")

    if len(demand.index) < 2:
        raise ValueError("At least two timestamps are required to plot data quality.")

    if demand.columns.empty:
        raise ValueError("At least one context is required to plot data quality.")

    if not demand.index.is_monotonic_increasing:
        raise ValueError("Demand timestamps must be monotonically increasing.")


def _infer_time_step(demand: pd.DataFrame) -> pd.Timedelta:
    """Infer the regular time step represented by the demand frame."""
    time_step = demand.index.to_series().diff().dropna().median()

    if pd.isna(time_step) or time_step <= pd.Timedelta(0):
        raise ValueError("Could not determine a valid temporal resolution.")

    return time_step


def _build_test_metadata(data_quality_config: Mapping[str, Any]) -> pd.DataFrame:
    """Describe configured tests in their evaluation/display order."""
    tests = data_quality_config["tests"]
    rows = [
        {
            "test_name": str(test["name"]),
            "method": str(test["method"]),
            "label": _format_test_name(str(test["name"])),
            "order": order,
        }
        for order, test in enumerate(tests)
    ]

    metadata = pd.DataFrame(
        rows,
        columns=["test_name", "method", "label", "order"],
    )

    if metadata.empty:
        return metadata.set_index("test_name")

    duplicate_names = metadata["test_name"].duplicated(keep=False)
    if duplicate_names.any():
        duplicates = sorted(metadata.loc[duplicate_names, "test_name"].unique())
        raise ValueError(f"Data-quality test names must be unique: {duplicates!r}.")

    return metadata.set_index("test_name")


def _prepare_failures(
    failures: pd.DataFrame,
    *,
    demand: pd.DataFrame,
    test_metadata: pd.DataFrame,
    plot_start: pd.Timestamp,
    plot_end: pd.Timestamp,
) -> pd.DataFrame:
    """Keep constructed-demand failures relevant to the plotted demand."""
    required_columns = {"context", "source", "start", "end", "test_name", "method"}
    missing_columns = required_columns - set(failures.columns)

    if missing_columns:
        raise ValueError(
            "Data-quality failures are missing required columns: "
            f"{sorted(missing_columns)!r}."
        )

    selected = failures.loc[failures["source"].eq(CONSTRUCTED_SOURCE_NAME)].copy()

    if selected.empty:
        return selected.reset_index(drop=True)

    selected["context"] = selected["context"].astype(str)
    selected["test_name"] = selected["test_name"].astype(str)
    selected["method"] = selected["method"].astype(str)
    selected["start"] = pd.to_datetime(selected["start"], utc=True)
    selected["end"] = pd.to_datetime(selected["end"], utc=True)

    unknown_contexts = sorted(set(selected["context"]) - set(demand.columns))
    if unknown_contexts:
        raise ValueError(
            "Data-quality failures reference contexts absent from demand: "
            f"{unknown_contexts!r}."
        )

    configured_tests = set(test_metadata.index)
    unknown_tests = sorted(set(selected["test_name"]) - configured_tests)
    if unknown_tests:
        raise ValueError(
            "Data-quality failures reference tests absent from configuration: "
            f"{unknown_tests!r}."
        )

    expected_methods = test_metadata["method"]
    observed_methods = selected.set_index("test_name")["method"]
    mismatched_tests = sorted(
        test_name
        for test_name in observed_methods.index.unique()
        if not observed_methods.loc[[test_name]].eq(expected_methods.loc[test_name]).all()
    )
    if mismatched_tests:
        raise ValueError(
            "Data-quality failures do not match configured methods for tests: "
            f"{mismatched_tests!r}."
        )

    invalid_periods = selected["end"].le(selected["start"])
    if invalid_periods.any():
        raise ValueError(
            "Data-quality failures must use positive [start, end) periods."
        )

    outside_plot = selected["start"].lt(plot_start) | selected["end"].gt(plot_end)
    if outside_plot.any():
        raise ValueError(
            "Data-quality failures extend outside the plotted demand period."
        )

    return selected.reset_index(drop=True)


def _build_test_colours(
    test_metadata: pd.DataFrame,
) -> dict[str, tuple[float, float, float, float]]:
    """Assign Plasma colours to tests in configured priority order."""
    test_names = test_metadata.sort_values("order").index.tolist()
    if not test_names:
        return {}

    colourtheme = plt.get_cmap("plasma")

    if len(test_names) == 1:
        positions = [0.45]
    else:
        # Avoid the palest yellow end of Plasma against a white page.
        positions = np.linspace(0.05, 0.85, len(test_names))

    return {
        test_name: colourtheme(position)
        for test_name, position in zip(test_names, positions, strict=True)
    }


def _test_order(test_metadata: pd.DataFrame) -> dict[str, int]:
    """Return configured data-quality test priority by name."""
    return test_metadata["order"].astype(int).to_dict()


def _active_test_names(
    failures: pd.DataFrame,
    *,
    test_order: dict[str, int],
) -> list[str]:
    """Return tests represented in one trace, preserving configured order."""
    if failures.empty:
        return []

    observed = set(failures["test_name"].astype(str))
    return [
        test_name
        for test_name, _ in sorted(test_order.items(), key=lambda item: item[1])
        if test_name in observed
    ]


def _build_row_layout(
    *,
    row_keys: list[str | int],
    failures: pd.DataFrame,
    failure_row_field: str,
    test_order: dict[str, int],
    base_row_height_px: int,
    footer_height_px: int = 0,
) -> tuple[pd.DataFrame, dict[tuple[str | int, str], int]]:
    """Allocate one active test lane above each trace, in configured order."""
    rows: list[dict[str, float | str | int]] = []
    lane_by_test: dict[tuple[str | int, str], int] = {}
    cursor = 0.0

    for row_key in row_keys:
        row_failures = failures.loc[failures[failure_row_field].eq(row_key)]
        active_tests = _active_test_names(row_failures, test_order=test_order)
        lane_count = len(active_tests)

        for lane, test_name in enumerate(active_tests):
            lane_by_test[(row_key, test_name)] = lane

        marker_space = 0.0
        if lane_count:
            marker_space = MARKER_GAP_PX + lane_count * MARKER_LEVEL_SPACING_PX

        axis_height = marker_space + base_row_height_px
        axis_end = cursor + axis_height
        row_end = axis_end + footer_height_px
        centre = cursor + marker_space + base_row_height_px / 2

        rows.append(
            {
                "row_key": row_key,
                "start": cursor,
                "centre": centre,
                "axis_end": axis_end,
                "end": row_end,
                "lane_count": lane_count,
            }
        )

        cursor = row_end

    layout = pd.DataFrame(rows).set_index("row_key")
    return layout, lane_by_test


def _build_context_summary(
    *, demand: pd.DataFrame, failures: pd.DataFrame
) -> pd.DataFrame:
    """Summarise range and unflagged share for every plotted context."""
    rows: list[dict[str, float | str]] = []

    for context in demand.columns:
        context_failures = failures.loc[failures["context"].eq(context)]
        metrics = _summarise_series(demand[context].astype(float), context_failures)
        rows.append({"context": context, **metrics})

    return pd.DataFrame(rows).set_index("context")


def _summarise_series(
    series: pd.Series, failures: pd.DataFrame
) -> dict[str, float]:
    """Return min/max load and the share of non-missing observations unflagged."""
    valid = series.notna()
    valid_count = int(valid.sum())

    if valid_count == 0:
        return {
            "min_load_gw": np.nan,
            "max_load_gw": np.nan,
            "unflagged": np.nan,
        }

    flagged = np.zeros(len(series), dtype=bool)

    for failure in failures.itertuples():
        flagged |= np.asarray(
            (series.index >= failure.start) & (series.index < failure.end),
            dtype=bool,
        )

    valid_values = series.loc[valid]
    unflagged_count = int(np.count_nonzero(valid.to_numpy() & ~flagged))

    return {
        "min_load_gw": float(valid_values.min()) / 1000,
        "max_load_gw": float(valid_values.max()) / 1000,
        "unflagged": unflagged_count / valid_count,
    }


def _write_pdf(
    *,
    demand: pd.DataFrame,
    failures: pd.DataFrame,
    test_metadata: pd.DataFrame,
    test_colours: dict[str, tuple[float, float, float, float]],
    overview_summary: pd.DataFrame,
    plot_start: pd.Timestamp,
    plot_end: pd.Timestamp,
    time_step: pd.Timedelta,
    detail_years_per_row: int,
    output_path: Path,
) -> None:
    """Write overview pages followed by one detailed page per context."""
    with PdfPages(output_path) as pdf:
        _write_overview_pages(
            pdf=pdf,
            demand=demand,
            failures=failures,
            test_metadata=test_metadata,
            test_colours=test_colours,
            summary=overview_summary,
            plot_start=plot_start,
            plot_end=plot_end,
        )

        _write_country_detail_pages(
            pdf=pdf,
            demand=demand,
            failures=failures,
            test_metadata=test_metadata,
            test_colours=test_colours,
            time_step=time_step,
            detail_years_per_row=detail_years_per_row,
        )


def _write_overview_pages(
    *,
    pdf: PdfPages,
    demand: pd.DataFrame,
    failures: pd.DataFrame,
    test_metadata: pd.DataFrame,
    test_colours: dict[str, tuple[float, float, float, float]],
    summary: pd.DataFrame,
    plot_start: pd.Timestamp,
    plot_end: pd.Timestamp,
) -> None:
    """Write the multi-context overview pages."""
    contexts = list(demand.columns)
    context_slices = [
        slice(start, min(start + CONTEXTS_PER_PAGE, len(contexts)))
        for start in range(0, len(contexts), CONTEXTS_PER_PAGE)
    ]
    test_order = _test_order(test_metadata)
    configured_test_names = test_metadata.sort_values("order").index.tolist()

    for page_index, context_slice in enumerate(context_slices):
        page_contexts = contexts[context_slice]
        page_demand = demand.loc[:, page_contexts]
        page_failures = failures.loc[failures["context"].isin(page_contexts)]
        page_summary = summary.loc[page_contexts]

        layout, lane_by_test = _build_row_layout(
            row_keys=page_contexts,
            failures=page_failures,
            failure_row_field="context",
            test_order=test_order,
            base_row_height_px=OVERVIEW_BASE_ROW_HEIGHT_PX,
        )

        visible_test_names = [
            test_name
            for test_name in configured_test_names
            if test_name in set(page_failures["test_name"])
        ]
        legend_height_px = _legend_height_px(visible_test_names)
        panel_height_px = int(np.ceil(layout["end"].iloc[-1]))
        page_height_px = (
            OVERVIEW_PAGE_TOP_MARGIN_PX
            + panel_height_px
            + legend_height_px
            + PAGE_BOTTOM_MARGIN_PX
        )

        figure, axis, summary_axis = _new_overview_page(
            demand=page_demand,
            layout=layout,
            page_height_px=page_height_px,
            panel_height_px=panel_height_px,
            legend_height_px=legend_height_px,
            page_index=page_index,
            page_count=len(context_slices),
            plot_start=plot_start,
            plot_end=plot_end,
        )

        _add_overview_traces(axis=axis, demand=page_demand, layout=layout)

        _add_failure_annotations(
            axis=axis,
            failures=page_failures,
            layout=layout,
            failure_row_field="context",
            lane_by_test=lane_by_test,
            test_colours=test_colours,
            trace_half_height_px=OVERVIEW_TRACE_HALF_HEIGHT_PX,
        )

        _add_summary_panel(axis=summary_axis, summary=page_summary, layout=layout)
        _add_test_legend(
            figure=figure,
            test_names=visible_test_names,
            test_metadata=test_metadata,
            test_colours=test_colours,
            page_height_px=page_height_px,
        )

        pdf.savefig(figure)
        plt.close(figure)


def _new_overview_page(
    *,
    demand: pd.DataFrame,
    layout: pd.DataFrame,
    page_height_px: int,
    panel_height_px: int,
    legend_height_px: int,
    page_index: int,
    page_count: int,
    plot_start: pd.Timestamp,
    plot_end: pd.Timestamp,
) -> tuple[plt.Figure, plt.Axes, plt.Axes]:
    """Create one overview page with a timeline and aligned summary table."""
    figure = _new_figure(height_px=page_height_px)
    axis_bottom_px = PAGE_BOTTOM_MARGIN_PX + legend_height_px

    axis = figure.add_axes(
        [
            PAGE_LEFT_MARGIN_PX / PAGE_WIDTH_PX,
            axis_bottom_px / page_height_px,
            TIMELINE_WIDTH_PX / PAGE_WIDTH_PX,
            panel_height_px / page_height_px,
        ]
    )

    summary_axis = figure.add_axes(
        [
            (PAGE_LEFT_MARGIN_PX + TIMELINE_WIDTH_PX + PLOT_SUMMARY_GAP_PX)
            / PAGE_WIDTH_PX,
            axis_bottom_px / page_height_px,
            SUMMARY_WIDTH_PX / PAGE_WIDTH_PX,
            panel_height_px / page_height_px,
        ],
        sharey=axis,
    )

    axis.set_xlim(plot_start, plot_end)
    axis.set_ylim(panel_height_px, 0)
    axis.set_yticks(layout["centre"].to_numpy())
    axis.set_yticklabels(demand.columns, fontsize=7)

    _add_row_boundaries(axis=axis, layout=layout)

    axis.set_xlabel("Date-Time")
    axis.set_ylabel("Country")

    date_locator = mdates.AutoDateLocator(minticks=4, maxticks=8)
    axis.xaxis.set_major_locator(date_locator)
    axis.xaxis.set_major_formatter(
        mdates.ConciseDateFormatter(date_locator, show_offset=False)
    )
    axis.tick_params(axis="x", labelsize=7)

    _configure_summary_axis(
        axis=summary_axis,
        layout=layout,
        panel_height_px=panel_height_px,
    )

    figure.text(
        0.5,
        1.0 - (28 / page_height_px),
        "Electricity demand and data-quality failures",
        ha="center",
        va="center",
        fontsize=11,
    )

    if page_count > 1:
        figure.text(
            1.0 - (PAGE_RIGHT_MARGIN_PX / PAGE_WIDTH_PX),
            1.0 - (50 / page_height_px),
            f"Overview {page_index + 1} of {page_count}",
            ha="right",
            va="center",
            fontsize=6.5,
            color="0.4",
        )

    return figure, axis, summary_axis


def _write_country_detail_pages(
    *,
    pdf: PdfPages,
    demand: pd.DataFrame,
    failures: pd.DataFrame,
    test_metadata: pd.DataFrame,
    test_colours: dict[str, tuple[float, float, float, float]],
    time_step: pd.Timedelta,
    detail_years_per_row: int,
) -> None:
    """Write one page per context, split into calendar-year horizon rows."""
    test_order = _test_order(test_metadata)
    configured_test_names = test_metadata.sort_values("order").index.tolist()

    for context in demand.columns:
        series = demand[context].astype(float)
        periods = _build_detail_periods(
            index=demand.index,
            time_step=time_step,
            years_per_row=detail_years_per_row,
        )

        detail_failures = _clip_failures_to_periods(
            failures=failures,
            context=context,
            periods=periods,
        )

        row_keys = periods["row_id"].astype(int).tolist()
        layout, lane_by_test = _build_row_layout(
            row_keys=row_keys,
            failures=detail_failures,
            failure_row_field="row_id",
            test_order=test_order,
            base_row_height_px=DETAIL_BASE_ROW_HEIGHT_PX,
            footer_height_px=DETAIL_X_TICK_FOOTER_PX,
        )

        summary = _build_period_summary(
            series=series,
            periods=periods,
            failures=detail_failures,
        )

        visible_test_names = [
            test_name
            for test_name in configured_test_names
            if test_name in set(detail_failures["test_name"])
        ]

        legend_height_px = _legend_height_px(visible_test_names)
        panel_height_px = int(np.ceil(layout["end"].iloc[-1]))
        page_height_px = (
            DETAIL_PAGE_TOP_MARGIN_PX
            + panel_height_px
            + legend_height_px
            + PAGE_BOTTOM_MARGIN_PX
        )

        figure = _new_figure(height_px=page_height_px)
        summary_axis = _new_detail_summary_axis(
            figure=figure,
            layout=layout,
            panel_height_px=panel_height_px,
            legend_height_px=legend_height_px,
            page_height_px=page_height_px,
        )

        normalisation = _normalisation_parameters(series)

        for period in periods.itertuples(index=False):
            row_key = int(period.row_id)
            row_layout = layout.loc[row_key]
            row_axis = _new_detail_row_axis(
                figure=figure,
                row_layout=row_layout,
                label=str(period.label),
                page_height_px=page_height_px,
                panel_height_px=panel_height_px,
                legend_height_px=legend_height_px,
            )

            segment = series.loc[
                (series.index >= period.start) & (series.index < period.end)
            ]

            local_centre = float(row_layout["centre"] - row_layout["start"])

            _add_normalised_trace(
                axis=row_axis,
                series=segment,
                centre=local_centre,
                half_height=DETAIL_TRACE_HALF_HEIGHT_PX,
                normalisation=normalisation,
            )

            row_failures = detail_failures.loc[
                detail_failures["row_id"].eq(row_key)
            ]

            _add_detail_failure_annotations(
                axis=row_axis,
                failures=row_failures,
                row_key=row_key,
                row_layout=row_layout,
                local_centre=local_centre,
                lane_by_test=lane_by_test,
                test_colours=test_colours,
            )

            row_axis.set_xlim(period.start, period.end)
            row_axis.tick_params(axis="x", labelsize=6.5)

        _add_summary_panel(axis=summary_axis, summary=summary, layout=layout)

        figure.text(
            0.5,
            1.0 - (28 / page_height_px),
            f"Electricity demand and data-quality failures — {context}",
            ha="center",
            va="center",
            fontsize=11,
        )

        _add_test_legend(
            figure=figure,
            test_names=visible_test_names,
            test_metadata=test_metadata,
            test_colours=test_colours,
            page_height_px=page_height_px,
        )

        pdf.savefig(figure)
        plt.close(figure)


def _build_detail_periods(
    *,
    index: pd.DatetimeIndex,
    time_step: pd.Timedelta,
    years_per_row: int,
) -> pd.DataFrame:
    """Split the plotted horizon into calendar-year detail rows."""
    plot_start = index[0]
    plot_end = index[-1] + time_step
    timezone = index.tz

    rows: list[dict[str, object]] = []
    row_id = 0

    for first_year in range(index[0].year, index[-1].year + 1, years_per_row):
        nominal_start = pd.Timestamp(
            year=first_year,
            month=1,
            day=1,
            tz=timezone,
        )
        nominal_end = nominal_start + pd.DateOffset(years=years_per_row)

        start = max(plot_start, nominal_start)
        end = min(plot_end, nominal_end)

        if start >= end:
            continue

        final_year = (end - pd.Timedelta(nanoseconds=1)).year
        label = (
            str(start.year)
            if start.year == final_year
            else f"{start.year}\u2013{final_year}"
        )

        rows.append(
            {
                "row_id": row_id,
                "label": label,
                "start": start,
                "end": end,
            }
        )
        row_id += 1

    return pd.DataFrame(rows)


def _clip_failures_to_periods(
    *,
    failures: pd.DataFrame,
    context: str,
    periods: pd.DataFrame,
) -> pd.DataFrame:
    """Clip a context's failure intervals to the detail-row boundaries."""
    context_failures = failures.loc[failures["context"].eq(context)]
    rows: list[dict[str, object]] = []

    for period in periods.itertuples(index=False):
        overlapping = context_failures.loc[
            context_failures["start"].lt(period.end)
            & context_failures["end"].gt(period.start)
        ]

        for failure in overlapping.itertuples(index=False):
            rows.append(
                {
                    "row_id": int(period.row_id),
                    "context": context,
                    "test_name": str(failure.test_name),
                    "method": str(failure.method),
                    "start": max(failure.start, period.start),
                    "end": min(failure.end, period.end),
                }
            )

    return pd.DataFrame(
        rows,
        columns=["row_id", "context", "test_name", "method", "start", "end"],
    )


def _build_period_summary(
    *,
    series: pd.Series,
    periods: pd.DataFrame,
    failures: pd.DataFrame,
) -> pd.DataFrame:
    """Summarise each detail row using the same table metrics as the overview."""
    rows: list[dict[str, float | int]] = []

    for period in periods.itertuples(index=False):
        segment = series.loc[
            (series.index >= period.start) & (series.index < period.end)
        ]
        row_failures = failures.loc[failures["row_id"].eq(period.row_id)]
        metrics = _summarise_series(segment, row_failures)
        rows.append({"row_id": int(period.row_id), **metrics})

    return pd.DataFrame(rows).set_index("row_id")


def _new_figure(*, height_px: int) -> plt.Figure:
    """Create a figure from pixel dimensions."""
    return plt.figure(
        figsize=(PAGE_WIDTH_PX / FIGURE_DPI, height_px / FIGURE_DPI),
        dpi=FIGURE_DPI,
    )


def _new_detail_summary_axis(
    *,
    figure: plt.Figure,
    layout: pd.DataFrame,
    panel_height_px: int,
    legend_height_px: int,
    page_height_px: int,
) -> plt.Axes:
    """Create the table axis shared by all detail rows on one country page."""
    panel_bottom_px = PAGE_BOTTOM_MARGIN_PX + legend_height_px

    axis = figure.add_axes(
        [
            (PAGE_LEFT_MARGIN_PX + TIMELINE_WIDTH_PX + PLOT_SUMMARY_GAP_PX)
            / PAGE_WIDTH_PX,
            panel_bottom_px / page_height_px,
            SUMMARY_WIDTH_PX / PAGE_WIDTH_PX,
            panel_height_px / page_height_px,
        ]
    )

    _configure_summary_axis(
        axis=axis,
        layout=layout,
        panel_height_px=panel_height_px,
    )

    return axis


def _new_detail_row_axis(
    *,
    figure: plt.Figure,
    row_layout: pd.Series,
    label: str,
    page_height_px: int,
    panel_height_px: int,
    legend_height_px: int,
) -> plt.Axes:
    """Create one independent date axis for a country detail row."""
    panel_bottom_px = PAGE_BOTTOM_MARGIN_PX + legend_height_px
    row_start = float(row_layout["start"])
    axis_end = float(row_layout["axis_end"])
    axis_height = axis_end - row_start

    axis_bottom_px = panel_bottom_px + panel_height_px - axis_end

    axis = figure.add_axes(
        [
            PAGE_LEFT_MARGIN_PX / PAGE_WIDTH_PX,
            axis_bottom_px / page_height_px,
            TIMELINE_WIDTH_PX / PAGE_WIDTH_PX,
            axis_height / page_height_px,
        ]
    )

    local_centre = float(row_layout["centre"] - row_layout["start"])
    axis.set_ylim(axis_height, 0)
    axis.set_yticks([local_centre])
    axis.set_yticklabels([label], fontsize=7)
    axis.tick_params(axis="y", length=0)

    # Intentionally leave Matplotlib's default date locator/formatter in place.
    # The one-year default horizon is narrow enough for it to expose more detail.

    return axis


def _configure_summary_axis(
    *, axis: plt.Axes, layout: pd.DataFrame, panel_height_px: int
) -> None:
    """Style a summary table axis aligned with timeline rows."""
    axis.set_xlim(0, 1)
    axis.set_ylim(panel_height_px, 0)
    axis.tick_params(
        axis="both",
        which="both",
        left=False,
        bottom=False,
        labelleft=False,
        labelbottom=False,
    )

    for spine in axis.spines.values():
        spine.set_visible(False)

    axis.axvline(0.0, linewidth=0.6, color="0.7")

    for boundary in layout["start"]:
        axis.axhline(boundary, linewidth=0.4, alpha=0.3, color="0.5", zorder=0)

    axis.axhline(
        layout["end"].iloc[-1],
        linewidth=0.4,
        alpha=0.3,
        color="0.5",
        zorder=0,
    )


def _add_row_boundaries(*, axis: plt.Axes, layout: pd.DataFrame) -> None:
    """Draw the existing light row separators on a stacked overview axis."""
    for boundary in layout["start"]:
        axis.axhline(boundary, linewidth=0.4, alpha=0.3, color="0.5", zorder=0)

    axis.axhline(
        layout["end"].iloc[-1],
        linewidth=0.4,
        alpha=0.3,
        color="0.5",
        zorder=0,
    )


def _add_summary_panel(
    *, axis: plt.Axes, summary: pd.DataFrame, layout: pd.DataFrame
) -> None:
    """Add min/max load and unflagged percentage beside timeline rows."""
    columns = [
        ("Min\n(GW)", "min_load_gw", "load"),
        ("Max\n(GW)", "max_load_gw", "load"),
        ("Unflagged\n(%)", "unflagged", "percentage"),
    ]
    x_positions = np.linspace(0.14, 0.86, len(columns))

    for x_position, (header, _, _) in zip(x_positions, columns, strict=True):
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

    for row_key, row in summary.iterrows():
        y_position = float(layout.loc[row_key, "centre"])

        for x_position, (_, field, kind) in zip(x_positions, columns, strict=True):
            value = row[field]
            label = _format_load_gw(value) if kind == "load" else _format_percentage(value)

            axis.text(
                x_position,
                y_position,
                label,
                ha="center",
                va="center",
                fontsize=7,
            )


def _format_load_gw(value: float) -> str:
    """Format load while distinguishing tiny positive values from exact zero."""
    if pd.isna(value):
        return "—"

    value = float(value)
    if 0.0 < value < 0.01:
        return "<0.01"

    return f"{value:.2f}"


def _format_percentage(value: float) -> str:
    """Format a fraction without rounding an imperfect result to 100.0."""
    if pd.isna(value):
        return "—"

    value = float(value)

    if value >= 1.0:
        return "100.0"

    percentage = np.floor(value * 1000) / 10
    percentage = min(percentage, 99.9)

    return f"{percentage:.1f}"


def _normalisation_parameters(series: pd.Series) -> tuple[float, float] | None:
    """Return the mean and robust relative scale used for one demand trace."""
    mean_load = series.mean(skipna=True)

    if pd.isna(mean_load) or mean_load == 0:
        return None

    relative = (series / mean_load) - 1
    scale = relative.abs().quantile(0.99)

    if pd.isna(scale):
        return None

    return float(mean_load), float(scale)


def _add_overview_traces(
    *, axis: plt.Axes, demand: pd.DataFrame, layout: pd.DataFrame
) -> None:
    """Overlay one independently normalised demand trace per overview context."""
    for context in demand.columns:
        series = demand[context].astype(float)
        centre = float(layout.loc[context, "centre"])

        _add_normalised_trace(
            axis=axis,
            series=series,
            centre=centre,
            half_height=OVERVIEW_TRACE_HALF_HEIGHT_PX,
            normalisation=_normalisation_parameters(series),
        )


def _add_normalised_trace(
    *,
    axis: plt.Axes,
    series: pd.Series,
    centre: float,
    half_height: float,
    normalisation: tuple[float, float] | None,
) -> None:
    """Plot one mean-normalised trace at a supplied vertical centre."""
    if normalisation is None:
        return

    mean_load, scale = normalisation
    relative = (series / mean_load) - 1

    if scale == 0:
        plotted_y = pd.Series(np.nan, index=series.index, dtype=float)
        plotted_y.loc[series.notna()] = centre
    else:
        scaled = relative.clip(lower=-scale, upper=scale) / scale
        plotted_y = centre - scaled * half_height

    axis.plot(
        series.index,
        plotted_y,
        color="black",
        linewidth=0.55,
        alpha=0.9,
        zorder=3,
    )


def _add_failure_annotations(
    *,
    axis: plt.Axes,
    failures: pd.DataFrame,
    layout: pd.DataFrame,
    failure_row_field: str,
    lane_by_test: dict[tuple[str | int, str], int],
    test_colours: dict[str, tuple[float, float, float, float]],
    trace_half_height_px: float,
) -> None:
    """Add failure segments in stable, test-specific lanes above overview traces."""
    for failure in failures.itertuples():
        row_key = getattr(failure, failure_row_field)
        test_name = str(failure.test_name)
        centre = float(layout.loc[row_key, "centre"])
        lane = lane_by_test[(row_key, test_name)]
        lane_count = int(layout.loc[row_key, "lane_count"])
        marker_y = _marker_y(
            centre=centre,
            lane=lane,
            lane_count=lane_count,
            trace_half_height_px=trace_half_height_px,
        )

        axis.plot(
            [failure.start, failure.end],
            [marker_y, marker_y],
            color=test_colours[test_name],
            linewidth=MARKER_LINEWIDTH,
            solid_capstyle="round",
            zorder=5,
        )


def _add_detail_failure_annotations(
    *,
    axis: plt.Axes,
    failures: pd.DataFrame,
    row_key: int,
    row_layout: pd.Series,
    local_centre: float,
    lane_by_test: dict[tuple[str | int, str], int],
    test_colours: dict[str, tuple[float, float, float, float]],
) -> None:
    """Add failure segments in stable, test-specific lanes above one detail trace."""
    lane_count = int(row_layout["lane_count"])

    for failure in failures.itertuples():
        test_name = str(failure.test_name)
        lane = lane_by_test[(row_key, test_name)]
        marker_y = _marker_y(
            centre=local_centre,
            lane=lane,
            lane_count=lane_count,
            trace_half_height_px=DETAIL_TRACE_HALF_HEIGHT_PX,
        )

        axis.plot(
            [failure.start, failure.end],
            [marker_y, marker_y],
            color=test_colours[test_name],
            linewidth=MARKER_LINEWIDTH,
            solid_capstyle="round",
            zorder=5,
        )


def _marker_y(
    *,
    centre: float,
    lane: int,
    lane_count: int,
    trace_half_height_px: float,
) -> float:
    """Return the y position for one configured-priority lane above a trace."""
    # The y-axis is inverted. Lane zero is therefore placed highest, so lanes
    # read top-to-bottom in the same order as the configured tests and legend.
    reversed_lane = lane_count - 1 - lane
    return (
        centre
        - trace_half_height_px
        - MARKER_GAP_PX
        - reversed_lane * MARKER_LEVEL_SPACING_PX
    )


def _legend_height_px(test_names: list[str]) -> int:
    """Return enough footer height for a simple three-column test legend."""
    if not test_names:
        return 28

    column_count = min(3, len(test_names))
    row_count = int(np.ceil(len(test_names) / column_count))
    return LEGEND_VERTICAL_PADDING_PX + row_count * LEGEND_ROW_HEIGHT_PX


def _add_test_legend(
    *,
    figure: plt.Figure,
    test_names: list[str],
    test_metadata: pd.DataFrame,
    test_colours: dict[str, tuple[float, float, float, float]],
    page_height_px: int,
) -> None:
    """Add configured test names and colours to a diagnostic page."""
    if not test_names:
        figure.text(
            0.5,
            8 / page_height_px,
            "No data-quality failures identified.",
            ha="center",
            va="bottom",
            fontsize=6.5,
            color="0.4",
        )
        return

    handles = [
        Line2D(
            [0],
            [0],
            color=test_colours[test_name],
            linewidth=MARKER_LINEWIDTH,
            label=str(test_metadata.loc[test_name, "label"]),
        )
        for test_name in test_names
    ]

    figure.legend(
        handles=handles,
        loc="lower center",
        bbox_to_anchor=(0.5, 7 / page_height_px),
        frameon=False,
        ncol=min(3, len(handles)),
        fontsize=6.5,
        handlelength=2.0,
        columnspacing=1.0,
    )


def _format_test_name(test_name: str) -> str:
    """Format a configured data-quality test name for display."""
    return test_name.replace("_", " ").capitalize()


