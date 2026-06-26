# Dataset discrimination

Most cross-benchmark comparisons (e.g., analyzing multiple benchmarks aiming to address the same task) ask whether benchmarks agree on the method order, which requires shared methods. When the method sets are disjoint, that comparison is not possible. Yet a property defined per dataset is still available: how much a dataset separates the methods it scores. Every benchmark can report it for every dataset.

`beam.mcda.dataset_discrimination` computes it from the scores. A dataset on which the methods score about the same cannot rank them; a dataset on which they differ can. This is the per-dataset form of the metric-level idea in the [weighting code](weighting-schemes.md), where a metric on which methods do not differ has no discrimination. It complements [dataset concordance](dataset-concordance.md), which asks whether datasets agree on the order.

## Implementation 

beam computes two values per dataset.

- Spread, the effect size. Each metric is oriented to higher-is-better and min-max scaled across the benchmark's cells, so metrics are comparable and a dataset on which every method scores near the maximum keeps a small spread. The metrics are pooled to one score per method, and the spread is the standard deviation across methods.
- Concordance, the consistency. Kendall's W over the dataset's method-by-metric matrix, with its Friedman p value. A high W means the metrics order the methods the same way; a low W means they do not, so a single ranking on that dataset is unstable.

A dataset with high spread and high W separates the methods, and its metrics agree on the order. The scaling is per benchmark, so spreads are comparable within a benchmark and only roughly across benchmarks.

A method or metric not observed on a dataset stays NaN and is handled available-case, never imputed. Spread uses the observed methods. Kendall's W uses the complete method-by-metric block and is reported only when at least `min_methods` methods and two metrics remain.

## Hard datasets

A dataset can be hard because the biology is complex, in which case every method struggles, or because it provides a disadvantage to some methods, e.g. label quality for semi-supervised methods that wouldn't affect fully unsupervised methods. `beam.mcda.difficulty_concordance` aims to separate the two. It splits the methods into groups, measures each dataset's difficulty for each group as the group's mean pooled score, and correlates the per-group difficulty profiles across datasets with Spearman. High concordance means the hardness comes from the data; low concordance means it comes from the kind of method.

On the [OpenProblems batch-integration task](../../examples/openproblems/openproblems.qmd) the deep-learning and classical methods agree (Spearman about 0.89). On the Shen 2026 benchmark, whose scenarios degrade annotation quality, they agree weakly (about 0.32), and the hard cases are harder for the label-using deep-learning methods.

## See also

- [Dataset concordance](dataset-concordance.md)
- [OpenProblems as a data source](openproblems-as-a-data-source.md)
