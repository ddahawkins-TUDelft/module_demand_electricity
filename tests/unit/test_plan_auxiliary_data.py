"""Tests for compiling the advanced execution plan."""

import json

import pandas as pd
import pytest
from cleaning.advanced.planning.execution import build_advanced_execution_plan
from cleaning.advanced.planning.source_requests import _build_batch_id, _build_group_id


def _config(
    overrides: dict,
    *,
    mode: str = "advanced",
    basic_cleaning_enabled: bool = False,
    basic_rules: list[dict] | None = None,
) -> dict:
    return {
        "mode": mode,
        "basic": {"rules": basic_rules or []},
        "advanced": {
            "auxiliary_data": {"basic_cleaning": {"enabled": basic_cleaning_enabled}},
            "overrides": overrides,
        },
    }


def _construct_override(
    *,
    source_country: str = "GRC",
    source_start: str = "2020-01-01",
    source_end: str = "2020-02-01",
) -> dict:
    return {
        "country": "ALB",
        "start": "2020-01-01",
        "end": "2020-02-01",
        "scope": "fill_gaps",
        "method": "construct_from_sources",
        "sources": [
            {
                "country": source_country,
                "start": source_start,
                "end": source_end,
                "weight": 1,
            }
        ],
    }


def _external_profile_override(
    *, country: str = "ALB", path: str = "resources/user/external_profiles/alb.csv"
) -> dict:
    return {
        "country": country,
        "start": "2020-01-01",
        "end": "2020-02-01",
        "scope": "fill_gaps",
        "method": "external_profile",
        "path": path,
    }


def _fill_plan(rule_names: list[str]) -> pd.DataFrame:
    if not rule_names:
        return pd.DataFrame()

    return pd.DataFrame(
        {"rule_name": rule_names, "status": ["ready"] * len(rule_names)}
    )


def _empty_execution_plan() -> dict:
    return {
        "version": 1,
        "active_rule_names": [],
        "rules": {},
        "batches": [],
        "batch_ids_by_source": {},
        "groups": {},
        "constructed_profile_rule_names": [],
        "external_profile_files": {},
    }


def test_plan_is_empty_outside_advanced_mode() -> None:
    result = build_advanced_execution_plan(
        fill_plan=_fill_plan(["example"]),
        gap_filling_config=_config({}, mode="basic"),
        source_names=["entsoe_api", "neso", "opsd_api"],
    )

    assert result == _empty_execution_plan()


def test_advanced_plan_with_empty_fill_plan_is_empty() -> None:
    result = build_advanced_execution_plan(
        fill_plan=pd.DataFrame(),
        gap_filling_config=_config({"fill_albania": _construct_override()}),
        source_names=["entsoe_api"],
    )

    assert result == _empty_execution_plan()


def test_plan_builds_complete_execution_manifest() -> None:
    override = _construct_override()

    result = build_advanced_execution_plan(
        fill_plan=_fill_plan(["fill_albania"]),
        gap_filling_config=_config({"fill_albania": override}),
        source_names=["entsoe_api", "opsd_api"],
    )

    start = pd.Timestamp("2020-01-01", tz="UTC")
    end = pd.Timestamp("2020-02-01", tz="UTC")
    group_id = _build_group_id(start=start, end=end)
    entsoe_batch_id = _build_batch_id(
        source="entsoe_api", start=start, end=end, countries=["GRC"]
    )
    opsd_batch_id = _build_batch_id(
        source="opsd_api", start=start, end=end, countries=["GRC"]
    )

    assert result == {
        "version": 1,
        "active_rule_names": ["fill_albania"],
        "rules": {
            "fill_albania": {"override": override, "required_group_ids": [group_id]}
        },
        "batches": [
            {
                "group_id": group_id,
                "batch_id": entsoe_batch_id,
                "source": "entsoe_api",
                "start": "2020-01-01T00:00:00+00:00",
                "end": "2020-02-01T00:00:00+00:00",
                "countries": ["GRC"],
                "years": [2020],
            },
            {
                "group_id": group_id,
                "batch_id": opsd_batch_id,
                "source": "opsd_api",
                "start": "2020-01-01T00:00:00+00:00",
                "end": "2020-02-01T00:00:00+00:00",
                "countries": ["GRC"],
                "years": [2020],
            },
        ],
        "batch_ids_by_source": {
            "entsoe_api": [entsoe_batch_id],
            "opsd_api": [opsd_batch_id],
        },
        "groups": {group_id: [entsoe_batch_id, opsd_batch_id]},
        "constructed_profile_rule_names": ["fill_albania"],
        "external_profile_files": {},
    }


def test_plan_uses_only_overrides_in_fill_plan() -> None:
    result = build_advanced_execution_plan(
        fill_plan=_fill_plan(["active"]),
        gap_filling_config=_config(
            {
                "active": _construct_override(source_country="GRC"),
                "inactive": _construct_override(source_country="SRB"),
            }
        ),
        source_names=["entsoe_api"],
    )

    assert result["active_rule_names"] == ["active"]
    assert list(result["rules"]) == ["active"]
    assert result["constructed_profile_rule_names"] == ["active"]
    assert all("GRC" in batch["countries"] for batch in result["batches"])
    assert all("SRB" not in batch["countries"] for batch in result["batches"])


def test_plan_preserves_configured_override_order() -> None:
    result = build_advanced_execution_plan(
        fill_plan=_fill_plan(["second", "first"]),
        gap_filling_config=_config(
            {
                "first": _construct_override(source_country="GRC"),
                "second": _construct_override(source_country="SRB"),
            }
        ),
        source_names=["entsoe_api"],
    )

    assert result["active_rule_names"] == ["first", "second"]
    assert list(result["rules"]) == ["first", "second"]
    assert result["constructed_profile_rule_names"] == ["first", "second"]


