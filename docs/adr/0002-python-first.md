# 0002 - Python-first core, thin R wrapper

- Status: Accepted
- Date: 2025-03-01
- Deciders: Izaskun Mallona
- Supersedes: -
- Superseded by: -

## Context

The CRS proposal commits to an R package for CRAN or Bioconductor. The prior MCDA work in this repo is a Python notebook on pymcdm. omnibenchmark is Python and Snakemake. The Phase 4 heterogeneity diagnostics (psychotree, lme4, glmmTMB) are R-only.

## Decision

Python is the canonical implementation. R-only methods run via reticulate or subprocess. A thin R wrapper covers the CRAN or Bioconductor submission.

## Consequences

- Reuse the existing notebook code.
- One canonical test suite, in Python.
- R users install Python (or use reticulate's bundled one).
- Subprocess calls to R add latency and a hard R dependency for the heterogeneity module.

## Alternatives considered

- R-first: would force a rewrite of the notebook and cut beam off from omnibenchmark.
- Two parallel implementations: doubles maintenance, drifts.
- Pure R: pymcdm has no R equivalent.

## References

- https://github.com/Valdecy/pymcdm
- https://rstudio.github.io/reticulate/
- https://omnibenchmark.org
