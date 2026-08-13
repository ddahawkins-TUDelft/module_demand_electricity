# European electricity demand

This module prepares hourly electricity-demand time series for European regions at arbitrary spatial resolution. National demand data from multiple sources are combined and cleaned before being spatially disaggregated using population data and aggregated to user-provided target regions.

The module supports configurable gap filling, including deterministic cleaning rules and advanced country- and period-specific strategies, whilst retaining provenance for observed and filled demand values.


<!-- Place an attractive image of module outputs here -->
<p align="center">
  <img src="./figures/plot_profiles.png">
</p>

## About
<!-- Please do not modify this templated section -->

This is a modular `snakemake` workflow created as part of the [Modelblocks project](https://www.modelblocks.org/). It can be imported directly into any `snakemake` workflow.

For more information, please consult the Modelblocks [documentation](https://modelblocks.readthedocs.io/en/latest/),
the [integration example](./tests/integration/Snakefile),
and the `snakemake` [documentation](https://snakemake.readthedocs.io/en/stable/snakefiles/modularization.html).

## Overview
<!-- Please describe the processing stages of this module here -->

The workflow first builds a cleaned national electricity-demand time series and then spatially distributes that demand to the user-provided target regions.

The main processing stages are:

1. Download electricity-demand data from the configured sources. Current sources include: ENTSO-E, OPSD, and NESO.
2. Combine the available demand sources according to their configured priority.
3. Apply basic gap-filling rules to gaps that can be resolved using deterministic rules.
4. In advanced mode, identify remaining gaps and apply explicitly configured country- and period-specific strategies.
5. Finalise the cleaned national demand time series and retain provenance for observed and filled values.
6. Download and prepare gridded population data as a spatial disaggregation proxy.
7. Disaggregate national demand to a population-weighted raster.
8. Re-aggregate the raster to the target shapes and assign the corresponding national demand profile to each region.

A simplified representation of the workflow is:

```text
Demand sources
      │
      ▼
Combine sources
      │
      ▼
Basic gap filling
      │
      ├── basic mode ──────────────────────┐
      │                                    │
      └── advanced mode ─► Advanced rules ─┤
                                           ▼
                               Final national demand
                                   + provenance
                                           │
                                           ▼
                                Population-weighted
                               spatial disaggregation
                                           │
                                           ▼
                                 Regional hourly demand
```

## Configuration
<!-- Please describe how to configure this module below -->

Please consult the configuration [README](./config/README.md) and the [configuration example](./config/config.yaml) for a general overview on the configuration options of this module.

## Input / output structure
<!-- Please describe input / output file placement below -->

The module requires user-provided target shapes and, when ENTSO-E data is used, a valid ENTSO-E API token. Optional external electricity-demand profiles can also be supplied for use in advanced gap-filling rules.

Intermediate data, including downloaded demand sources, cleaned national demand, provenance information, and auxiliary gap-filling data, are stored under `resources/automatic/`.

The final output contains hourly electricity demand in MW for the requested target regions and is written to the module results directory.

The workflow also produces diagnostic outputs, including a gap report describing unresolved missing periods and a cleaning timeline showing how observed and filled values contribute to the final national demand series. See [Provenance and diagnostics](#provenance-and-diagnostics) for more information.

Please consult the [interface file](./INTERFACE.yaml) for more information.

## Cleaning and Gap Handling

After the available electricity-demand sources have been combined, the resulting national time series are checked for missing values and cleaned according to the configured gap-filling mode.

Three modes are available:

- `off`:   no gap filling is applied.
- `basic`:   deterministic gap-filling rules are applied in the configured order.
- `advanced`:   basic gap filling is applied first, after which remaining gaps can be handled using explicitly configured country- and period-specific rules.

### Basic gap filling

Basic gap filling is intended for gaps that can be resolved using simple and reproducible rules, such as interpolation or copying values from a comparable period.

Rules are applied sequentially in the order in which they are configured. Values filled by an earlier rule are therefore available to subsequent rules.

Any gaps that remain after basic cleaning are retained rather than filled automatically with increasingly speculative values. These unresolved periods are reported in the [gap report](#provenance-and-diagnostics).

### Advanced gap filling

Advanced mode provides explicit strategies for gaps that cannot be resolved appropriately using the basic rules. Advanced rules are defined for a specific country and time period and can use one of the following methods:

- `construct_from_sources`: construct a demand profile from one or more alternative country or time-period sources.
- `external_profile`: use a user-provided electricity-demand profile.
- `leave_missing`: explicitly retain the remaining gap.

Advanced rules can either fill only missing values (`fill_gaps`) or replace all supplied values within the configured period (`overwrite`).

Configured time periods follow a half-open interval convention, `[start, end)`: the start timestamp is included and the end timestamp is excluded.

## Provenance and diagnostics

The workflow retains provenance information throughout the cleaning process so that observed electricity-demand values can be distinguished from values introduced by basic or advanced gap-filling rules.

Two diagnostic outputs are particularly useful when assessing data quality and configuring gap handling:

- **Gap report**: lists periods that remain unresolved after cleaning, including the affected country and time interval. This can be used to identify where additional advanced rules or external data may be required.
- **Cleaning timeline**: visualises the origin and cleaning method of demand values over time, making it easier to inspect source coverage, basic fills, advanced overrides, and remaining gaps.

These diagnostics are intended to support transparent gap handling rather than hide missing data behind automatic imputation.

## Development
<!-- Please do not modify this templated section -->

We use [`pixi`](https://pixi.sh/) as our package manager for development.
Once installed, run the following to clone this repository and install all dependencies.

```shell
git clone git@github.com:modelblocks-org/module_demand_electricity.git
cd module_demand_electricity
pixi install --all
```

Please be aware that this is a multi-environment project (see [pixi.toml](./pixi.toml) for details).
- `default`: used for development and integration testing.
Because it contains `Snakemake`, `conda` and `pytest` as dependencies it **should not be used** in `Snakemake` rules.
- `module`: contains minimal dependencies used in `Snakemake` rules.
If modified, be sure to export it to `Snakemake` so it can be recreated by module users:

```shell
# create module.yaml and conda-spec pin files in workflow/envs/
pixi run export-snakemake-env module
```


## Testing
<!-- Please do not modify this templated section -->

For testing, simply run:

```shell
pixi run test-integration
```

To test a minimal example of a workflow using this module:

```shell
pixi shell    # activate this project's environment
cd tests/integration/  # navigate to the integration example
snakemake --use-conda --cores 2  # run the workflow!
```

## References
<!-- Please provide thorough referencing below -->

This module is based on the following research and datasets:

* ENTSOE Transparency Platform (https://transparency.entsoe.eu)
* Open Power System Data (https://data.open-power-system-data.org)
* NESO Data Portal (https://www.neso.energy/data-portal/historic-demand-data)
* Schiavina M., Freire S., Carioli A., MacManus K. (2023):
  GHS-POP R2023A - GHS population grid multitemporal (1975-2030).European Commission, Joint Research Centre (JRC)
  PID: http://data.europa.eu/89h/2ff68a52-5b5b-4a22-8f40-c41da8332cfe, doi:10.2905/2FF68A52-5B5B-4A22-8F40-C41DA8332CFE

## Contributors ✨

Thanks goes to these wonderful people, sorted alphabetically ([emoji key](https://allcontributors.org/en/reference/emoji-key/)):

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tbody>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="http://www.flombardi.org"><img src="https://avatars.githubusercontent.com/u/26432077?v=4?s=100" width="100px;" alt="Francesco Lombardi"/><br /><sub><b>Francesco Lombardi</b></sub></a><br /><a href="#ideas-FLomb" title="Ideas, Planning, & Feedback">🤔</a> <a href="https://github.com/modelblocks-org/module_demand_electricity/commits?author=FLomb" title="Tests">⚠️</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://orcid.org/0000-0003-2288-6423"><img src="https://avatars.githubusercontent.com/u/72193617?v=4?s=100" width="100px;" alt="Ivan Ruiz Manuel"/><br /><sub><b>Ivan Ruiz Manuel</b></sub></a><br /><a href="https://github.com/modelblocks-org/module_demand_electricity/pulls?q=is%3Apr+reviewed-by%3Airm-codebase" title="Reviewed Pull Requests">👀</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/jnnr"><img src="https://avatars.githubusercontent.com/u/32454596?v=4?s=100" width="100px;" alt="Jann Launer"/><br /><sub><b>Jann Launer</b></sub></a><br /><a href="https://github.com/modelblocks-org/module_demand_electricity/commits?author=jnnr" title="Documentation">📖</a> <a href="https://github.com/modelblocks-org/module_demand_electricity/commits?author=jnnr" title="Code">💻</a> <a href="#ideas-jnnr" title="Ideas, Planning, & Feedback">🤔</a> <a href="https://github.com/modelblocks-org/module_demand_electricity/commits?author=jnnr" title="Tests">⚠️</a></td>
    </tr>
  </tbody>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind welcome!
