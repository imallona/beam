# 0011 - glmmTMB beta engine and Plackett-Luce via R subprocesses

- Status: Accepted
- Date: 2026-05-26
- Deciders: Izaskun Mallona
- Supersedes: -
- Superseded by: -

## Context

Two model extensions remained after the mixed-effects (lme4) and Bradley-Terry (psychotree) work: glmmTMB for bounded and non-Gaussian benchmark metrics, and Plackett-Luce for full-ranking inputs. [ADR 0009](0009-heterogeneity-mixed-effects-via-r.md) already settled the boundary between Python and R, a one-shot R subprocess rather than reticulate. This ADR records the two additions and their design choices. Both reuse the shared subprocess machinery in `beam.heterogeneity._rsubprocess`.

## Decision

### glmmTMB as an engine of mixed_effects

glmmTMB is an engine of the existing `mixed_effects`, not a new function. `mixed_effects` gained an `engine` parameter ("lmer" by default, or "glmmtmb") and a `family` parameter ("beta", "gaussian", or None). With `engine="glmmtmb"` and `family="beta"` it fits the same `score ~ method + (1 | dataset)` structure in glmmTMB with a beta family, for a metric bounded in (0, 1) such as a scIB-scaled score. Scores exactly at 0 or 1 are squeezed inside the open interval with the Smithson-Verkuilen transform before the fit.

The marginal means and the variance components are then on the model link (logit) scale. The report's `scale` field records this as "link", against "response" for the Gaussian fits. The beta fit reports a dispersion term in place of a Gaussian residual. Auto family resolution picks beta only when every score lies strictly in (0, 1), and gaussian otherwise, so an unbounded metric such as raw ARI in [-1, 1] stays Gaussian. The same `MixedEffectsReport` is reused. The call is gated by `glmmtmb_available`.

### Plackett-Luce as a new module

Plackett-Luce is a new module `beam.heterogeneity.plackett_luce` wrapping R's PlackettLuce. It takes a method by dataset score matrix, turns each dataset column into a dense ranking of the methods oriented by the metric polarity (ties shared, methods missing from a column left out of that ranking), and fits PlackettLuce. It returns the worth parameters (summing to one), the log-worth, the quasi-standard-errors from qvcalc, and fit statistics. Paired rankings reduce to Bradley-Terry, so Plackett-Luce is the generalization of the Bradley-Terry strengths to full orderings.

Worths are read from `coef` rather than `itempar`. `itempar` and `qvcalc` refit through the model's Poisson form, which fails on rankings that mix ties with partial coverage. `coef` is the stable path and gives the same unit-sum worth after normalization. The quasi-standard-errors are best-effort: they are NA with a warning when that refit fails. The call is gated by `plackett_luce_available` (PlackettLuce and qvcalc).

## Consequences

- r-glmmtmb, r-plackettluce and r-qvcalc join `envs/heterogeneity.yml`, and the conda CI job runs all three heterogeneity test files.
- Installation note: on R 4.3 the current PlackettLuce cannot be installed from CRAN because its CVXR dependency requires Matrix >= 1.7, which needs R >= 4.4. The conda-forge build (R 4.5) installs cleanly, so validation uses a conda environment.
- Validated on Duo 2018 ARI. The glmmTMB Gaussian fit reproduces the lme4 result. The beta fit, on the scIB-scaled OpenProblems ARI which lies in [0, 1], keeps the leading methods while the lower ordering differs near the bounds. The Plackett-Luce worth ranks SC3 first, matching the Bradley-Terry global ranking and the mixed-effects marginal means.

## Alternatives considered

- A separate glmmTMB function. Rejected: it is the same model with a different likelihood, so an engine switch is cleaner than a parallel function.
- `itempar` and `qvcalc` for the worth. Rejected as the primary path because they fail on ties with partial rankings; kept as the best-effort source of the quasi-standard-errors.
- IRT and Rasch models. Already parked in [ADR 0003](0003-bradley-terry-not-irt.md).

## References

- [Full rankings and bounded metrics explanation](../explanations/full-rankings-and-bounded-metrics.md)
- [ADR 0009 (mixed-effects via R)](0009-heterogeneity-mixed-effects-via-r.md), [ADR 0010 (bradley-terry-trees)](0010-bradley-terry-trees.md)
- Brooks ME, Kristensen K, van Benthem KJ, Magnusson A, Berg CW, Nielsen A, Skaug HJ, Maechler M, Bolker BM. glmmTMB balances speed and flexibility among packages for zero-inflated generalized linear mixed models. The R Journal 2017. DOI 10.32614/RJ-2017-066.
- Turner HL, van Etten J, Firth D, Kosmidis I. Modelling rankings in R: the PlackettLuce package. Computational Statistics 2020, 35:1027-1057. DOI 10.1007/s00180-020-00959-3.
- Smithson M, Verkuilen J. A better lemon squeezer? Maximum-likelihood regression with beta-distributed dependent variables. Psychological Methods 2006. DOI 10.1037/1082-989X.11.1.54. Used for the beta squeeze.
