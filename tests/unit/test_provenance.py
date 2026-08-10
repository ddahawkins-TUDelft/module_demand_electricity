"""Tests for provenance rules."""

from cleaning.provenance import build_final_cleaning_rules


def test_build_final_cleaning_rules_includes_advanced_overrides():
    config = {
        "mode": "advanced",
        "basic": {
            "rules": [
                {
                    "name": "basic_rule",
                    "method": "linear_interpolation",
                }
            ]
        },
        "advanced": {
            "overrides": {
                "advanced_rule": {
                    "method": "construct_from_sources",
                }
            }
        },
    }

    rules = build_final_cleaning_rules(config)

    assert [rule["name"] for rule in rules] == [
        "basic_rule",
        "advanced_rule",
    ]

def test_build_final_cleaning_rules_excludes_advanced_overrides_in_basic_mode():
    config = {
        "mode": "basic",
        "basic": {
            "rules": [
                {
                    "name": "basic_rule",
                    "method": "linear_interpolation",
                }
            ]
        },
        "advanced": {
            "overrides": {
                "advanced_rule": {
                    "method": "construct_from_sources",
                }
            }
        },
    }

    rules = build_final_cleaning_rules(config)

    assert [rule["name"] for rule in rules] == [
        "basic_rule",
    ]
