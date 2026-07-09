# Method-by-dataset heterogeneity

A pooled [MCDA](aggregation-methods.md) ranking treats the datasets as interchangeable and reports one order of the methods. The heterogeneity question is whether that order is stable across datasets or an average over datasets that disagree. beam has four models in `beam.heterogeneity`, each reading one metric's method by dataset score matrix, all fitting in R:

- the mixed-effects variance decomposition: how much of the score variation is a method-by-dataset interaction;
- the Bradley-Terry tree: which dataset features produce that interaction, and the ranking inside each subgroup;
- Plackett-Luce: one global ranking with uncertainty when each dataset gives a full ordering;
- the glmmTMB beta engine: the mixed-effects decomposition for a metric bounded in (0, 1).

## Mixed-effects variance decomposition

[`beam.heterogeneity.mixed_effects`](../reference/mixed_effects.qmd) follows Eugster, Hothorn and Leisch (2008). For one metric, every benchmark score is one observation labelled by its method and its dataset. The model is

    score ~ method + (1 | dataset)

The method is a fixed effect: each method gets a marginal mean over datasets, with a standard error. The dataset is a random intercept: it absorbs the fact that some datasets are easy and some are hard, a shift that moves every method together. What is left after the method effect and the dataset shift is the residual.

The variance splits into two parts: the dataset variance and the residual variance. The intraclass correlation, the dataset variance over the total, is the share of the spread that is a pure dataset shift. A high value means the datasets differ mostly in difficulty, not in which method they favour. A low value means most of the variation is within datasets, where the method-by-dataset interaction occurs.

A single global ranking is safe when the interaction is small: the method that leads on average leads nearly everywhere. When the interaction is large, the average hides reversals, and an appropriate split is "use method A on data like this, method B on data like that". This is the Strobl critique, that one method does not fit all datasets, written as a variance component.

With one run per (method, dataset) cell, the usual single-run benchmark, the interaction cannot be separated from measurement noise. There is one number per cell and two things to explain it with, so they are confounded; the residual is their sum. beam reports the residual share as the upper bound on the interaction and says so. To split them you need replicates, several runs of the same method on the same dataset. When the input has them, the auto path fits

    score ~ method + (1 | dataset) + (1 | dataset:method)

and reports the interaction as its own component, so `interaction_share` is defined instead of `None`.

The per-cell residuals are the local signal. A large residual is a cell where a method does much better or worse than its global effect predicts on that dataset. `top_outliers` returns the largest ones. They point to where the interaction sits, which methods on which datasets, even when its size cannot be separated from noise.

Call `mixed_effects(methods, datasets, scores)` with three parallel sequences for one metric, or `mixed_effects_from_matrix(matrix, method_names, dataset_names)` with a method by dataset matrix. NaN scores are dropped. The report carries the method marginal means and their standard errors, the variance components, the dataset ICC, the interaction or residual share, the residuals, and the outlier cells.

## Bradley-Terry trees

The mixed-effects model measures how much interaction there is. The Bradley-Terry tree in [`beam.heterogeneity.bradley_terry_tree`](../reference/bradley_terry_tree.qmd) asks which dataset properties produce it, and what the ranking is inside each subgroup. It follows Strobl, Wickelmaier and Zeileis, who combine a Bradley-Terry model with model-based recursive partitioning.

For one metric, each dataset gives a ranking of the methods. The tree works with the pairwise form: for every method pair, the dataset records which method scored higher (a win for one, a loss for the other), a tie on an exact equality, or a missing comparison where a method has no score there. The metric polarity orients the comparison, so a lower-is-better metric needs no manual flipping. [`beam.heterogeneity.paired_comparisons`](../reference/paired_comparisons.qmd) builds this design from a method by dataset matrix; it is pure Python and is the part you can inspect without R. The datasets are the subjects of the model and the methods are the objects being compared, reversed from the usual reading because the tree splits on properties of the datasets.

A Bradley-Terry model turns pairwise wins into a latent strength per method, the worth, with the worths summing to one. Fit on all datasets at once, it gives a single ranking, the `global_worth` in the report. Model-based recursive partitioning fits the model at the root, then tests whether the worth parameters are stable across the candidate dataset features. When the stability test flags a feature, the datasets split on it and the model is refit in each child. The recursion continues until no further split is warranted or a node would fall below the minimum size. The result is a tree whose leaves each carry their own Bradley-Terry ranking, with inner nodes that read as "datasets with feature X above threshold Z go this way". Instead of one ranking averaged over datasets that may disagree, the tree gives "prefer method A on datasets like this, method B on datasets like that", with a statistical test deciding where the split is real. `reversed_leaves` reports the leaves whose strongest method differs from the global one.

