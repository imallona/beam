# Full rankings and bounded metrics

The mixed-effects model and the Bradley-Terry tree both start from a method by dataset score matrix and read it as pairwise comparisons. Two further models in `beam.heterogeneity` take different views of the same matrix: Plackett-Luce reads each dataset as a full ranking of the methods, and the glmmTMB beta engine models a metric bounded in (0, 1) without the Gaussian approximation.

## The Plackett-Luce model

When each dataset gives a full ranking of the methods, not just pairwise wins, Plackett-Luce turns those orderings into one worth per method, with the worths summing to one. It generalizes the Bradley-Terry strengths from pairwise comparisons to full orderings, and it reduces to Bradley-Terry when the data are pairwise.

`beam.heterogeneity.plackett_luce` builds the per-dataset dense ranking from the score matrix, oriented by the metric polarity so a lower-is-better metric needs no manual flipping. Ties are shared and any method missing from a column is dropped from that dataset's ranking. The report carries the worth, the log-worth, and the quasi-standard-errors. The quasi-standard-errors are reference-free, so any two methods compare without picking a baseline. The report also says whether the ranking network is connected, which is the condition for the worths to be jointly identified.

There is an honest limit. On rankings that mix ties with partial coverage, the quasi-standard-errors can be unavailable, because the variance refit fails on that shape. When that happens the worths are still reported and the standard-error fields are NA with a warning.

Plackett-Luce and the Bradley-Terry tree answer different questions. Plackett-Luce gives one global ranking with uncertainty across all datasets. The tree localizes where that ranking reverses, splitting the datasets by their features. Use Plackett-Luce when the input is a per-dataset ordering and the question is the overall order; use the tree when the question is which dataset features change the order.

## The glmmTMB beta engine

The lme4 mixed-effects model assumes a Gaussian residual. That is an approximation for a metric bounded in (0, 1), and it is worst near the bounds, where the Gaussian tail runs past 0 or 1 but the metric cannot. The glmmTMB beta engine models the bound directly with a beta likelihood.

Call `mixed_effects(engine="glmmtmb", family="beta")`. It fits the same `score ~ method + (1 | dataset)` structure with a beta likelihood. The marginal means and the variance components come back on the link (logit) scale, and the report's `scale` field says "link". The variance components are not directly comparable to the Gaussian-scale lme4 numbers, but the method ordering is comparable across the two fits. Auto family resolution picks beta only for scores strictly in (0, 1), so an unbounded metric stays Gaussian.

## How to use them

Both need the R toolchain. Check `plackett_luce_available()` and `glmmtmb_available()` before calling. The conda environment [envs/heterogeneity.yml](https://github.com/imallona/beam/blob/main/envs/heterogeneity.yml) provides PlackettLuce, qvcalc and glmmTMB.

## Relation to the rest

With these two models the heterogeneity model set is complete: the mixed-effects variance decomposition, the Bradley-Terry trees, the glmmTMB beta engine, and Plackett-Luce.
