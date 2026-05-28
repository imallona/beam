# 0009 - Mixed-effects heterogeneity via a one-shot R subprocess

- Status: Accepted
- Date: 2026-05-25
- Deciders: Izaskun Mallona
- Supersedes: -
- Superseded by: -

## Context

beam uses a mixed-effects model on benchmark scores (Eugster, Hothorn, Leisch 2008) to split the global method effect from the method-by-dataset interaction. The mature engines are in R: lme4 and glmmTMB. [ADR 0002](0002-python-first.md) already chose Python-first with R called from Python; what was open is reticulate or subprocess.

## Decision

Wrap lme4 in a one-shot R subprocess. `beam.heterogeneity.mixed_effects` serialises the long-format scores to JSON, runs `src/beam/heterogeneity/mixed_effects.R`, and parses the JSON reply. The default model is `score ~ method + (1 | dataset)`. With replicates in a cell it adds `(1 | dataset:method)`. R is found on PATH (overridable with `BEAM_RSCRIPT`) and provisioned by the conda environment `envs/heterogeneity.yml`.

## Consequences

- The R dependency is optional and discovered at runtime through `r_available()`. beam installs and imports without R; only this call needs it. A CI job builds the conda environment and runs the tests; the Python test job skips them.
- The contract is JSON over a process boundary. A failed fit is an exit code and a stderr message, with no shared-interpreter state to manage. The cost is process start-up per call, which is negligible here.
- With one run per cell the interaction is confounded with noise, so the residual is their sum and the report names it as the upper bound on the interaction. Separating it needs a multi-run benchmark.
- lme4 is Gaussian. On a bounded metric this is an approximation; a glmmTMB beta family is the documented extension and is not built yet.

## Alternatives considered

- reticulate: couples the Python process to a built R at import time for no benefit at these data sizes. Swappable later without changing the API.
- statsmodels MixedLM: less complete for crossed random effects, a heavy dependency, and off the lme4 and glmmTMB path the rest of the heterogeneity module uses.

## References

- [Mixed-effects explanation](../explanations/heterogeneity-mixed-effects.md)
- [ADR 0002 (python-first)](0002-python-first.md), [ADR 0003 (bradley-terry-not-irt)](0003-bradley-terry-not-irt.md)
- Eugster, Hothorn, Leisch (2008): https://epub.ub.uni-muenchen.de/11425/
- lme4: https://cran.r-project.org/package=lme4 ; glmmTMB: https://cran.r-project.org/package=glmmTMB
