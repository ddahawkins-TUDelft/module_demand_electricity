"""Collection of auxiliary functions for this module."""


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
