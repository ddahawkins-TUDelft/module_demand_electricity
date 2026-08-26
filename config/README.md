# Configuration

This module is configured through `config/config.yaml`.

The configuration schema is intentionally strict: malformed or unsupported configuration should fail validation rather than silently falling back to defaults.

Useful references are:

- [`config/config.yaml`](./config.yaml): example configuration;
- [`workflow/internal/config.schema.yaml`](../workflow/internal/config.schema.yaml): authoritative configuration schema;
- [`INTERFACE.yaml`](../INTERFACE.yaml): module input/output interface;
- [`tests/integration/test_config.yaml`](../tests/integration/test_config.yaml): a richer integration configuration;
- [`tests/integration/Snakefile`](../tests/integration/Snakefile): example module import.

## Temporal scope

`temporal_scope` defines the regular target time grid used for demand cleaning.

```yaml
temporal_scope:
  start: "2017-01-01"
  end: "2017-01-03"
  frequency: "1h"
```

The grid follows a half-open interval:

```text
[start, end)
```

so `start` is included and `end` is excluded.

The period length must be an integer multiple of `frequency`. The `start` timestamp also anchors the grid phase, so timestamps used by provider data, auxiliary data, and external profiles must align with the configured grid.

Date-only timestamps represent midnight. Date-time strings may be used when the grid needs a non-midnight start or another explicit offset.

## Demand sources

`load_sources` selects the national demand providers and defines their priority.

```yaml
load_sources:
  - entsoe
  - neso
  - opsd
```

Available identifiers are:

- `entsoe`: ENTSO-E Transparency Platform;
- `neso`: National Energy System Operator historic demand;
- `opsd`: Open Power System Data.

Sources are combined in the listed order. When more than one provider supplies a value for the same country and timestamp, the higher-priority provider is retained.

## Gap filling

Gap handling is configured below `gap_filling`.

```yaml
gap_filling:
  mode: basic
```

Three modes are available:

- `off`: no gap filling;
- `basic`: apply deterministic basic rules in configured order;
- `advanced`: run basic cleaning first and then apply configured advanced rules that are active for the current target countries and time grid.

## Basic gap filling

Basic rules are listed under `gap_filling.basic.rules`.

```yaml
gap_filling:
  mode: basic

  basic:
    rules:
      - name: interpolate_short_gaps
        method: linear_interpolation
        max_gap: 3h

      - name: average_adjacent_weeks
        method: average_periods
        max_gap: 326h
        source_offsets:
          - -7d
          - 7d

      - name: copy_previous_week
        method: copy_periods
        max_gap: 168h
        source_offset: -168h
        require_complete_source: true

      - name: copy_following_week
        method: copy_periods
        max_gap: 168h
        source_offset: 168h
        require_complete_source: true
```

Rules are applied sequentially. Values filled by an earlier rule are therefore available to later rules.

Each rule requires a unique, descriptive `name`. Rule names are retained in cleaning provenance and diagnostic outputs.

### `linear_interpolation`

Interpolates across missing periods up to `max_gap`.

```yaml
- name: interpolate_short_gaps
  method: linear_interpolation
  max_gap: 3h
```

### `average_periods`

Uses the mean of corresponding values from one or more offset periods.

```yaml
- name: average_adjacent_weeks
  method: average_periods
  max_gap: 326h
  source_offsets:
    - -7d
    - 7d
```

In this example, corresponding values one week before and one week after the gap are averaged.

### `copy_periods`

Copies corresponding values from a configured offset period.

```yaml
- name: copy_previous_week
  method: copy_periods
  max_gap: 168h
  source_offset: -168h
  require_complete_source: true
```

A negative `source_offset` uses an earlier period; a positive offset uses a later period.

`require_complete_source: true` requires the source period needed for the copy to be complete before that rule can fill the target gap.

## Advanced gap filling

Advanced mode separates two concepts:

1. **sources** describe how an advanced profile is obtained;
2. **rules** describe the target country, period, scope, and source to apply.

This keeps reusable source definitions separate from their application.

The overall structure is:

```yaml
gap_filling:
  mode: advanced

  basic:
    rules: [...]

  advanced:
    auxiliary_data:
      basic_cleaning:
        enabled: true

    sources:
      example_source:
        method: construct_from_sources
        periods: [...]

    rules:
      - name: example_rule
        country: ALB
        start: "2017-01-01"
        end: "2017-01-03"
        scope: overwrite
        source: example_source
```

### Active and inactive rules

