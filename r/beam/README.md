# beam: R interface

Thin R interface to the [beam](https://github.com/imallona/beam) Python package via `reticulate`. Mirrors the Python entry points (`beam.rank`, `beam.report`, `beam.validate`, `beam.run`, `beam.metric.show`) plus the heterogeneity diagnostics (mixed-effects, Bradley-Terry trees, Plackett-Luce, cross-benchmark variance decomposition).

The R package does not reimplement the science. The canonical implementation is the Python package; the R side is a typed shim plus roxygen docs.

## Install

```r
# From the monorepo (development install):
devtools::install_local("r/beam", dependencies = TRUE)

# After CRAN release:
install.packages("beam")

# Then install the Python side once:
library(beam)
install_beam_python()
```

`install_beam_python()` installs the beam Python package into the active reticulate environment. If you already have a Python environment with beam installed, point `reticulate` at it with `reticulate::use_python()` or set `RETICULATE_PYTHON` instead.

## Quick use

```r
library(beam)
result <- beam_rank("scores.csv", weights = "entropy", method = "topsis")
beam_report(result, "report.html")
print(result$top_tool)
```

## What runs where

Every wrapper forwards arguments to a Python function and returns the Python object. Use `$` to access fields:

```r
result <- beam_rank("scores.csv")
result$top_tool        # character
result$ranking         # integer vector
result$smaa$confidence # named numeric
result$manifest        # named list (write to JSON if you want)
```

The heterogeneity entry points (`beam_mixed_effects`, `beam_bradley_terry_tree`, `beam_plackett_luce`, `beam_source_variance_decomposition`) drive R packages (lme4, glmmTMB, psychotree, PlackettLuce) through one-shot subprocesses on the Python side. So an R caller goes R -> reticulate -> Python -> Rscript subprocess -> the upstream R package. It is indirect, but it keeps a single source of truth for the heterogeneity code and lets R users call the same entry points the Python users do.

## License

GPL (>= 3), matching the Python package.

## Citation

See the top-level repository `CITATION.cff`. Cite Mallona, Robinson and Soneson (2025) for the omnibenchmark ecosystem context.