def test_plan_resolves_scaling_target_sources_to_groups() -> None:
    override = _construct_override()
    override["scaling"] = {
        "method": "match_energy",
        "target_sources": [
            {"country": "ALB", "start": "2020-03-01", "end": "2020-04-01", "weight": 1}
        ],
    }

    result = build_advanced_execution_plan(
        fill_plan=_fill_plan(["fill_albania"]),
        gap_filling_config=_config({"fill_albania": override}),
        source_names=["entsoe_api"],
    )

    expected_group_ids = sorted(
        [
            _build_group_id(
                start=pd.Timestamp("2020-01-01", tz="UTC"),
                end=pd.Timestamp("2020-02-01", tz="UTC"),
            ),
            _build_group_id(
                start=pd.Timestamp("2020-03-01", tz="UTC"),
                end=pd.Timestamp("2020-04-01", tz="UTC"),
            ),
        ]
    )

    assert result["rules"]["fill_albania"]["required_group_ids"] == expected_group_ids


def test_plan_resolves_rule_to_expanded_basic_cleaning_group() -> None:
    override = _construct_override()
    basic_rules = [
        {
            "name": "copy_previous_week",
            "method": "copy_period",
            "max_gap": "168h",
            "source_offset": "-168h",
            "require_complete_source": True,
        }
    ]

    result = build_advanced_execution_plan(
        fill_plan=_fill_plan(["fill_albania"]),
        gap_filling_config=_config(
            {"fill_albania": override},
            basic_cleaning_enabled=True,
            basic_rules=basic_rules,
        ),
        source_names=["entsoe_api"],
    )

    batch = result["batches"][0]

    assert batch["start"] < "2020-01-01T00:00:00+00:00"
    assert batch["end"] > "2020-02-01T00:00:00+00:00"
    assert result["rules"]["fill_albania"]["required_group_ids"] == [batch["group_id"]]


def test_non_construct_rule_requires_no_auxiliary_groups() -> None:
    override = {
        "country": "ALB",
        "start": "2020-01-01",
        "end": "2020-02-01",
        "scope": "fill_gaps",
        "method": "leave_missing",
    }

    result = build_advanced_execution_plan(
        fill_plan=_fill_plan(["leave_albania"]),
        gap_filling_config=_config({"leave_albania": override}),
        source_names=["entsoe_api"],
    )

    assert result["rules"] == {
        "leave_albania": {"override": override, "required_group_ids": []}
    }
    assert result["batches"] == []
    assert result["groups"] == {}
    assert result["constructed_profile_rule_names"] == []


def test_batch_years_use_half_open_period_semantics() -> None:
    result = build_advanced_execution_plan(
        fill_plan=_fill_plan(["fill_albania"]),
        gap_filling_config=_config(
            {
                "fill_albania": _construct_override(
                    source_country="GBR",
                    source_start="2020-12-31",
                    source_end="2021-01-01",
                )
            }
        ),
        source_names=["neso"],
    )

    assert result["batches"][0]["years"] == [2020]


def test_plan_rejects_unresolvable_auxiliary_group() -> None:
    with pytest.raises(
        ValueError, match="Expected exactly one auxiliary group covering"
    ):
        build_advanced_execution_plan(
            fill_plan=_fill_plan(["fill_albania"]),
            gap_filling_config=_config({"fill_albania": _construct_override()}),
            source_names=[],
        )


def test_plan_is_json_serializable() -> None:
    result = build_advanced_execution_plan(
        fill_plan=_fill_plan(["fill_albania"]),
        gap_filling_config=_config({"fill_albania": _construct_override()}),
        source_names=["entsoe_api"],
    )

    json.dumps(result)


def test_plan_records_active_external_profile_file() -> None:
    override = _external_profile_override(
        path="resources/user/external_profiles/alb_2020.csv"
    )

    result = build_advanced_execution_plan(
        fill_plan=_fill_plan(["external_albania"]),
        gap_filling_config=_config({"external_albania": override}),
        source_names=["entsoe_api"],
    )

    assert result["external_profile_files"] == {
        "external_albania": ("resources/user/external_profiles/alb_2020.csv")
    }

    assert result["constructed_profile_rule_names"] == []
    assert result["batches"] == []


def test_plan_excludes_inactive_external_profile_file() -> None:
    result = build_advanced_execution_plan(
        fill_plan=_fill_plan(["active"]),
        gap_filling_config=_config(
            {
                "active": _external_profile_override(path="resources/user/active.csv"),
                "inactive": _external_profile_override(
                    path="resources/user/inactive.csv"
                ),
            }
        ),
        source_names=["entsoe_api"],
    )

    assert result["external_profile_files"] == {"active": "resources/user/active.csv"}


def test_plan_allows_external_profile_file_reuse() -> None:
    shared_path = "resources/user/external_profiles/gbr_2000_2025.csv"

    result = build_advanced_execution_plan(
        fill_plan=_fill_plan(["gbr_period_one", "gbr_period_two"]),
        gap_filling_config=_config(
            {
                "gbr_period_one": _external_profile_override(
                    country="GBR", path=shared_path
                ),
                "gbr_period_two": _external_profile_override(
                    country="GBR", path=shared_path
                ),
            }
        ),
        source_names=["entsoe_api"],
    )

    assert result["external_profile_files"] == {
        "gbr_period_one": shared_path,
        "gbr_period_two": shared_path,
    }
