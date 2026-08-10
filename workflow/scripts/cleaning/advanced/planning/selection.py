from collections.abc import Mapping, Sequence

from common.time import as_utc_timestamp


def get_auxiliary_batch(
    plan: Mapping,
    *,
    batch_id: str,
    source: str,
) -> Mapping:
    """Return one source batch from an auxiliary acquisition plan."""
    matches = [
        batch
        for batch in plan["batches"]
        if (
            batch["batch_id"] == batch_id
            and batch["source"] == source
        )
    ]

    if len(matches) != 1:
        raise ValueError(
            "Expected exactly one auxiliary batch for "
            f"{source=} and {batch_id=}, found {len(matches)}."
        )

    return matches[0]


def get_auxiliary_group_batches(
    plan: Mapping,
    *,
    group_id: str,
) -> list[Mapping]:
    """Return acquisition batches belonging to one auxiliary group."""
    batches = [
        batch
        for batch in plan["batches"]
        if batch["group_id"] == group_id
    ]

    if not batches:
        raise ValueError(
            f"No auxiliary batches found for group {group_id!r}."
        )

    return batches


def get_source_batch_ids(
    plan: Mapping,
    *,
    source: str,
) -> list[str]:
    """Return batch identifiers for one auxiliary source."""
    return [
        batch["batch_id"]
        for batch in plan["batches"]
        if batch["source"] == source
    ]


def get_auxiliary_group_ids(
    plan: Mapping,
) -> list[str]:
    """Return all auxiliary group identifiers."""
    return sorted(
        {
            batch["group_id"]
            for batch in plan["batches"]
        }
    )


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
