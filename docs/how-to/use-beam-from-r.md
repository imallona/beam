# Use beam from R

beam ships an R package alongside the Python one. The R package is a thin reticulate wrapper: every R function forwards to the Python implementation. So R users get the same metric cards, the same MCDA pipeline, the same sensitivity primitives, and the same heterogeneity diagnostics, called from R syntax.

This recipe goes from install to a first run.

## 1. Install the R package

While beam is pre-CRAN, install from the repo checkout:

```r
devtools::install_local("r/beam", dependencies = TRUE)
```

After the CRAN release:

```r
install.packages("beam")
```

The R package declares `SystemRequirements: Python (>= 3.12)`. R will not install Python for you.

## 2. Install the Python side

Once, after installing the R package:

```r
library(beam)
install_beam_python()
```

This calls `reticulate::py_install("beam")` and puts the Python package into the active reticulate environment. If you already have a Python environment with beam in it, point reticulate at it instead:

```r
reticulate::use_python("/path/to/python", required = TRUE)
# or set RETICULATE_PYTHON before loading the package
```

## 3. Rank a benchmark and write a report

```r
library(beam)
result <- beam_rank("scores.csv", weights = "entropy", method = "topsis")
beam_report(result, "report.html")
print(result$top_tool)
```

The CSV is the same wide format the Python side reads: first column the tool, one column per metric id. Every metric id resolves to a card in the bundled registry.

## 4. Reach into the result

`result` is the Python `RunResult` object. Use `$` to access fields:

```r
result$top_tool          # character: the tool ranked first
result$ranking           # integer vector aligned with result$tool_names
result$smaa$confidence   # SMAA confidence factor per tool
result$leave_one_metric_out$rank_stability
result$manifest          # named list, write to JSON for reproducibility
```

The fields and their types match the Python `RunResult`. See `?beam_rank` for the wrapper signature and `?beam_report` for the report function.

## 5. Heterogeneity diagnostics

The four heterogeneity entry points live under their own R wrappers:

```r
beam_mixed_effects(scores, method_names = m, dataset_names = d, metric = "ari")
beam_bradley_terry_tree(scores, method_names = m, dataset_names = d, features = f)
beam_plackett_luce(scores, method_names = m, dataset_names = d)
beam_source_variance_decomposition(methods, datasets, benchmarks, scores)
```

Each forwards to a Python function that drives an R subprocess (lme4, psychotree, PlackettLuce). So an R caller goes R, then reticulate, then Python, then a one-shot Rscript, then the upstream R package. The user does not see the indirection; it keeps a single source of truth for the heterogeneity code.

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

## Where to go next

- The R package's own quick start lives in `vignette("duo2018", package = "beam")`.
- The Python and R sides share metric cards and explanations. The conceptual essays under [explanations](../explanations/) apply to both languages.
- The R wrapper's source is under `r/beam/` in the main repo. Each R function file is short: read `r/beam/R/rank.R` for the simplest example of how the wrappers forward arguments.
