# rbeam: R interface to beam

R interface to the [beam](https://github.com/imallona/beam) Python package. The MCDA wrappers (`beam_rank`, `beam_report`, `beam_validate`, `beam_run`, `beam_metric_show`) forward to Python through `reticulate`. The heterogeneity diagnostics (mixed-effects, Bradley-Terry trees, Plackett-Luce, cross-benchmark variance decomposition) are implemented natively in R.

For the MCDA pipeline, the metric cards and reporting, the canonical implementation is the Python package and the R side is a typed reticulate shim. The heterogeneity diagnostics are implemented natively in R.

## Install

Clone the repository first, then install from the checkout:

```sh
git clone https://github.com/imallona/beam.git
cd beam
```

```r
# Development install from the monorepo checkout:
devtools::install_local("r/beam")

# After CRAN release:
install.packages("rbeam")

# Then install the Python side once:
library(rbeam)
install_beam_python()
```

`install_beam_python()` installs the beam Python package into the active reticulate environment. If you already have a Python environment with beam installed, point `reticulate` at it with `reticulate::use_python()` or set `RETICULATE_PYTHON` instead.

The install above does not pull the heterogeneity Suggests. Install them once with:

```r
install_beam_heterogeneity_deps()
```

Avoid `dependencies = TRUE` on the development install: it tries to source-compile every Suggests, and `PlackettLuce` pulls in `CVXR` and `clarabel` (the latter needs a Rust toolchain), which fails without those build tools. Install a prebuilt binary instead (Posit Package Manager or r-universe), or use the conda recipe [envs/heterogeneity.yml](https://github.com/imallona/beam/blob/main/envs/heterogeneity.yml).

## Quick use

```r
library(rbeam)
result <- beam_rank("scores.csv", weights = "entropy", method = "topsis")
beam_report(result, "report.html")
print(result$top_tool)
```

## Python and R split

Every wrapper forwards arguments to a Python function and returns the Python object. Use `$` to access fields:

```r
result <- beam_rank("scores.csv")
result$top_tool        # character
result$tool_names      # the tools, input order
result$result$ranks    # integer ranks, aligned with tool_names
result$manifest        # named list (write to JSON if you want)
```

The heterogeneity entry points (`beam_mixed_effects`, `beam_bradley_terry_tree`, `beam_plackett_luce`, `beam_source_variance_decomposition`) run natively in R using lme4, glmmTMB, psychotree and PlackettLuce, with no Python involved. Those packages are Suggests, so each entry point needs only its own package installed and stops with a clear message otherwise.

## Plots

The figures are drawn natively in R with ggplot2 (and patchwork for the multi-panel ones), so they match the Python package's plots without calling matplotlib. `plot(result)` draws the funky heatmap for a run. `beam_plot(x, kind)` selects a figure and returns the ggplot object, or writes a file when a path is given:

```r
result <- beam_rank("scores.csv", sensitivity = TRUE)
plot(result)                                   # funky heatmap
beam_plot(result, "specification_curve", "curve.png")
beam_plot(mixed, "variance_components")
beam_plot(validity, "metric_correlation")
```

The kinds cover ranking and stability (`ranking`, `normalized_scores`, `smaa`, `dataset_stability`, `funky_heatmap`, `specification_curve`, `critical_difference`, `critical_difference_band`), the choice-effect bump charts (`weighting_effect`, `aggregation_effect`, `normalization_effect`, `dataset_effect`), the agreement and concordance heatmaps (`aggregation_agreement`, `normalization_agreement`, `dataset_concordance`, `dataset_struggle`, `pairwise_majority`, `bayesian_comparison`, `dataset_discrimination`, `difficulty_concordance`), the heterogeneity reports (`model_effects`, `variance_components`, `bradley_terry_leaves`, `network_forest`, `attribution_progression`), and the metric-quality reports (`metric_correlation`, `metric_reliability_dropped`, `metric_dimensionality_scree`). The full list is in `?beam_plot`.

## License

GPL (>= 3), matching the Python package.

## Citation

See the top-level repository `CITATION.cff`. Cite Mallona, Robinson and Soneson (2025) for the omnibenchmark ecosystem context.
