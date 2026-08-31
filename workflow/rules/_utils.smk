"""Collection of auxiliary functions for this module."""

from datetime import datetime, timedelta, timezone
import yaml


SOURCE_REGISTRY_PATH = workflow.source_path(
    "../internal/source_registry.yaml"
)

with open(
    SOURCE_REGISTRY_PATH,
    encoding="utf-8",
) as file:
    SOURCE_REGISTRY = yaml.safe_load(file) or {}

if not isinstance(SOURCE_REGISTRY, dict):
    raise ValueError(
        "Source registry must contain a mapping "
        "of source identifiers to metadata."
    )


def _as_utc(value):
    """Interpret naive timestamps as UTC and convert aware timestamps to UTC. Mirrors tclean logic."""
    parsed = datetime.fromisoformat(str(value))

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def source_overlaps_period(
    source_name,
    start,
    end,
):
    """Return whether a source can supply any part of a period."""
    metadata = SOURCE_REGISTRY[source_name]
    temporal_scope = metadata.get("temporal_scope") or {}

    source_start = temporal_scope.get("start")
    source_end = temporal_scope.get("end")

    start = _as_utc(start)
    end = _as_utc(end)

    if source_start is not None:
        source_start = _as_utc(source_start)

        if end <= source_start:
            return False

    if source_end is not None:
        source_end = _as_utc(source_end)

        if start >= source_end:
            return False

    return True


def years_for_period(start, end):
    """Return UTC calendar years intersected by the half-open period [start, end). Mirrors tclean logic."""
    start = _as_utc(start)
    end = _as_utc(end)

    if end <= start:
        raise ValueError("Temporal period end must be later than its start.")

    final_included_time = end - timedelta(microseconds=1)

    return list(range(start.year, final_included_time.year + 1))


def source_year_pattern(source_name):
    """Return a year wildcard pattern for a bounded source."""
    temporal_scope = (
        SOURCE_REGISTRY[source_name].get("temporal_scope")
        or {}
    )

    start = temporal_scope.get("start")
    end = temporal_scope.get("end")

    if start is None or end is None:
        return "[0-9]{4}"

    return "|".join(
        str(year)
        for year in years_for_period(start, end)
    )


def additional_config_validation():
    """Validate configuration relationships that require no module dependencies."""
    gap_filling = config["gap_filling"]

    if gap_filling["mode"] != "advanced":
        return

    advanced = gap_filling["advanced"]
    sources = advanced["sources"]
    advanced_rules = advanced["rules"]

    seen_rule_names = set()
    duplicate_rule_names = set()

    for rule in advanced_rules:
        rule_name = rule["name"]

        if rule_name in seen_rule_names:
            duplicate_rule_names.add(rule_name)

        seen_rule_names.add(rule_name)

    if duplicate_rule_names:
        raise ValueError(
            "Advanced cleaning rule names must be unique. "
            f"Duplicate names: {sorted(duplicate_rule_names)}."
        )

    for rule in advanced_rules:
        source_name = rule.get("source")

        # A rule without a source explicitly leaves the target values missing.
        if source_name is None:
            continue

        if source_name not in sources:
            raise ValueError(
                f"Advanced rule {rule['name']!r} references unknown "
                f"advanced source {source_name!r}."
            )


def validate_source_names(source_names):
    """Require configured demand sources to exist in the source registry."""
    unknown_sources = [
        source_name
        for source_name in source_names
        if source_name not in SOURCE_REGISTRY
    ]

    if unknown_sources:
        raise ValueError(
            "Unsupported electricity-demand source(s): "
            f"{unknown_sources}. "
            "Available sources are: "
            f"{sorted(SOURCE_REGISTRY)}."
        )


validate_source_names(config["load_sources"])
