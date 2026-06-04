# Use beam from R

beam ships an R package (rbeam) alongside the Python one. The MCDA wrappers forward to the Python implementation through reticulate, so R users get the same metric cards, pipeline and sensitivity primitives. The heterogeneity diagnostics are implemented natively in R (lme4, psychotree, glmmTMB, PlackettLuce).

This recipe goes from install to a first run.

## 1. Install the R package

While beam is pre-CRAN, clone the repository and install the R package from the checkout:

```sh
git clone https://github.com/imallona/beam.git
cd beam
```

```r
devtools::install_local("r/beam")
```

This installs the wrapper and its required dependencies. It does not install the heterogeneity Suggests; see section 5 for those. Avoid `dependencies = TRUE` here: it tries to source-compile every Suggests, and `PlackettLuce` pulls in `CVXR` and `clarabel` (the latter needs a Rust toolchain), which fails on machines without those build tools.

After the CRAN release:

```r
install.packages("rbeam")
```

The R package declares `SystemRequirements: Python (>= 3.12)`. R will not install Python for you.

## 2. Install the Python side

Once, after installing the R package:

```r
library(rbeam)
install_beam_python()
```

This calls `reticulate::py_install("beam")` and puts the Python package into the active reticulate environment. If you already have a Python environment with beam in it, point reticulate at it instead:

```r
reticulate::use_python("/path/to/python", required = TRUE)
# or set RETICULATE_PYTHON before loading the package
```

## 3. Rank a benchmark and write a report

```r
library(rbeam)
result <- beam_rank("scores.csv", weights = "entropy", method = "topsis")
beam_report(result, "report.html")
print(result$top_tool)
```

The CSV is the same wide format the Python side reads: first column the tool, one column per metric id. Every metric id resolves to a card in the bundled registry.

For the funky-heatmap figure (the glyph table plus beam's rank-robustness panels) drawn straight from the result:

```r
beam_funky_heatmap(result, "funky.png")
```

With no `path` it returns the matplotlib figure object instead of saving. This forwards to the Python `beam.funky_heatmap_from_run`.

## 4. Reach into the result

`result` is the Python `RunResult` object. Use `$` to access fields:

```r
result$top_tool          # character: the tool ranked first
result$tool_names        # the tools, in input order
result$result$ranks      # integer ranks aligned with result$tool_names
result$smaa              # SMAA sensitivity report (NULL when sensitivity = FALSE)
result$manifest          # named list, write to JSON for reproducibility
```

The fields and their types match the Python `RunResult`. See `?beam_rank` for the wrapper signature and `?beam_report` for the report function.

## 5. Heterogeneity diagnostics

The four heterogeneity entry points live under their own R wrappers:

```r
beam_mixed_effects(scores, method_names = m, dataset_names = d, metric = "ari")
beam_bradley_terry_tree(scores, method_names = m, dataset_names = d, features = f)
beam_plackett_luce(scores, method_names = m)
beam_source_variance_decomposition(methods, datasets, benchmarks, scores)
```

These run natively in R using lme4, psychotree, glmmTMB and PlackettLuce, with no Python involved. Each needs only its own package (a Suggests) installed. Install them once with the bundled helper:

```r
rbeam::install_beam_heterogeneity_deps()
```

`PlackettLuce` depends on `CVXR` and `clarabel`, which are slow or impossible to compile from source without a Rust toolchain. If a source build fails, install a prebuilt binary instead (Posit Package Manager and r-universe ship binaries for the common platforms), or use the conda recipe [envs/heterogeneity.yml](https://github.com/imallona/beam/blob/main/envs/heterogeneity.yml), which pulls every R package as a conda-forge binary.

## 6. Inspect a metric card

```r
beam_metric_show("ari")
```

prints the polarity, scale type, range, allowed transformations and ontology mappings of the card from the registry. Useful when adding a new metric to a benchmark to confirm beam reads it as you expect.

## 7. Validate before ranking

```r
beam_validate("scores.csv", method = "topsis")
```

checks that every metric id resolves to a card and that the scale types are compatible with the aggregation method you intend to use. Cleaner than running `beam_rank` and discovering a missing card halfway through.

## 8. Worked examples (vignettes)

The package ships four self-contained vignettes, each with its own figures. The rendered versions are published on the documentation site:

- [Ranking methods and checking the ranking](https://imallona.github.io/beam/r-vignettes/ranking.html): rank the Duo 2018 benchmark, then check the ranking with SMAA, leave-one-dataset-out, the smallest weight perturbation, aggregation agreement, the card reference levels, and the Friedman-Nemenyi critical-difference test.
- [Metric-set diagnostics](https://imallona.github.io/beam/r-vignettes/metric-diagnostics.html): convergent and discriminant validity, internal-consistency reliability, and dimensionality of a metric group, on the OpenProblems scIB metrics.
- [Method-by-dataset heterogeneity](https://imallona.github.io/beam/r-vignettes/heterogeneity.html): the mixed-effects variance decomposition, the Bradley-Terry tree, and the Plackett-Luce model on the Duo ARI matrix.
- [Cross-benchmark meta-analysis](https://imallona.github.io/beam/r-vignettes/cross-benchmark.html): the consensus bump plot, per-benchmark funky heatmaps, the network meta-analysis, the variance decomposition, and the same-data pancreas contrast.

Once the package is installed, the same vignettes open locally with `browseVignettes("rbeam")`, or one at a time:

```r
vignette("ranking", package = "rbeam")
vignette("metric-diagnostics", package = "rbeam")
vignette("heterogeneity", package = "rbeam")
vignette("cross-benchmark", package = "rbeam")
```

## Where to go next

- The Python and R sides share metric cards and the conceptual essays, which apply to both languages: see [measurement theory](../explanations/measurement-theory.md) and [cards and pipeline](../explanations/cards-and-pipeline.qmd).
- The R wrapper's source is under `r/beam/` in the main repo. Each R function file is short: read `r/beam/R/rank.R` for the simplest example of how the wrappers forward arguments.
