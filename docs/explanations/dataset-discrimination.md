# Dataset discrimination

Most cross-benchmark comparisons ask whether benchmarks agree on the method order, which requires shared methods. When the method sets are disjoint, that comparison is unavailable. A property defined per dataset is still available: how much a dataset separates the methods it scores. Every benchmark can report it for every dataset.

`beam.mcda.dataset_discrimination` computes it from the scores. A dataset on which the methods score about the same cannot rank them; a dataset on which they differ can. This is the per-dataset form of the metric-level idea in the weighting code, where a metric on which methods do not differ has no discrimination. It complements `dataset_concordance`, which asks whether datasets agree on the order.

## What it computes

Two values per dataset.

- Spread, the effect size. Each metric is oriented to higher-is-better and min-max scaled across the benchmark's cells, so metrics are comparable and a dataset on which every method scores near the maximum keeps a small spread. The metrics are pooled to one score per method, and the spread is the standard deviation across methods.
- Concordance, the consistency. Kendall's W over the dataset's method-by-metric matrix, with its Friedman p value. A high W means the metrics order the methods the same way; a low W means they do not, so a single ranking on that dataset is unstable.

A dataset with high spread and high W separates the methods, and its metrics agree on the order. The scaling is per benchmark, so spreads are comparable within a benchmark and only roughly across benchmarks.

## Missing cells

A method or metric not observed on a dataset stays NaN and is handled available-case, never imputed. Spread uses the observed methods. Kendall's W uses the complete method-by-metric block and is reported only when at least `min_methods` methods and two metrics remain.

## Do method families find the same datasets hard?

A dataset can be hard because the biology is complex, in which case every method struggles, or because of something one family of methods depends on, such as label quality for semi-supervised methods, in which case another family is unaffected.

`beam.mcda.difficulty_concordance` separates the two. It splits the methods into families, measures each dataset's difficulty for each family as the family's mean pooled score, and correlates the family difficulty profiles across datasets with Spearman. High concordance means the hardness comes from the data; low concordance means it comes from the method family.

On the OpenProblems batch-integration task the deep-learning and classical families agree (Spearman about 0.89). On the Shen 2026 benchmark, whose scenarios degrade annotation quality, they agree weakly (about 0.32), and the hard cases are harder for the label-using deep-learning family.

## See also

- `beam.mcda.dataset_concordance`.
- The cross-benchmark vignette runs both diagnostics on Shen 2026 and contrasts the result with OpenProblems.
