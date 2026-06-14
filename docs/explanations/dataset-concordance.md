# Dataset concordance

A pooled ranking answers one question: across all the datasets at once, which method does best on average. It cannot say whether the datasets agree on that order or pull in different directions. Two benchmarks with the same pooled ranking can hide very different structure. In one, every dataset orders the methods the same way and the pooled number is a faithful summary. In the other, the datasets disagree and the pooled number is an average over orderings that contradict each other.

`beam.mcda.dataset_concordance` measures that agreement directly. It ranks the methods within each dataset under the same pipeline as the headline run, then compares every pair of per-dataset orderings with the Kendall tau-b rank correlation. The output is a dataset by dataset agreement matrix and a single mean-agreement summary. A high mean says the pooled ranking stands in for the individual datasets. A low one says it does not, and a single pooled number then hides heterogeneity the reader should see.

## Why not a power analysis

One way to frame the gap is to ask how many datasets a benchmark needs to settle the ranking. That question assumes the datasets are interchangeable draws from a population, so that counting them is meaningful. Benchmark datasets are not interchangeable. They differ in size, biology, and whether they are simulated or real, and a method can be suited to one and not another. This is the point Strobl and colleagues make against a single ranking over heterogeneous data.

So beam does not estimate a required dataset count. It measures the heterogeneity that makes the count ill-posed. A low concordance is direct evidence that the datasets do not share one ordering, which is more useful than a sample-size number that assumes they do.

## What it computes

For each dataset the methods are ranked on that dataset's tool by metric matrix, holding the weighting, aggregation and normalization fixed at the headline choices. Each pair of per-dataset rankings is compared with Kendall tau-b, which handles the tied ranks that competition ranking produces. A dataset whose single-dataset matrix the pipeline cannot rank, for example one with a missing cell under the error policy, is dropped and noted in `evaluated_datasets`.

The report carries:

- the dataset by dataset tau-b matrix and its off-diagonal mean,
- each dataset's mean agreement with the rest, and the dataset that agrees least,
- a grouping of datasets whose pairwise agreement is at or above a threshold, built as connected components of that relation,
- the per-method mean rank across datasets and the signed rank-deviation table,
- the method-by-dataset cells at least one full rank from a method's mean rank.

## Reading the rank-deviation table

The agreement matrix says how much the datasets disagree. The rank-deviation table says where the disagreement comes from. For each method it records, on each dataset, the method's rank minus its mean rank across datasets. A negative value means the method places higher than its average on that dataset; a positive value means it places lower. The cells far from zero are the method-by-dataset combinations that move the ordering.

This is a within-method comparison, not a verdict on which method is preferable. It locates where a method departs from its own typical placement, so a reader can see that a method suited to most datasets struggles on a particular one, without that observation being read as an overall ranking.

`beam.plot.dataset_concordance` draws the agreement matrix and `beam.plot.dataset_struggle` draws the rank-deviation table, so both views are available to a notebook or vignette.

## How to read it on real data

On the Duo 2018 clustering benchmark (three metrics, equal weights, pooled across the twelve datasets) the mean tau-b is about 0.34, so the datasets share only a moderate ordering. The datasets group into a Koh pair, a Kumar, Sim and Trapnell cluster, and a Zhengmix cluster, which mirrors the way the source studies built the data. The rank-deviation table shows the disagreement concentrating in a few cells: SAFE places last on the harder simulated datasets while sitting mid-table on average, and ascend collapses on the Koh datasets. So the pooled ranking is a reasonable summary for the bulk of the methods, while a handful of method-dataset combinations carry most of the spread.

The diagnostic sits next to the other ways beam qualifies a pooled ranking. Leave-one-dataset-out asks whether the ranking depends on any single dataset. The critical-difference and Skillings-Mack tests ask whether the methods are separable on one metric. The Bradley-Terry tree splits the datasets by their declared features. Dataset concordance is the feature-free companion to the tree: it reports the agreement structure among the datasets from the rankings alone, with no features required and no assumption that the datasets are exchangeable.

## References

- Kendall, M. G. (1938). A new measure of rank correlation. Biometrika 30(1-2), 81-93. https://doi.org/10.1093/biomet/30.1-2.81
- Strobl, C., Wickelmaier, F., Zeileis, A., and colleagues. Against the "one method fits all data sets" philosophy for comparison studies in methodological research. Biometrical Journal (2024). https://doi.org/10.1002/bimj.202200104
