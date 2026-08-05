"""The pipeline coordinates the gap-filling rules and ensures each receives the necessary parameters."""
from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd

from cleaning.average_periods import METHOD_NAME as AVERAGE_PERIODS
from cleaning.average_periods import apply_average_periods
from cleaning.combine_sources import combine_sources
from cleaning.copy_period import METHOD_NAME as COPY_PERIOD
from cleaning.copy_period import apply_copy_period
from cleaning.linear_interpolation import METHOD_NAME as LINEAR_INTERPOLATION
from cleaning.linear_interpolation import apply_linear_interpolation
from cleaning.provenance import build_cleaning_method_ranks, derive_cleaning_method_rank

logger = logging.getLogger(__name__)


def clean_demand(
    sources: Mapping[str, pd.DataFrame],
    *,
    source_priority: Sequence[str],
    gap_filling_config: Mapping[str, Any],
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    """Combine observed sources and fill remaining gaps."""
    (
        combined,
        data_source,
        cleaning_method,
    ) = combine_sources(
        sources,
        priority=source_priority,
    )

    cleaned, cleaning_method = fill_gaps(
        combined,
        cleaning_method=cleaning_method,
        config=gap_filling_config,
    )

    rules = gap_filling_config["rules"]

    cleaning_method_ranks = build_cleaning_method_ranks(
        source_priority=source_priority,
        rules=rules,
    )

    cleaning_method_rank = derive_cleaning_method_rank(
        cleaning_method=cleaning_method,
        ranks=cleaning_method_ranks,
    )

    return (
        cleaned,
        data_source,
        cleaning_method,
        cleaning_method_rank,
    )


def fill_gaps(
    load: pd.DataFrame,
    *,
    cleaning_method: pd.DataFrame,
    config: Mapping[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply configured gap-filling rules and record method provenance.

    Parameters
    ----------
    load:
        Hourly demand data indexed by timestamp, with one column per country.
    cleaning_method:
        Per-cell cleaning-method provenance for the observed input values.
        Missing input values should contain ``pd.NA``.
    config:
        Gap-filling configuration containing ``enabled`` and ``rules``.

    Returns
    -------
    filled:
        Load after applying the configured rules. If gap filling is disabled,
        this is an unchanged copy of ``load``.
    cleaning_method:
        Per-cell provenance containing the observed-source identifier,
        configured gap-filling rule name, or ``missing``.
    """
    _validate_load(load)
    _validate_cleaning_method(
        load=load,
        cleaning_method=cleaning_method,
    )
    _validate_config(config)

    filled = load.copy()
    cleaning_method = cleaning_method.copy()

    if not config["enabled"]:
        logger.info("Gap filling is disabled.")

        cleaning_method = cleaning_method.fillna(
            "missing"
        )

        return filled, cleaning_method

    rules = config["rules"]
    original_gap_duration = calculate_missing_run_durations(
        load
    )

    for rule in rules:
        method = _get_method(rule)
        rule_name = _get_rule_name(rule)

        if method == LINEAR_INTERPOLATION:
            filled, newly_filled = apply_linear_interpolation(
                filled,
                max_gap=rule["max_gap"],
                original_gap_duration=original_gap_duration,
            )

        elif method == AVERAGE_PERIODS:
            filled, newly_filled = apply_average_periods(
                filled,
                max_gap=rule["max_gap"],
                source_offsets=rule["source_offsets"],
                original_gap_duration=original_gap_duration,
            )

        elif method == COPY_PERIOD:
            filled, newly_filled = apply_copy_period(
                filled,
                max_gap=rule["max_gap"],
                source_offset=rule["source_offset"],
                require_complete_source=rule.get(
                    "require_complete_source",
                    True,
                ),
                original_gap_duration=original_gap_duration,
            )

        else:
            raise ValueError(
                f"Unsupported gap-filling method: {method!r}"
            )

        cleaning_method = cleaning_method.mask(
            newly_filled,
            rule_name,
        )

        _log_rule_results(
            rule_name=rule_name,
            method=method,
            newly_filled=newly_filled,
        )

    cleaning_method = cleaning_method.fillna(
        "missing"
    )

    unresolved = int(
        filled.isna().to_numpy().sum()
    )

    logger.info(
        "Gap filling completed with %s unresolved values.",
        unresolved,
    )

    return filled, cleaning_method


def calculate_missing_run_durations(
    load: pd.DataFrame,
) -> pd.DataFrame:
    """Return the original duration of each missing run.

    Observed values receive a duration of zero.
    """
    timestep = _infer_regular_timestep(load.index)

    durations = pd.DataFrame(
        pd.Timedelta(0),
        index=load.index,
        columns=load.columns,
    )

    for column in load.columns:
        missing = load[column].isna()
        group_ids = missing.ne(missing.shift()).cumsum()

        run_lengths = (
            missing.groupby(group_ids)
            .transform("sum")
            .where(missing, 0)
        )

        durations[column] = run_lengths * timestep

    return durations


def _get_method(rule: Mapping[str, Any]) -> str:
    try:
        method = rule["method"]
    except KeyError as error:
        raise ValueError(
            "Each gap-filling rule must define a 'method'."
        ) from error

    if not isinstance(method, str):
        raise TypeError(
            "Gap-filling rule 'method' must be a string."
        )

    return method


def _get_rule_name(
    rule: Mapping[str, Any],
) -> str:
    try:
        name = rule["name"]
    except KeyError as error:
        raise ValueError(
            "Each gap-filling rule must define a 'name'."
        ) from error

    if not isinstance(name, str):
        raise TypeError(
            "Gap-filling rule 'name' must be a string."
        )

    if not name:
        raise ValueError(
            "Gap-filling rule 'name' must not be empty."
        )

    return name


def _validate_load(load: pd.DataFrame) -> None:
    if not isinstance(load, pd.DataFrame):
        raise TypeError("Load must be a pandas DataFrame.")

    if load.empty:
        raise ValueError("Load dataframe is empty.")

    timestep = _infer_regular_timestep(load.index)

    if timestep != pd.Timedelta(hours=1):
        raise ValueError(
            "Gap filling currently expects hourly load data. "
            f"Found timestep {timestep}."
        )

    if not all(pd.api.types.is_numeric_dtype(dtype) for dtype in load.dtypes):
        raise TypeError("All load columns must be numeric.")


def _infer_regular_timestep(
    index: pd.Index,
) -> pd.Timedelta:
    if not isinstance(index, pd.DatetimeIndex):
        raise TypeError(
            "Load data must use a pandas DatetimeIndex."
        )

    if not index.is_monotonic_increasing:
        raise ValueError(
            "Load timestamps must be sorted in increasing order."
        )

    if index.has_duplicates:
        raise ValueError(
            "Load timestamps must not contain duplicates."
        )

    differences = index.to_series().diff().dropna()

    if differences.empty:
        raise ValueError(
            "At least two timestamps are required for gap filling."
        )

    timestep = differences.iloc[0]

    if not differences.eq(timestep).all():
        raise ValueError(
            "Load data must have a complete, regular time index "
            "before gap filling."
        )

    return timestep


def _log_rule_results(
    *,
    rule_name: str,
    method: str,
    newly_filled: pd.DataFrame,
) -> None:
    total = int(
        newly_filled.to_numpy().sum()
    )

    logger.info(
        "Gap-filling rule '%s' using method '%s' filled %s values.",
        rule_name,
        method,
        total,
    )

    for country, count in newly_filled.sum().items():
        count = int(count)

        if count:
            logger.info(
                "%s: %s values filled using rule '%s'.",
                country,
                count,
                rule_name,
            )


def _validate_config(config: Mapping[str, Any]) -> None:
    if not isinstance(config, Mapping):
        raise TypeError(
            "Gap-filling configuration must be a mapping."
        )

    if "enabled" not in config:
        raise ValueError(
            "Gap-filling configuration must define 'enabled'."
        )

    if not isinstance(config["enabled"], bool):
        raise TypeError(
            "Gap-filling configuration 'enabled' must be a boolean."
        )

    if "rules" not in config:
        raise ValueError(
            "Gap-filling configuration must define 'rules'."
        )

    if not isinstance(config["rules"], Sequence) or isinstance(
        config["rules"],
        (str, bytes),
    ):
        raise TypeError(
            "Gap-filling configuration 'rules' must be an ordered sequence."
        )

    if config["enabled"] and not config["rules"]:
        raise ValueError(
            "At least one gap-filling rule is required when gap filling "
            "is enabled."
        )


def _validate_cleaning_method(
    *,
    load: pd.DataFrame,
    cleaning_method: pd.DataFrame,
) -> None:
    if not isinstance(cleaning_method, pd.DataFrame):
        raise TypeError(
            "Cleaning method must be a pandas DataFrame."
        )

    if not cleaning_method.index.equals(load.index):
        raise ValueError(
            "Cleaning-method provenance must use the same "
            "index as the load data."
        )

    if not cleaning_method.columns.equals(load.columns):
        raise ValueError(
            "Cleaning-method provenance must use the same "
            "columns as the load data."
        )

    missing_observed_provenance = (
        load.notna()
        & cleaning_method.isna()
    )

    if missing_observed_provenance.any().any():
        count = int(
            missing_observed_provenance.to_numpy().sum()
        )

        raise ValueError(
            "Cleaning-method provenance is missing for "
            f"{count} observed load values."
        )

    provenance_for_missing_values = (
        load.isna()
        & cleaning_method.notna()
    )

    if provenance_for_missing_values.any().any():
        count = int(
            provenance_for_missing_values.to_numpy().sum()
        )

        raise ValueError(
            "Cleaning-method provenance is already assigned "
            f"to {count} missing load values."
        )