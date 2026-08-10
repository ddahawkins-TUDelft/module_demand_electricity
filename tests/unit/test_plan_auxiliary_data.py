"""Tests for auxiliary acquisition planning."""

import pandas as pd
from cleaning.advanced.planning.source_requests import (
    _build_batch_id,
    _build_group_id,
)
from plan_auxiliary_data import build_auxiliary_acquisition_plan


def test_plan_is_empty_outside_advanced_mode() -> None:
    config = {
        "mode": "basic",
        "basic": {
            "rules": [],
        },
        "advanced": {
            "auxiliary_data": {
                "basic_cleaning": {
                    "enabled": True,
                }
            },
            "overrides": {},
        },
    }

    fill_plan = pd.DataFrame(
        {
            "rule_name": ["example"],
        }
    )

    result = build_auxiliary_acquisition_plan(
        fill_plan=fill_plan,
        gap_filling_config=config,
        source_names=[
            "entsoe_api",
            "neso",
            "opsd_api",
        ],
    )

    assert result == {
        "batches": [],
    }


def test_advanced_plan_with_no_overrides_is_empty() -> None:
    config = {
        "mode": "advanced",
        "basic": {
            "rules": [],
        },
        "advanced": {
            "auxiliary_data": {
                "basic_cleaning": {
                    "enabled": True,
                }
            },
            "overrides": {},
        },
    }

    fill_plan = pd.DataFrame()

    result = build_auxiliary_acquisition_plan(
        fill_plan=fill_plan,
        gap_filling_config=config,
        source_names=[
            "entsoe_api",
            "neso",
            "opsd_api",
        ],
    )

    assert result == {
        "batches": [],
    }


def test_advanced_plan_builds_serializable_source_batches() -> None:
    config = {
        "mode": "advanced",
        "basic": {
            "rules": [],
        },
        "advanced": {
            "auxiliary_data": {
                "basic_cleaning": {
                    "enabled": False,
                }
            },
            "overrides": {
                "fill_albania": {
                    "country": "ALB",
                    "start": "2020-01-01",
                    "end": "2020-02-01",
                    "scope": "fill_gaps_within_period",
                    "method": "construct_from_sources",
                    "sources": [
                        {
                            "country": "GRC",
                            "start": "2020-01-01",
                            "end": "2020-02-01",
                            "weight": 1,
                        }
                    ],
                }
            },
        },
    }

    fill_plan = pd.DataFrame(
        {
            "rule_name": ["fill_albania"],
            "method": ["construct_from_sources"],
            "status": ["ready"],
        }
    )

    result = build_auxiliary_acquisition_plan(
        fill_plan=fill_plan,
        gap_filling_config=config,
        source_names=[
            "entsoe_api",
            "opsd_api",
        ],
    )

    start = pd.Timestamp(
        "2020-01-01",
        tz="UTC",
    )
    end = pd.Timestamp(
        "2020-02-01",
        tz="UTC",
    )

    group_id = _build_group_id(
        start=start,
        end=end,
    )

    assert result == {
        "batches": [
            {
                "group_id": group_id,
                "batch_id": _build_batch_id(
                    source="entsoe_api",
                    start=start,
                    end=end,
                    countries=["GRC"],
                ),
                "source": "entsoe_api",
                "start": "2020-01-01T00:00:00+00:00",
                "end": "2020-02-01T00:00:00+00:00",
                "countries": ["GRC"],
            },
            {
                "group_id": group_id,
                "batch_id": _build_batch_id(
                    source="opsd_api",
                    start=start,
                    end=end,
                    countries=["GRC"],
                ),
                "source": "opsd_api",
                "start": "2020-01-01T00:00:00+00:00",
                "end": "2020-02-01T00:00:00+00:00",
                "countries": ["GRC"],
            },
        ]
    }


def test_empty_fill_plan_produces_no_acquisition_batches() -> None:
    config = {
        "mode": "advanced",
        "basic": {
            "rules": [],
        },
        "advanced": {
            "auxiliary_data": {
                "basic_cleaning": {
                    "enabled": False,
                }
            },
            "overrides": {
                "fill_albania": {
                    "country": "ALB",
                    "start": "2020-01-01",
                    "end": "2020-02-01",
                    "scope": "fill_gaps_within_period",
                    "method": "construct_from_sources",
                    "sources": [
                        {
                            "country": "GRC",
                            "start": "2020-01-01",
                            "end": "2020-02-01",
                            "weight": 1,
                        }
                    ],
                }
            },
        },
    }

    result = build_auxiliary_acquisition_plan(
        fill_plan=pd.DataFrame(),
        gap_filling_config=config,
        source_names=["entsoe_api"],
    )

    assert result == {
        "batches": [],
    }
