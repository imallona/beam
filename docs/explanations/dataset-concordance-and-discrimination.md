# Dataset concordance and discrimination

A ranking pooling different metrics aims to answer, across all the datasets at once, which method performs best on average. It cannot say whether the datasets agree on that order.

[`beam.mcda.dataset_concordance`](../reference/dataset_concordance.qmd) measures that agreement directly. It ranks the methods within each dataset separately, then compares every pair of per-dataset orderings with the Kendall tau-b rank correlation. The output is a dataset by dataset agreement matrix and a single mean-agreement summary. A high mean says the pooled ranking represents the individual datasets. A low one says it does not, and a single pooled number then obscures the heterogeneity.

Counting datasets, as a power analysis would, assumes they are interchangeable draws from a population. Benchmark datasets often are not: they differ in size, biology, confounders, and whether they are simulated (ground truth) or expert annotated (presumed truth), and a method can suit one and not another. This is the point Strobl and colleagues make against a single ranking over heterogeneous data.

So beam reports dataset-specific effects instead.

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



`beam.plot.dataset_concordance` draws the agreement matrix and `beam.plot.dataset_struggle` draws the rank-deviation table, so both views are available to a notebook or vignette.

On the [Duo 2018 clustering benchmark](../../examples/duo2018/duo2018.qmd) (three metrics, equal weights, pooled across the twelve datasets) the mean tau-b is about 0.34, so the datasets share only a moderate ordering. The datasets group into a Koh pair, a Kumar, Sim and Trapnell cluster, and a Zhengmix cluster, which mirrors the way the source studies built the data. The rank-deviation table shows the disagreement concentrating in a few cells: SAFE places last on the harder simulated datasets while sitting mid-table on average, and ascend collapses on the Koh datasets. So the pooled ranking is a reasonable summary for the bulk of the methods, while a handful of method-dataset combinations carry most of the spread.

The diagnostic sits next to the other ways beam evaluates multi-metric composite rankings. Leave-one-dataset-out asks whether the ranking depends on any single dataset. The [critical-difference](critical-difference.md) and [Skillings-Mack](critical-difference.md#skillings-mack-for-incomplete-blocks) tests ask whether the methods are separable on one metric. The [Bradley-Terry tree](method-by-dataset-heterogeneity.md#bradley-terry-trees) splits the datasets by their declared features.

## Dataset discrimination

Concordance needs shared methods: it compares method orders across datasets. A property defined per dataset needs no shared methods, and every benchmark can report it: how much a dataset separates the methods it scores. [`beam.mcda.dataset_discrimination`](../reference/dataset_discrimination.qmd) computes it. A dataset on which the methods score about the same cannot rank them; one on which they differ can. This is the per-dataset form of the metric-level idea in the [weighting code](weighting-schemes.md), where a metric on which methods do not differ has no discrimination.

beam computes two values per dataset.

- Spread, the effect size. Each metric is oriented to higher-is-better and min-max scaled across the benchmark's cells, so metrics are comparable and a dataset on which every method scores near the maximum keeps a small spread. The metrics are pooled to one score per method, and the spread is the standard deviation across methods.
- Concordance, the consistency. Kendall's W over the dataset's method-by-metric matrix, with its Friedman p value. A high W means the metrics order the methods the same way; a low W means they do not, so a single ranking on that dataset is unstable.

A dataset with high spread and high W separates the methods, and its metrics agree on the order. The scaling is per benchmark, so spreads are comparable within a benchmark and only roughly across benchmarks. A method or metric not observed on a dataset stays NaN and is handled available-case, never imputed: spread uses the observed methods, and Kendall's W uses the complete method-by-metric block, reported only when at least `min_methods` methods and two metrics remain.

### Hard datasets

A dataset can be hard because the biology is complex, in which case every method struggles, or because it puts some methods at a disadvantage, for example label quality for semi-supervised methods that would not affect fully unsupervised ones. [`beam.mcda.difficulty_concordance`](../reference/difficulty_concordance.qmd) separates the two. It splits the methods into groups, measures each dataset's difficulty for each group as the group's mean pooled score, and correlates the per-group difficulty profiles across datasets with Spearman. High concordance means the hardness comes from the data; low concordance means it comes from the kind of method.

On the [OpenProblems batch-integration task](../../examples/openproblems/openproblems.qmd) the deep-learning and classical methods agree (Spearman about 0.89). On the Shen 2026 benchmark, whose scenarios degrade annotation quality, they agree weakly (about 0.32), and the hard cases are harder for the label-using deep-learning methods.

## References

- Kendall, M. G. (1938). A new measure of rank correlation. Biometrika 30(1-2), 81-93. https://doi.org/10.1093/biomet/30.1-2.81
- Strobl, C., Wickelmaier, F., Zeileis, A., and colleagues. Against the "one method fits all data sets" philosophy for comparison studies in methodological research. Biometrical Journal (2024). https://doi.org/10.1002/bimj.202200104