Recursive partitioning needs enough datasets to support a split. With a dozen datasets the parameter-stability test rarely separates a feature-dependent regime from sampling noise, and the tree reduces to the single flat ranking. The report says so through `did_split` and the summary, rather than inventing a split. This is the same limit the critical-difference diagram and the mixed-effects fit hit on a small benchmark.

Call `bradley_terry_tree(matrix, method_names, dataset_names, numeric_features=, categorical_features=, polarity=)`. The features are per-dataset descriptors, numeric ones as continuous splitters and categorical ones as factors; pass at least one. `minsize` sets the smallest leaf and `alpha` the split test level. The report carries the tree nodes (split variables, breakpoints, parameter-stability p-values), the per-leaf worths with standard errors, the leaf assignment per dataset, the global flat ranking, and a plain-language summary. `node_ranking`, `datasets_in_node` and `reversed_leaves` read the leaves.

## Plackett-Luce: full rankings

When each dataset gives a full ranking of the methods, not just pairwise wins, Plackett-Luce turns those orderings into one worth per method, with the worths summing to one. It generalizes the Bradley-Terry strengths from pairwise comparisons to full orderings, and reduces to Bradley-Terry when the data are pairwise.

[`beam.heterogeneity.plackett_luce`](../reference/plackett_luce.qmd) builds the per-dataset dense ranking from the score matrix, oriented by the metric polarity so a lower-is-better metric is reversed. Ties are shared and any method missing from a column is dropped from that dataset's ranking. The report carries the worth, the log-worth, and the quasi-standard-errors. The quasi-standard-errors are reference-free, so any two methods compare without picking a baseline. The report also says whether the ranking network is connected, the condition for the worths to be jointly identified. In rankings that mix ties with partial coverage the quasi-standard-errors can be unavailable, because the variance refit fails on that shape; the worths are still reported and the standard-error fields are NA with a warning.

Plackett-Luce and the Bradley-Terry tree answer different questions. Plackett-Luce gives one global ranking with uncertainty across all datasets; the tree locates where that ranking reverses. Use Plackett-Luce when the input is a per-dataset ordering and the question is the overall order, and the tree when the question is which dataset features change the order.

## glmmTMB beta: bounded metrics

The lme4 mixed-effects model assumes a Gaussian residual. That is an approximation for a metric bounded in (0, 1), and it is worst near the bounds, where the Gaussian tail runs past 0 or 1 but the metric cannot. The glmmTMB beta engine models the bound directly with a beta likelihood.

Call `mixed_effects(engine="glmmtmb", family="beta")`. It fits the same `score ~ method + (1 | dataset)` structure with a beta likelihood. The marginal means and the variance components come back on the link (logit) scale, and the report's `scale` field says "link". The variance components are not directly comparable to the Gaussian-scale lme4 numbers, but the method ordering is comparable across the two fits. Auto family resolution picks beta only for scores strictly in (0, 1), so an unbounded metric stays Gaussian.

## R dependency

All four models fit in R through a subprocess, so they need the R toolchain. lme4 backs the Gaussian mixed-effects fit, psychotree and partykit the Bradley-Terry tree, PlackettLuce and qvcalc the Plackett-Luce worths, and glmmTMB the beta engine. Check the matching availability function before calling: `r_available()`, `bttree_available()`, `plackett_luce_available()`, `glmmtmb_available()`. The conda environment [envs/heterogeneity.yml](https://github.com/imallona/beam/blob/main/envs/heterogeneity.yml) provides all of them.

## Relation to the other checks

These models split the raw metric across datasets. Two composite-level checks sit next to them. Leave-one-dataset-out ([`beam.mcda.leave_one_dataset_out`](../reference/leave_one_dataset_out.qmd)) re-ranks with each dataset removed and asks whether the recommendation depends on any single dataset; a stable result with a low interaction share is a ranking you can trust across the datasets at hand. Whether the methods are statistically separable on a metric is the [Friedman-Nemenyi check](critical-difference.md).

The [Duo 2018 vignette](../../examples/duo2018/duo2018.qmd) works these through on the Adjusted Rand Index (ARI) scores, where the tree degrades to a flat ranking on 12 datasets.

## References

- Eugster, M. J. A., Hothorn, T., Leisch, F. (Psycho-)analysis of benchmark experiments. Technical Report 30, Department of Statistics, LMU Munich (2008).
- Strobl, C., Wickelmaier, F., Zeileis, A. Accounting for individual differences in Bradley-Terry models by means of recursive partitioning. Journal of Educational and Behavioral Statistics (2011). DOI [10.3102/1076998609359791](https://doi.org/10.3102/1076998609359791).
