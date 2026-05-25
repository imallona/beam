# Heterogeneity: the mixed-effects variance decomposition

A pooled MCDA ranking treats the datasets as interchangeable and reports one order of the methods. The heterogeneity question is whether that order is stable across datasets or an average over datasets that disagree. The mixed-effects model in `beam.heterogeneity.mixed_effects` answers it for one metric, following Eugster, Hothorn and Leisch (2008).

## The model

For one metric, every benchmark score is one observation labelled by its method and its dataset. The model is

    score ~ method + (1 | dataset)

The method is a fixed effect: each method gets a marginal mean over datasets, with a standard error. The dataset is a random intercept: it absorbs the fact that some datasets are easy and some are hard, a shift that moves every method together. What is left after the method effect and the dataset shift is the residual.

The variance splits into two parts: the dataset variance and the residual variance. The intraclass correlation, the dataset variance over the total, is the share of the spread that is a pure dataset shift. A high value means the datasets differ mostly in difficulty, not in which method they favour. A low value means most of the variation is within datasets, where the method-by-dataset interaction lives.

## Why the interaction is the point

A single global ranking is safe when the interaction is small: the method that leads on average leads nearly everywhere. When the interaction is large, the average hides reversals, and the better answer is "use method A on data like this, method B on data like that". This is the Strobl critique, that one method does not fit all datasets, stated as a variance component.

## The identifiability limit

With one run per (method, dataset) cell, the usual single-run benchmark, the interaction cannot be separated from measurement noise. There is one number per cell and two things to explain it with, so they are confounded; the residual is their sum. beam reports the residual share as the upper bound on the interaction and says so. To split them you need replicates, several runs of the same method on the same dataset. When the input has them, the auto path fits

    score ~ method + (1 | dataset) + (1 | dataset:method)

and reports the interaction as its own component, so `interaction_share` is defined instead of `None`.

## Reading the residuals

The per-cell residuals are the local signal. A large residual is a cell where a method does much better or worse than its global effect predicts on that dataset. `top_outliers` returns the largest ones. They point to where the interaction sits, which methods on which datasets, even when its size cannot be separated from noise.

## How to use it

Call `mixed_effects(methods, datasets, scores)` with three parallel sequences for one metric, or `mixed_effects_from_matrix(matrix, method_names, dataset_names)` with a method by dataset matrix. NaN scores are dropped. The report carries the method marginal means and their standard errors, the variance components, the dataset ICC, the interaction or residual share, the residuals, and the outlier cells.

The fit runs in R's lme4 through a subprocess, so it needs the R toolchain. Check `r_available()` first; the conda environment `envs/heterogeneity.yml` provides it. lme4 uses a Gaussian likelihood, which is an approximation for a metric bounded in [0, 1] such as ARI; a glmmTMB beta family is the documented extension.

## Relation to leave-one-dataset-out

Both qualify a pooled ranking along the dataset axis, and they answer different questions. Leave-one-dataset-out (`beam.mcda.leave_one_dataset_out`) re-ranks with each dataset removed and asks whether the recommendation depends on any single dataset. The mixed-effects model asks how much of the score variance is interaction at all. The first is a stability check on the composite; the second is a decomposition of the raw metric. Read together, a stable leave-one-dataset-out result with a low interaction share is a ranking you can trust across the datasets at hand. The separate question of whether the methods are statistically separable on a metric is the [Friedman-Nemenyi check](comparing-methods-across-datasets.md).

[Findings 0002](../findings/0002-duo-2018-variance-decomposition.md) works this through on the Duo 2018 ARI scores, and [ADR 0009](../adr/0009-heterogeneity-mixed-effects-via-r.md) records why the fit runs in R through a subprocess.
