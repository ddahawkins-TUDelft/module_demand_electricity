"""Collection of auxiliary functions for this module."""

from datetime import datetime, timedelta, timezone


ENTSOE_POWER_STATISTICS_YEARS = set(
    range(2019, 2026)
)


def _as_utc(value):
    """Interpret naive timestamps as UTC and convert aware timestamps to UTC. Mirrors tclean logic."""
    parsed = datetime.fromisoformat(str(value))

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def years_for_period(start, end):
    """Return UTC calendar years intersected by the half-open period [start, end). Mirrors tclean logic."""
    start = _as_utc(start)
    end = _as_utc(end)

    if end <= start:
        raise ValueError("Temporal period end must be later than its start.")

    final_included_time = end - timedelta(microseconds=1)

    return list(range(start.year, final_included_time.year + 1))


def neso_annual_files(years):
    """Return reusable annual NESO raw-file paths for the requested years."""
    return [
        "<resources>/automatic/neso/" f"historic_demand_{int(year)}.csv"
        for year in years
    ]


def entsoe_annual_files(countries, years):
    """Return reusable ENTSO-E country-year raw-file paths."""
    return [
        "<resources>/automatic/entsoe/raw/" f"{country}/{int(year)}.parquet"
        for country in countries
        for year in years
    ]


def entsoe_power_statistics_annual_files(years):
    """Return supported annual ENTSO-E Power Statistics files."""
    return [
        (
            "<resources>/automatic/"
            "entsoe_power_statistics/raw/"
            f"{int(year)}.parquet"
        )
        for year in years
        if int(year) in ENTSOE_POWER_STATISTICS_YEARS
    ]

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
