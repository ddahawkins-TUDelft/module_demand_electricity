"""The pipeline coordinates the gap-filling rules and ensures each receives the necessary parameters."""
from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd

from gap_filling.linear_interpolation import METHOD_NAME as LINEAR_INTERPOLATION
from gap_filling.linear_interpolation import apply_linear_interpolation

logger = logging.getLogger(__name__)

def fill_gaps(
    load: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply configured gap-filling rules and record value provenance.

    Parameters
    ----------
    load:
        Hourly demand data indexed by timestamp, with one column per country.
    config:
        Gap-filling configuration containing ``enabled`` and ``rules``.

    Returns:
    -------
    filled:
        Load after applying the configured rules. If gap filling is disabled,
        this is an unchanged copy of ``load``.
    value_source:
        Per-cell provenance such as ``observed``,
        ``linear_interpolation``, or ``missing``.
    """
    _validate_load(load)
    _validate_config(config)

    filled = load.copy()
    value_source = _initialise_value_source(load)

    if not config["enabled"]:
        logger.info("Gap filling is disabled.")
        return filled, value_source

    rules = config["rules"]
    original_gap_duration = calculate_missing_run_durations(load)

    for rule in rules:
        method = _get_method(rule)

        if method == LINEAR_INTERPOLATION:
            filled, newly_filled = apply_linear_interpolation(
                filled,
                max_gap=rule["max_gap"],
                original_gap_duration=original_gap_duration,
            )
        else:
            raise ValueError(
                f"Unsupported gap-filling method: {method!r}"
            )

        value_source = value_source.mask(newly_filled, method)
        _log_rule_results(method, newly_filled)

    unresolved = int(filled.isna().to_numpy().sum())
    logger.info(
        "Gap filling completed with %s unresolved values.",
        unresolved,
    )

    return filled, value_source

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
    method: str,
    newly_filled: pd.DataFrame,
) -> None:
    total = int(newly_filled.to_numpy().sum())

    logger.info(
        "Gap-filling method '%s' filled %s values.",
        method,
        total,
    )

    for country, count in newly_filled.sum().items():
        count = int(count)

        if count:
            logger.info(
                "%s: %s values filled using '%s'.",
                country,
                count,
                method,
            )

def _initialise_value_source(load: pd.DataFrame) -> pd.DataFrame:
    value_source = pd.DataFrame(
        "observed",
        index=load.index,
        columns=load.columns,
        dtype="string",
    )

    return value_source.mask(load.isna(), "missing")


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

