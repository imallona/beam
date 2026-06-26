# Dataset concordance

A ranking pooling different metrics aims to answer, across all the datasets at once, which method performs best on average. It cannot say whether the datasets agree on that order.

`beam.mcda.dataset_concordance` measures that agreement directly. It ranks the methods within each dataset separately, then compares every pair of per-dataset orderings with the Kendall tau-b rank correlation. The output is a dataset by dataset agreement matrix and a single mean-agreement summary. A high mean says the pooled ranking represents the individual datasets. A low one says it does not, and a single pooled number then hides heterogeneity the reader should see.

## Why not a power analysis

One way to frame the gap is to ask how many datasets a benchmark needs to settle the ranking. That question assumes the datasets are interchangeable draws from a population, so that counting them is meaningful. But, in many cases, benchmark datasets are not interchangeable, as they differ in size, biology, confounders, whether they are simulated (ground truth) or expert annotated (presumed truth), and a method can be suited to one and not another. This is the point Strobl and colleagues make against a single ranking over heterogeneous data.

Hence, beam does not estimate the number of datasets, akin to a power analysis, and focuses on dataset-specific effects instead.

## Implementation

For each dataset the methods are ranked on that dataset's tool by metric matrix, holding the [weighting](weighting-schemes.md), [aggregation](aggregation-methods.md) and [normalization](normalization-and-scales.md) the standard run carries. Each pair of per-dataset rankings is compared with Kendall tau-b, which handles the tied ranks that competition ranking produces. A dataset whose single-dataset matrix the pipeline cannot rank, for example one with a missing cell under the error policy, is dropped and noted in `evaluated_datasets`.

As a result, the report provides:

- the dataset by dataset tau-b matrix and its off-diagonal mean,
- each dataset's mean agreement with the rest, and the dataset that agrees least,
- a grouping of datasets whose pairwise agreement is at or above a threshold, built as connected components of that relation,
- the per-method mean rank across datasets and the signed rank-deviation table,
- the method-by-dataset cells at least one full rank from a method's mean rank.

## Interpretation

The agreement matrix says how much the datasets disagree. The rank-deviation table says where the disagreement comes from. For each method it records, on each dataset, the method's rank minus its mean rank across datasets. A negative value means the method places higher than its average on that dataset; a positive value means it places lower. The cells far from zero are the method-by-dataset combinations that move the ordering.

This is a within-method comparison.

`beam.plot.dataset_concordance` draws the agreement matrix and `beam.plot.dataset_struggle` draws the rank-deviation table, so both views are available to a notebook or vignette.

## How to read it on a worked example

On the [Duo 2018 clustering benchmark](../../examples/duo2018/duo2018.qmd) (three metrics, equal weights, pooled across the twelve datasets) the mean tau-b is about 0.34, so the datasets share only a moderate ordering. The datasets group into a Koh pair, a Kumar, Sim and Trapnell cluster, and a Zhengmix cluster, which mirrors the way the source studies built the data. The rank-deviation table shows the disagreement concentrating in a few cells: SAFE places last on the harder simulated datasets while sitting mid-table on average, and ascend collapses on the Koh datasets. So the pooled ranking is a reasonable summary for the bulk of the methods, while a handful of method-dataset combinations carry most of the spread.

The diagnostic sits next to the other ways beam evaluates multi-metric composite rankings. Leave-one-dataset-out asks whether the ranking depends on any single dataset. The [critical-difference](comparing-methods-across-datasets.md) and [Skillings-Mack](skillings-mack.md) tests ask whether the methods are separable on one metric. The [Bradley-Terry tree](heterogeneity-bradley-terry.md) splits the datasets by their declared features. Dataset concordance reports the agreement structure among the datasets from the rankings alone, with no features required and no assumption that the datasets are exchangeable.

## References

- Kendall, M. G. (1938). A new measure of rank correlation. Biometrika 30(1-2), 81-93. https://doi.org/10.1093/biomet/30.1-2.81
- Strobl, C., Wickelmaier, F., Zeileis, A., and colleagues. Against the "one method fits all data sets" philosophy for comparison studies in methodological research. Biometrical Journal (2024). https://doi.org/10.1002/bimj.202200104
