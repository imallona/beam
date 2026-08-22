# Dataset concordance and discrimination

A ranking pooling different metrics aims to answer, across all the datasets at once, which method performs best on average. It cannot say whether the datasets agree on that order.

[`beam.mcda.dataset_concordance`](../reference/dataset_concordance.qmd) measures that agreement directly. It ranks the methods within each dataset separately, then compares every pair of per-dataset orderings with the Kendall tau-b rank correlation. The output is a dataset by dataset agreement matrix and a single mean-agreement summary. A high mean says the pooled ranking represents the individual datasets. A low one says it does not, and a single pooled number then obscures the heterogeneity.

Benchmark datasets differ in size, biology, confounders, and whether they are simulated (ground truth) or expert annotated (presumed truth), and a method can suit one and not another (Strobl and colleagues 2024).

## Implementation

For each dataset the methods are ranked on that dataset's tool by metric matrix, holding the [weighting](weighting-schemes.md), [aggregation](aggregation-methods.md) and [normalization](normalization-and-scales.md) the standard run carries. Each pair of per-dataset rankings is compared with Kendall tau-b, which handles the tied ranks that competition ranking produces. A dataset whose single-dataset matrix the pipeline cannot rank, for example one with a missing cell under the error policy, is dropped and noted in `evaluated_datasets`.

As a result, the report provides:

- the dataset by dataset tau-b matrix and its off-diagonal mean,
- each dataset's mean agreement with the rest, and the dataset that agrees least,
- a grouping of datasets whose pairwise agreement is at or above a threshold, built as connected components of that relation,
- the per-method mean rank across datasets and the signed rank-deviation table,
- the method-by-dataset cells at least one full rank from a method's mean rank.

## Interpretation

The rank-deviation table has, for each method and dataset, the rank on that dataset minus the mean rank across datasets. A negative value is a better rank than average.

`beam.plot.dataset_concordance` draws the agreement matrix and `beam.plot.dataset_struggle` the rank-deviation table.

The diagnostic sits next to the other ways beam evaluates multi-metric composite rankings. Leave-one-dataset-out asks whether the ranking depends on any single dataset. The [critical-difference](critical-difference.md) and [Skillings-Mack](critical-difference.md#skillings-mack-for-incomplete-blocks) tests ask whether the methods are separable on one metric. The [Bradley-Terry tree](method-by-dataset-heterogeneity.md#bradley-terry-trees) splits the datasets by their declared features.

## Dataset discrimination

[`beam.mcda.dataset_discrimination`](../reference/dataset_discrimination.qmd) measures how much a dataset separates the methods it scores. It needs no methods shared between datasets.

beam computes two values per dataset.

- Spread. Each metric is oriented to higher-is-better and min-max scaled across the cells of the benchmark. The metrics are pooled to one score per method, and the spread is the standard deviation across methods.
- Concordance. Kendall's W over the method by metric matrix of the dataset, with its Friedman p value. A high W means the metrics order the methods the same way.

Spreads are comparable within a benchmark and only roughly across benchmarks. Missing cells are not imputed: the spread uses the observed methods, and Kendall's W the complete cases, when at least `min_methods` methods and two metrics remain.

### Hard datasets

A dataset can be hard for every method, or for some kinds of method only. [`beam.mcda.difficulty_concordance`](../reference/difficulty_concordance.qmd) splits the methods into groups, takes the mean pooled score of each group on each dataset as its difficulty, and correlates the difficulty profiles of the groups across datasets with Spearman. A high correlation means the difficulty comes from the data.

## References

- Kendall, M. G. (1938). A new measure of rank correlation. Biometrika 30(1-2), 81-93. https://doi.org/10.1093/biomet/30.1-2.81
- Strobl, C., Wickelmaier, F., Zeileis, A., and colleagues. Against the "one method fits all data sets" philosophy for comparison studies in methodological research. Biometrical Journal (2024). https://doi.org/10.1002/bimj.202200104
