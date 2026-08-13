# Configuration

This module is configured through `config/config.yaml`.

We recommend consulting the following alongside this file:

- [`config/config.yaml`](./config.yaml): example configuration for this module.
- [`workflow/internal/config.schema.yaml`](../workflow/internal/config.schema.yaml): complete schema defining valid configuration options.
- [`INTERFACE.yaml`](../INTERFACE.yaml): module input and output files and their default locations.
- [`tests/integration/Snakefile`](../tests/integration/Snakefile): example of how to import and call this module from another workflow.

This data module is part of the [Modelblocks](https://www.modelblocks.org/) project.
Please consult the [Modelblocks documentation](https://modelblocks.readthedocs.io/) for more information.

## Temporal scope

The requested electricity-demand period is configured using `temporal_scope`.

```yaml
temporal_scope:
  start: "2016-01-01"
  end: "2026-01-01"
```

## Demand sources

The load_sources setting defines which demand datasets are used and their priority order.

```yaml
load_sources:
  - entsoe_api
  - neso
  - opsd_api
```

Sources are combined in the order listed. Where more than one source provides a value for the same country and timestamp, the higher-priority source is retained.

Available sources are:

- `entsoe_api`: ENTSO-E Transparency Platform data
- `neso`: historical demand data from the National Energy System Operator for Great Britain.
- `opsd_api`: historical demand data from Open Power System Data.

## Gap filling
Gap handling is configured under `gap_filling`.

```yaml
gap_filling:
  mode: basic
```

### Modes
Three modes are available:

- `off`: do not apply gap filling.
- `basic`: apply deterministic gap-filling rules in the configured order.
- `advanced`: apply basic gap filling first, then process remaining gaps using explicitly configured advanced rules.


## Basic gap filling
Basic rules are listed under `gap_filling.basic.rules` and are applied sequentially in the order in which they appear.

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
        method: copy_period
        max_gap: 168h
        source_offset: -168h

      - name: copy_following_week
        method: copy_period
        max_gap: 168h
        source_offset: 168h
```
Each rule must have a unique `name`. The rule name is retained in the cleaning provenance and diagnostic plots, and should therefore be descriptive.

### linear_interpolation

Interpolates across missing periods up to the configured `max_gap`.

```yaml
- name: interpolate_short_gaps
  method: linear_interpolation
  max_gap: 3h
```

### average_periods

Fills a gap using the average of one or more periods offset from the missing interval.

```yaml
- name: average_adjacent_weeks
  method: average_periods
  max_gap: 326h
  source_offsets:
    - -7d
    - 7d
```

In this example, the value from the same hour one week earlier and one week later is averaged.

### copy_period

Copies values from a period offset from the missing interval.

```yaml
- name: copy_previous_week
  method: copy_period
  max_gap: 168h
  source_offset: -168h
```
A positive offset copies from a later period; a negative offset copies from an earlier period.

## Advanced gap filling
Advanced mode is intended for gaps that cannot be resolved appropriately using the deterministic basic rules.

Advanced rules are defined under:

```yaml
gap_filling:
  mode: advanced

  advanced:
    auxiliary_data:
    overrides:

      example_override_rule_name:
        ...
```

Each override targets a specific country and time period and defines:

- `country`: ISO3 country code.
- `start`: start of the target period.
- `end`: end of the target period.
- `scope`: whether to fill only missing values or overwrite supplied values.
- `method`: the advanced strategy to apply.

Override names must be unique and use lowercase letters, numbers, and underscores.

### Active and inactive overrides

Advanced overrides may be kept in the configuration even when they are not relevant to the current model run.

An override is **active** when its target country and time period overlap with the demand being processed. Only active overrides are included in the advanced gap-filling workflow. Overrides that fall outside the current target countries or `temporal_scope` are considered **inactive** and are not executed.

This allows a configuration to maintain a reusable collection of known gap-handling rules across countries and time periods. For example, a project may keep established overrides for Albania, Cyprus, and North Macedonia in the same configuration while running a model instance that only requires Albania. The rules for the other countries remain available but do not trigger unnecessary auxiliary data acquisition or processing.

In the example below, if the current run covers Albania in 2022 but not Montenegro in 2020, fill_alb_2022 is active while fill_mne_2020 remains inactive.

```yaml
advanced:
  overrides:
    fill_alb_2022:
      country: ALB
      start: "2022-01-01"
      end: "2022-02-01"
      scope: fill_gaps
      method: construct_from_sources
      ...

    fill_mne_2020:
      country: MNE
      start: "2020-03-01"
      end: "2020-04-01"
      scope: fill_gaps
      method: construct_from_sources
      ...
```

> [!IMPORTANT]
> All configured overrides must still be valid according to the configuration schema. An inactive rule is ignored because it is outside the current model scope, not because invalid configuration is tolerated.


### Scope

Two scopes are supported:

- `fill_gaps`: only missing target values are replaced.
- `overwrite`: all values supplied by the advanced rule within the configured target period are replaced. Note, this method forces existing values to be overwritten.

### Method
Three methods are currently supported:
- `construct_from_sources`: builds a synthetic profile from one or more alternative country-period sources using a weighted-average method configured by the user.
- `external_profile`: reads a profile from a user-provided CSV file.
- `leave_missing`: explicitly leaves the specified period unresolved.

### Timestamps

All configured timestamps refer to the module's hourly UTC time index.

For YAML configuration, timestamps may be written in one of the following forms:

```yaml
start: "2022-01-01"
end: "2022-02-01"
```
or, when an hour must be specified explicitly:

```yaml
start: "2022-01-01 00:00"
end: "2022-02-01 00:00"
```

A date without an explicit time represents 00:00 at the start of that date.

Configured periods follow a half-open interval convention, [start, end): the start timestamp is included and the end timestamp is excluded.

> [!Important]
> Naive timestamps in the configuration are interpreted consistently with the module's UTC hourly time index; external profiles should use ISO 8601 timestamps and are therefore recommended to be supplied explicitly in UTC using `Z`. See [Advanced Method: `external_profile`](#advanced-method-external_profile).

## Advanced Method: `construct_from_sources`

`construct_from_sources` builds a synthetic profile from one or more alternative country-period sources using a weighted-average method configured by the user.

```yaml
example_rule_construct_from_sources:
  country: ALB
  start: "2022-01-01"
  end: "2022-02-01"
  scope: fill_gaps
  method: construct_from_sources

  sources:
    - country: GRC
      start: "2022-01-01"
      end: "2022-02-01"
      weight: 1
    - country: MKD
      start: "2022-01-01"
      end: "2022-02-01"
      weight: 3

  scaling:
    method: match_energy
    target_sources:
      - country: ALB
        start: "2024-01-01"
        end: "2024-02-01"
        weight: 1
```

The source period must describe the same number of hourly timestamps as the target period.

Multiple sources may be supplied. Their weight values determine their relative contribution to the constructed profile.

> [!IMPORTANT]
> Weighting is relative and values provided are normalised such that all weights sum to 1, i.e. in the example above, `GRC` has a relative contribution of `0.25` and `MKD` has a relative contribution of `0.75`.

> [!NOTE]
> The combination of `scope: overwrite` and providing a single source, effectively provides a broad copy-paste function.

### Scaling

A constructed profile can optionally be scaled before it is applied. This is helpful where sources are from other countries with different average energy consumptions.

The currently supported scaling method is:

```yaml
scaling:
  method: match_energy
```

`match_energy` scales the constructed profile so that its total energy matches the weighted energy of the configured target_sources.

This allows the temporal shape of one country or period to be used while matching the overall demand level of a more representative target period.

## Advanced Method: `external_profile`
`external_profile` applies demand values supplied in a user-provided .CSV file.

```yaml
external_alb_profile:
  country: ALB
  start: "2022-01-01 00:00"
  end: "2022-01-08 00:00"
  scope: overwrite
  method: external_profile
  path: inputs/external_profiles/alb_external.csv
```

External profiles must contain exactly two columns and use ISO 8601 timestamps with an explicit UTC designator:

```csv
timestamp,demand
2022-01-01T00:00:00Z,723.0
2022-01-01T01:00:00Z,716.0
```

Requirements:

- timestamp must contain parseable hourly timestamps.
- timestamps must be unique.
- timestamps must be aligned to whole hours.
- demand must be numeric and non-missing.
- sparse profiles are allowed.

Only timestamps present in both the external profile and the configured target period are applied.

## Advanced Method: `leave_missing`

`leave_missing` explicitly accepts that a target period remains unresolved.

```yaml
leave_alb_gap:
  country: ALB
  start: "2016-01-01"
  end: "2016-02-01"
  scope: fill_gaps
  method: leave_missing
```

No replacement values are generated. The missing period remains visible in the cleaned demand series and diagnostic outputs.

## Auxiliary Data
Advanced rules that construct profiles from other countries or periods may require additional demand data outside the main requested target period.

Auxiliary acquisition is configured under:
```yaml
advanced:
  auxiliary_data:
    basic_cleaning:
      enabled: true
```
When enabled, the same basic gap-filling logic is applied to auxiliary demand before it is used to construct an advanced profile.


## Complete example

```yaml
temporal_scope:
  start: "2020-01-01"
  end: "2025-01-01"

load_sources:
  - entsoe_api
  - neso
  - opsd_api

gap_filling:
  mode: advanced

  basic:
    rules:
      - name: interpolate_short_gaps
        method: linear_interpolation
        max_gap: 3h

      - name: copy_previous_week
        method: copy_period
        max_gap: 168h
        source_offset: -168h

  advanced:
    auxiliary_data:
      basic_cleaning:
        enabled: true

    overrides:

      # This rule  constructs a synthetic profile from GRC
      # and MKD Jan 2022, rescales to ALB Jan 2024 average
      # energy levels, and fill gaps in ALB Jan 2022. It
      # does not overwrite existing values.
      build_alb_winter:
        country: ALB
        start: "2022-01-01"
        end: "2022-02-01"
        scope: fill_gaps
        method: construct_from_sources
        sources:
          - country: GRC
          start: "2022-01-01"
          end: "2022-02-01"
          weight: 1
          - country: MKD
          start: "2022-01-01"
          end: "2022-02-01"
          weight: 3
        scaling:
          method: match_energy
          target_sources:
          - country: ALB
            start: "2024-01-01"
            end: "2024-02-01"
            weight: 1

      # This rule overwrites ALB 2021 using an external
      # profile, including any values that do exist from
      # the original ENTSO-E/NESO/OPSD download.
      external_alb_profile:
        country: ALB
        start: "2021-01-01 00:00"
        end: "2022-01-01 00:00"
        scope: overwrite
        method: external_profile
        path: inputs/external_profiles/alb_external.csv

      # This rule intentionally leaves missing values.
      # This rule is inactive because its target period lies
      # outside the configured temporal_scope.
      leave_alb_gap:
        country: ALB
        start: "2016-01-01"
        end: "2017-01-01"
        scope: fill_gaps
        method: leave_missing
```
