# European electricity demand

This module prepares regular electricity-demand time series for target regions. National demand observations from multiple providers are combined, cleaned, and evaluated for data-quality issues on a user-defined time grid, then spatially disaggregated using population data and aggregated to user-provided shapes.

<p align="center">
  <img src="./figures/readme_cleaning_timeline.jpg">
</p>
<p align="center">
  <em>Example diagnostic showing electricity-demand data provenance.</em>
</p>

## About
<!-- Please do not modify this templated section -->

This is a modular `snakemake` workflow created as part of the [Modelblocks project](https://www.modelblocks.org/). It can be imported directly into any `snakemake` workflow.

For more information, please consult the Modelblocks [documentation](https://modelblocks.readthedocs.io/en/latest/),
the [integration example](./tests/integration/Snakefile),
and the `snakemake` [documentation](https://snakemake.readthedocs.io/en/stable/snakefiles/modularization.html).

## Overview

The workflow first prepares a cleaned national electricity-demand time series on the configured time grid and then spatially distributes that demand to the requested target regions.

The main processing stages are:

1. Download demand data from the configured providers.
2. Prepare each provider dataset on the configured time grid.
3. Combine available providers according to the configured source-priority order.
4. Apply deterministic basic cleaning rules.
5. In `advanced` mode, determine which configured advanced rules are active for the current countries and time grid, acquire any required auxiliary demand data, construct or read advanced profiles, and apply them.
6. Evaluate any configured data-quality tests against the processed demand and available provider sources.
7. Finalise national demand together with cleaning provenance and data-quality diagnostics.
8. Download and prepare gridded population data.
9. Spatially disaggregate national demand using population weights and aggregate it to the user-provided target shapes.


## Configuration

The module is configured through `config/config.yaml`.

The key configuration groups are:

- `temporal_scope`: the target time grid;
- `load_sources`: demand providers and their priority;
- `gap_filling`: basic and advanced gap handling;
- `data_quality`: diagnostic tests applied to demand data.

Detailed configuration syntax, accepted values, provider metadata, validation rules, and examples are documented in the [configuration README](./config/README.md). See also the [example configuration](./config/config.yaml) and the authoritative [configuration schema](./workflow/internal/config.schema.yaml).

## Demand preparation and gap handling

National electricity-demand observations can be drawn from multiple providers and combined according to a configurable source priority on a regular user-defined time grid.

The module supports several levels of gap handling. Demand can be left unfilled, processed using deterministic basic cleaning rules, or handled with targeted advanced rules that can reconstruct or replace selected periods using auxiliary demand data or external profiles. Cleaning provenance is retained so that observed and reconstructed values remain distinguishable downstream.

See [Configuration: Temporal scope](./config/README.md#temporal-scope), [Demand sources](./config/README.md#demand-sources), and [Gap filling](./config/README.md#gap-filling) for detailed configuration and examples.

## Data-quality evaluation

After gap handling and before spatial disaggregation, the module can evaluate demand using configurable data-quality tests. These checks are diagnostic: they identify suspicious observations, profiles, source disagreements, and limitations in what could be evaluated, but they do **not** alter the processed demand series.

Data-quality methods and statistical semantics are provided by `tclean.data_quality`. The module supplies the electricity-demand-specific orchestration around those methods, including the processed demand and available provider data as evaluation sources, configuration validation, persistence of failures and issues, and diagnostic plotting.

See [Configuration: Data quality](./config/README.md#data-quality) for the module-facing configuration contract. Method-level threshold and reference semantics are documented in tclean's `docs/data_quality.md`.

## Provenance and diagnostics

The workflow retains cleaning provenance alongside national demand so observed values can be distinguished from values introduced by basic or advanced rules.

Important diagnostic outputs include:

- **Gap report**: unresolved contiguous gaps remaining after basic cleaning, which can be used to identify periods that need targeted advanced handling;
- **Cleaning method and rank**: the source or rule responsible for each output value and its provenance ordering;
- **Cleaning timeline and summary**: visual and tabular diagnostics showing demand provenance and completeness through the raw, basic, and advanced cleaning stages;
- **Data-quality failures and issues**: structured records of detected problems and limitations in evaluation;
- **Data-quality diagnostic plot**: a visual summary of configured failures on the processed demand.

Together, these diagnostics are intended to make gap handling and data quality explicit rather than conceal unresolved or reconstructed data. A typical advanced workflow is therefore to run the basic cleaning stage, inspect the remaining gaps and diagnostics, and then configure targeted advanced rules where explicit reconstruction or replacement is appropriate.

## Input / output structure

The primary user input is the set of target shapes to which national demand is spatially disaggregated. Depending on the selected demand sources and advanced cleaning configuration, the workflow may also require provider credentials or user-supplied external profiles.

Intermediate provider data, cleaned national demand, provenance, execution plans, auxiliary data, and data-quality diagnostics are stored below the module resources path. Final regional electricity demand is written to the configured module results path.

Please consult [`INTERFACE.yaml`](./INTERFACE.yaml) for the module's formal input/output interface.

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
- `test`: used for unit testing. It combines the `module` environment with test-only dependencies such as `pytest`.
- `module`: contains minimal dependencies used in `Snakemake` rules.
If modified, be sure to export it to `Snakemake` so it can be recreated by module users:

```shell
# create module.yaml and conda-spec pin files in workflow/envs/
pixi run export-snakemake-env module
```

### Adding a demand source

Demand-provider metadata is registered centrally in [`workflow/internal/source_registry.yaml`](./workflow/internal/source_registry.yaml), while provider-specific workflow behaviour lives in a matching `workflow/rules/source_<source>.smk` file.

A new provider normally requires:

1. Add the source identifier and metadata to `workflow/internal/source_registry.yaml`. `display_name` gives the human-readable label; optional `temporal_scope` uses the module-wide half-open convention `[start, end)`; optional `contexts` restricts the source to listed country contexts.
2. Add `workflow/rules/source_<source>.smk` containing the provider-specific acquisition, main preparation, and auxiliary preparation rules and helpers that are required.
3. Add the provider implementation under `workflow/scripts/sources/<source>/` together with any thin Snakemake wrapper scripts needed by the rules.
4. Include the new source rule file directly from `workflow/Snakefile`.
5. Add credentials or other user-facing inputs to `INTERFACE.yaml` only when the provider requires them.
6. Add tests covering the provider and, where applicable, both main-period and advanced auxiliary acquisition.

Prepared national-demand outputs follow the `load_<source>.parquet` naming convention. Generic source validation, display names, and tlean source capabilities are derived from the registry where applicable, so adding a provider should not require separate source-name mappings in those parts of the workflow.

Provider-specific behaviour should remain explicit rather than being encoded as generic registry metadata: APIs, raw cache layouts, download resources, preparation logic, and auxiliary-file resolution belong in the provider implementation and its source rule file.

## Testing
<!-- Please do not modify this templated section -->

For testing, simply run:

```shell
pixi run test-unit
pixi run test-integration
```

To test a minimal example of a workflow using this module:

```shell
pixi shell    # activate this project's environment
cd tests/integration/  # navigate to the integration example
snakemake  # run the workflow!
```

The integration workflow's default Snakemake profile enables Conda, uses 2 cores, and limits concurrent ENTSO-E downloads (including Transparency Platform and Power Statistics acquisition) and NESO downloads to 2 each. These execution settings can be overridden with the corresponding Snakemake command-line options:

- **Cores**: Defaults can be overridden using the `--cores` flag.
- **ENTSO-E downloads**: Override with `--resources entsoe_download=<n>`.
- **NESO downloads**: Override with `--resources neso_download=<n>`.

A complete example:

```shell
snakemake --cores 4 --resources entsoe_download=1 neso_download=1
```


## References
<!-- Please provide thorough referencing below -->

This module is based on the following research and datasets:

* ENTSOE Transparency Platform (https://transparency.entsoe.eu)
* ENTSO-E Power Statistics (https://www.entsoe.eu/data/power-stats/)
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
