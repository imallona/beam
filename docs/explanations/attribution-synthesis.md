# Attribution synthesis

A benchmark ranking is affected by three factors. The analyst's choices, the [weighting](weighting-schemes.md) and the [aggregation rule](aggregation-methods.md). The datasets: a method that ranks first on one dataset trails on another. And the benchmarker: two benchmarks of the same task, each with its own pipeline, methods and datasets, rank the shared methods differently. beam already measures these one at a time. [`rank_sensitivity`](rank-sensitivity.md) splits a ranking between the choices and the dataset. [`source_variance_decomposition`](method-by-dataset-heterogeneity.md) splits a method's standing between the benchmark and the method. The two use different scales, so they cannot be compared directly.

[`attribution_synthesis`](../reference/attribution_synthesis.qmd) puts them on one scale. For each setting it gives three independent axes, for analyst choice, dataset and benchmarker, that sum to one. Compared across settings, from one benchmark to a contrast where the datasets are held fixed, the axes show how the source of the movement changes as the dataset contribution is removed.

## Approach

Within one benchmark, from a `RankSensitivityReport` over a tool by dataset by metric tensor: analyst choice is the weighting plus aggregation share, the dataset share is the dataset main effect, and benchmarker is zero because one benchmark does the scoring. The interaction share is split between analyst choice and dataset in proportion to the main effect each already carries.

Across [pooled benchmarks](network-meta-analysis.md) (e.g., different benchmarks on the same task), from a `SourceVarianceReport`: benchmarker is the method-by-benchmark component, the part of a method's standing that changes between benchmarks. The dataset share is every other component (the between-benchmark and within-benchmark-dataset terms and the residual). The pooled scores are mean ranks with no metric axis, so analyst choice cannot be measured here and is set to zero unless supplied. If/when supplied, the rest of the budget is split between benchmarker and dataset in the ratio the model gives.

On a same-data contrast, where two or more pipelines score the methods on the same datasets: the dataset share is zero by construction. Each method's rank is centred on its mean across the pipelines, removing the part they agree on. What remains is split into a pipeline offset (benchmarker) and the method-by-pipeline reordering (analyst choice). When the pipelines give the same order there is nothing to attribute and the shares are undefined.

## Limitations

The axes are descriptive, without confidence intervals, and limited by data availability (different benchmarks, shared datasets, shared methods).

## See also

- [Mixed-effects model](method-by-dataset-heterogeneity.md)
- [Specification curve](rank-sensitivity.md#the-specification-curve)
