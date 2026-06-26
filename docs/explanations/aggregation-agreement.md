# Aggregation agreement: does the benchmark result depend on the aggregation method?

beam offers [five aggregations](aggregation-methods.md): SAW, TOPSIS, VIKOR, PROMETHEE II and [COMET](comet.md). Each combines the per-metric scores into a composite under each aggregation method own assumptions, and the headline ranking commits to one of them  The question tat follows is whether that commitment changes the evaluation results. `beam.mcda.aggregation_agreement` addresses this by re-ranking the same (normalized) input metrics matrix under each aggregation, holding the weighting fixed. Then, the agreement of the ranks is reported.

This can be read as a diagnostic of choice sensitivity, complementing beam's leave-one-metric-out and leave-one-dataset-out functions and weight variation via stochastic multicriteria acceptability analysis (SMAA). This aggregation agreement procedure evaluates the remaining degree of freedom to choose a final rank.

## Method

[Normalization](normalization-and-scales.md) and [weighting](weighting-schemes.md) happen before aggregation and do not depend on the aggregation rule, so the weight vector is the same across the five methods. So only the aggregation step is evaluated here. The diagnostic runs the full pipeline once per method, collects the per-tool ranks, and compares every pair of rankings.

Agreement between two rankings is measured with the Kendall tau-b coefficient. tau-b counts the concordant and discordant pairs of tools and corrects for ties, which matters here because beam uses competition ranking, so ties are common. tau-b is 1 for identical orderings, -1 for exact reversals, and near 0 when the two methods order the tools randomly. The report plots the full method-by-method tau matrix and a single mean of its off-diagonal entries as a summary.

The report also gives a consensus ranking, the ranking of the per-method mean ranks, and a diagnostic flag reporting whether the top ranked method is stable across aggregations.  The per-tool smallest and largest rank across the methods are the rank span drawn in the consensus panel of the [funky heatmap](funky-heatmaps-and-robustness.md).

## Interpretation

A high mean tau means the recommendation is stable under the aggregation choice: whichever method a reader prefers, they reach about the same order. A low mean tau means the aggregation rule is itself deciding the order.

The [Duo 2018 clustering benchmark](../../examples/duo2018/duo2018.qmd) is a worked example. On the three-metric pooled matrix (the Adjusted Rand Index, runtime, Shannon entropy difference) under equal weights, the five aggregations agree at a mean pairwise tau-b of 0.65, and Seurat is the unanimous top under every one of them. So the top recommendation does not depend on the aggregation choice. The agreement is not complete, though. PROMETHEE II correlates only 0.34 to 0.54 with the others, so the ordering in the middle of the ranking depends on which method is used.

## How to use it

Call `aggregation_agreement(scores, polarity)` with a tool by metric matrix and the per-metric polarity from `beam.cards.polarities_for`. Pass the normalization context from `beam.mcda.registry_context` so the comparison rests on the same normalized matrix as the headline ranking. The weighting is held fixed at whatever you pass; the default is equal weights.

In case an aggregation method fails to run on the input then it is dropped from the report rather than failing the whole analysis. At least two methods must produce a ranking, otherwise there is nothing to compare. When every tool scores identically the orderings are all-ties, tau-b is undefined and the run fails.

## What it does not do

The diagnostic measures whether the methods agree, not which one is correct. The five aggregations encode different value judgements: TOPSIS rewards closeness to an ideal point, VIKOR seeks a compromise solution, PROMETHEE II nets pairwise outranking flows. A disagreement among them is a disagreement about what a composite metric should do. The consensus ranking is a convenience summary. Typically, incompatible results from different aggregation methods point to some disagreement that has to be further evaluated.

## See also

- [Aggregation methods](aggregation-methods.md)

## References

- Kendall, M. G. A new measure of rank correlation. Biometrika 30 (1938). DOI [10.1093/biomet/30.1-2.81](https://doi.org/10.1093/biomet/30.1-2.81).
