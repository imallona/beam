# Attribution synthesis

A benchmark ranking depends on three sources of variation. The first is the analyst's choice of [weighting](weighting-schemes.md) and [aggregation rule](aggregation-methods.md). The second is the dataset: a method that ranks first on one dataset can rank last on another. The third is the benchmark itself: two benchmarks of the same task, each with its own pipeline, methods and datasets, rank their shared methods differently.

beam has a separate measure for each. Within one benchmark, [`rank_sensitivity`](rank-sensitivity.md) gives the fraction of the rank variance due to the analyst's choices and the fraction due to the dataset. Across benchmarks, [`source_variance_decomposition`](method-by-dataset-heterogeneity.md) gives the variance of the mean ranks split between the method and the benchmark. The first is a variance over a grid of weightings, aggregations and datasets. The second comes from a mixed model. The two are on different scales and cannot be compared.

[`attribution_synthesis`](../reference/attribution_synthesis.qmd) expresses both as fractions of one total. For each setting there are three fractions that sum to one: analyst choice, dataset and benchmarker. Across the three settings, from a single benchmark to a contrast on the same datasets, the fractions show which source changes the ranking when the dataset is held fixed.

## How the fractions are computed

Within one benchmark, from a `RankSensitivityReport` over a tool by dataset by metric tensor. Analyst choice is the weighting fraction plus the aggregation fraction. Dataset is the dataset main effect. Benchmarker is zero, since one benchmark does all the scoring. The interaction term is divided between analyst choice and dataset in proportion to their main effects.

Across [pooled benchmarks](network-meta-analysis.md), from a `SourceVarianceReport`. Benchmarker is the method-by-benchmark component, the between-benchmark variation of a method's mean rank. Dataset is every other component: the between-benchmark term, the within-benchmark dataset term and the residual. The pooled scores are mean ranks with no metric axis, so analyst choice cannot be measured here. It is zero unless the caller supplies it, in which case the remainder is divided between benchmarker and dataset in the ratio from the model.

On a same-data contrast, where two or more pipelines score the methods on the same datasets. Dataset is zero by construction. Each method's rank is centred on its mean across the pipelines, which removes the order shared by the pipelines. What is left is divided into a pipeline offset (benchmarker) and a method-by-pipeline reordering (analyst choice). When the pipelines give the same order there is nothing to divide and the fractions are undefined.

## Limitations

The fractions are descriptive, without confidence intervals. Each setting needs its own kind of data: a grid within one benchmark, several benchmarks of one task, or shared datasets across pipelines.

## See also

- [Mixed-effects model](method-by-dataset-heterogeneity.md)
- [Specification curve](rank-sensitivity.md#the-specification-curve)
