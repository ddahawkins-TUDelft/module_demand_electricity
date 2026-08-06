"""Tests for source-based advanced profile construction."""

import pandas as pd
import pytest
from cleaning.advanced.construct_from_sources import construct_from_sources


def test_construct_from_sources_is_not_yet_implemented() -> None:
    index = pd.date_range(
        "2021-01-01",
        periods=2,
        freq="h",
        tz="UTC",
    )

    load = pd.DataFrame(
        {"ALB": [1.0, 2.0]},
        index=index,
    )

    rule = {
        "country": "ALB",
        "start": "2021-01-01",
        "end": "2021-01-01 01:00",
        "scope": "overwrite_entire_period",
        "method": "construct_from_sources",
        "sources": [
            {
                "country": "ALB",
                "start": "2022-01-01",
                "end": "2022-01-01 01:00",
            }
        ],
    }

    with pytest.raises(
        NotImplementedError,
        match="construct_from_sources",
    ):
        construct_from_sources(
            load,
            rule_name="replace_albania",
            rule=rule,
        )