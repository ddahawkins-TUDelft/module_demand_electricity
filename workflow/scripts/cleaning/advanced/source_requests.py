"""Plan source requests for auxiliary electricity-demand data."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence

import pandas as pd

SOURCE_REQUEST_COLUMNS = [
    "source",
    "country",
    "start",
    "end",
]

SUPPORTED_SOURCES = {
    "entsoe_api",
    "neso",
    "opsd_api",
}


def build_auxiliary_source_requests(
    requirements: pd.DataFrame,
    *,
    source_names: Sequence[str],
) -> pd.DataFrame:
    """Map auxiliary requirements onto applicable configured sources."""
    _validate_source_names(source_names)

    if requirements.empty:
        return pd.DataFrame(
            columns=SOURCE_REQUEST_COLUMNS
        )

    requests: list[dict[str, object]] = []

    for source_name in source_names:
        for row in requirements.itertuples(index=False):
            if not _source_supports_country(
                source_name,
                row.country,
            ):
                continue

            requests.append(
                {
                    "source": source_name,
                    "country": row.country,
                    "start": row.start,
                    "end": row.end,
                }
            )

    return pd.DataFrame(
        requests,
        columns=SOURCE_REQUEST_COLUMNS,
    )


def _source_supports_country(
    source_name: str,
    country: str,
) -> bool:
    """Return whether a source is structurally applicable to a country."""
    if source_name == "neso":
        return country == "GBR"

    if source_name in {
        "entsoe_api",
        "opsd_api",
    }:
        return True

    raise ValueError(
        f"Unsupported auxiliary load source: {source_name!r}"
    )


def _validate_source_names(
    source_names: Sequence[str],
) -> None:
    """Validate configured sources used for auxiliary acquisition."""
    unknown = [
        source_name
        for source_name in source_names
        if source_name not in SUPPORTED_SOURCES
    ]

    if unknown:
        raise ValueError(
            "Unsupported auxiliary load sources: "
            f"{unknown}"
        )

    if len(source_names) != len(set(source_names)):
        raise ValueError(
            "Auxiliary load source names must be unique."
        )

def build_auxiliary_source_batches(
    requests: pd.DataFrame,
) -> list[dict[str, object]]:
    """Group compatible auxiliary source requests into batches."""
    if requests.empty:
        return []

    batches: list[dict[str, object]] = []

    grouped = requests.groupby(
        [
            "source",
            "start",
            "end",
        ],
        sort=False,
    )

    for (
        source,
        start,
        end,
    ), group in grouped:
        countries = sorted(
            group["country"]
            .unique()
            .tolist()
        )

        batches.append(
            {
                "group_id": _build_group_id(
                    start=start,
                    end=end,
                ),
                "batch_id": _build_batch_id(
                    source=source,
                    start=start,
                    end=end,
                    countries=countries,
                ),
                "source": source,
                "start": start,
                "end": end,
                "countries": countries,
            }
        )

    return batches


def _build_batch_id(
    *,
    source: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
    countries: list[str],
) -> str:
    """Build a deterministic identifier for an auxiliary source batch."""
    countries_key = ",".join(
        sorted(countries)
    )

    countries_hash = hashlib.sha1(
        countries_key.encode("utf-8")
    ).hexdigest()[:8]

    return (
        f"{source}__"
        f"{start.strftime('%Y%m%dT%H%M')}__"
        f"{end.strftime('%Y%m%dT%H%M')}__"
        f"{countries_hash}"
    )


def _build_group_id(
    *,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> str:
    """Build a deterministic identifier for an auxiliary period group."""
    return (
        f"{start.strftime('%Y%m%dT%H%M')}__"
        f"{end.strftime('%Y%m%dT%H%M')}"
    )