Advanced rules may remain in a reusable configuration even when they do not apply to a particular run.

A rule is **active** when:

- its target country is part of the demand being processed; and
- its target interval overlaps the configured target time grid.

A rule outside the current countries or time grid is **inactive** and does not trigger auxiliary-data acquisition or profile construction.

Activity is determined from target scope, not from whether a matching gap happens to remain after basic cleaning. In particular, a `fill_gaps` rule can be active even when there is ultimately nothing for it to fill.

All configured rules must still be valid according to the schema. Inactivity does not make invalid configuration acceptable.

### Rule scopes

Two scopes are supported:

- `fill_gaps`: replace missing target values only;
- `overwrite`: replace target values throughout the rule period.

### Advanced periods

Advanced target and source periods follow the same half-open convention as the model grid:

```text
[start, end)
```

Source periods used to construct a target profile must have the temporal length required by the target construction.

## Advanced source: `construct_from_sources`

A `construct_from_sources` source builds a profile from one or more configured country-period profiles.

```yaml
advanced:
  sources:
    alb_from_gbr_alb_winter:
      method: construct_from_sources
      periods:
        - country: GBR
          start: "2024-01-01"
          end: "2024-02-01"
          weight: 1

      scaling:
        method: match_energy
        periods:
          - country: ALB
            start: "2024-01-01"
            end: "2024-02-01"
            weight: 1
```

Each `periods` entry identifies:

- `country`;
- `start`;
- `end`;
- `weight`.

Weights are relative contributions and must be finite and positive.

Multiple source periods can be combined. Their relative weights determine their contribution to the constructed profile.

### Scaling constructed profiles

A constructed profile may optionally be rescaled.

The currently configured scaling strategy is:

```yaml
scaling:
  method: match_energy
  periods:
    - country: ALB
      start: "2024-01-01"
      end: "2024-02-01"
      weight: 1
```

`match_energy` uses the configured scaling periods to align the overall energy level of the constructed profile with a more representative reference.

Scaling periods can require auxiliary demand data outside the main target grid; the workflow includes them when compiling acquisition requirements.

## Advanced source: `external_profile`

An `external_profile` source reads a user-supplied CSV.

```yaml
advanced:
  sources:
    alb_external:
      method: external_profile
      file: inputs/external_profiles/alb_external.csv
```

The target country, period, and application scope belong to the **rule**, not to the source:

```yaml
advanced:
  rules:
    - name: use_alb_external_profile
      country: ALB
      start: "2022-01-01 00:00"
      end: "2022-01-08 00:00"
      scope: overwrite
      source: alb_external
```

External profile CSVs use the generic T-Clean column contract:

```csv
timestamp,value
2022-01-01T00:00:00Z,723.0
2022-01-01T01:00:00Z,716.0
```

The profile must use valid, unique timestamps aligned with the target grid, and numeric non-missing values. Sparse profiles are permitted where supported by the configured rule/application behavior.

## Explicitly leaving values missing

Advanced configuration can explicitly retain unresolved values rather than fabricate a profile. This is useful when missing data is known and accepted.

Consult the authoritative configuration schema for the exact `leave_missing` source/rule form supported by the current module version.

## Auxiliary data

Advanced constructed profiles can require demand observations from countries or periods outside the main target grid.

Auxiliary behavior is configured under:

```yaml
advanced:
  auxiliary_data:
    basic_cleaning:
      enabled: true
```

When enabled, the configured basic cleaning rules are also applied to auxiliary demand before it is used in advanced profile construction.

The module determines auxiliary acquisition requirements only for **active** advanced rules. Provider acquisition and preparation remain Modelblocks responsibilities; generic planning and cleaning behavior is delegated to T-Clean.

## End-to-end tested example

For a complete configuration used by the integration workflow, see
[`tests/integration/test_config.yaml`](../tests/integration/test_config.yaml).

This configuration is exercised by the integration test suite and therefore
serves as the canonical end-to-end example. The examples above are intentionally
focused on individual configuration features.

## Validation

Configuration is checked in two layers:

1. the YAML schema checks structure, permitted values, required fields, and basic types;
2. semantic validation checks constraints that depend on relationships between fields, such as time-grid alignment, unique rule/source names, valid source references, and compatible advanced periods.

Invalid configuration should be corrected at source rather than handled through silent fallbacks.

For the complete accepted configuration contract, refer to [`workflow/internal/config.schema.yaml`](../workflow/internal/config.schema.yaml).
