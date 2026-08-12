from collections.abc import Mapping

from common.time import as_utc_timestamp


def get_required_auxiliary_sources(
    override: Mapping,
) -> list[Mapping]:
    """Return all auxiliary sources consumed by an override."""
    sources = list(override["sources"])

    scaling = override.get("scaling")
    if scaling is not None:
        sources.extend(
            scaling.get("target_sources", [])
        )

    return sources


def get_required_auxiliary_group_ids(
    plan: Mapping,
    *,
    override: Mapping,
) -> list[str]:
    """Return auxiliary groups required to execute one override."""
    group_ids: set[str] = set()

    for source in get_required_auxiliary_sources(override):
        country = source["country"]
        start = as_utc_timestamp(source["start"])
        end = as_utc_timestamp(source["end"])

        matching_groups = {
            batch["group_id"]
            for batch in plan["batches"]
            if (
                country in batch["countries"]
                and as_utc_timestamp(batch["start"]) <= start
                and as_utc_timestamp(batch["end"]) >= end
            )
        }

        if len(matching_groups) != 1:
            raise ValueError(
                "Expected exactly one auxiliary group covering "
                f"{country!r} from {start} to {end}, "
                f"found {sorted(matching_groups)}."
            )

        group_ids.update(matching_groups)

    return sorted(group_ids)
