# Aggregation agreement: does the recommendation depend on the method?

beam offers five aggregations: SAW, TOPSIS, VIKOR, PROMETHEE II and COMET. Each combines the per-metric scores into one composite under its own assumptions, and the headline ranking commits to one of them. A reader is entitled to ask whether that commitment changed the answer. `beam.mcda.aggregation_agreement` answers it: it re-ranks the same normalized matrix under each aggregation, holding the weighting fixed, and reports how closely the orderings agree.

This is a choice-sensitivity diagnostic, the same family as the others beam ships. Leave-one-metric-out and leave-one-dataset-out vary the inputs, SMAA varies the weights, and this varies the aggregation rule. The aggregation choice is a degree of freedom like any other, and the honest report discloses how much it moves the ranking.

## What it computes

Normalization and weighting happen before aggregation and do not depend on the aggregation rule, so the weight vector is the same across the five methods. The only thing that changes is how the normalized scores collapse into a composite. The diagnostic runs the full pipeline once per method, collects the per-tool ranks, and compares every pair of rankings.

Agreement between two rankings is measured with the Kendall tau-b coefficient. tau-b counts the concordant and discordant pairs of tools and corrects for ties, which matters here because beam uses competition ranking, so ties are common. tau-b is 1 for identical orderings, -1 for exact reversals, and near 0 when the two methods order the tools unrelatedly. The report carries the full method-by-method tau matrix and a single mean of its off-diagonal entries as a summary.

The report also gives a consensus ranking, the ranking of the per-method mean ranks, and a flag that is true only when every aggregation puts the same tool first. The per-tool smallest and largest rank across the methods are the rank span drawn in the consensus panel of the funky heatmap.

## Reading the number

A high mean tau means the recommendation is stable under the aggregation choice: whichever method a reader prefers, they reach about the same order. A low mean tau means the aggregation rule is itself deciding the order, and a ranking presented under one method should be read with that in mind.

The Duo 2018 clustering benchmark is a worked example. On the three-metric pooled matrix (ARI, runtime, Shannon entropy difference) under equal weights, the five aggregations agree at a mean pairwise tau-b of 0.65, and Seurat is the unanimous top under every one of them. So the top recommendation does not hang on the aggregation choice. The agreement is not complete, though. PROMETHEE II correlates only 0.34 to 0.54 with the others, so the ordering in the middle of the table depends on which method is used. This is the typical pattern. The leader is often stable while the mid-tier is not, and a report that prints one full ordering without this caveat overstates how settled the middle is.

## How to use it

Call `aggregation_agreement(scores, polarity)` with a tool by metric matrix and the per-metric polarity from `beam.cards.polarities_for`. Pass the normalization context from `beam.mcda.registry_context` so the comparison rests on the same normalized matrix as the headline ranking. The weighting is held fixed at whatever you pass; the default is equal weights.

A method that cannot run on the input, for example a degenerate matrix that one aggregation rejects, is dropped from the report rather than failing the whole analysis. At least two methods must produce a ranking, otherwise there is nothing to compare and the call raises. When every tool scores identically the orderings are all-ties, tau-b is undefined on a constant ranking, and the mean tau is reported as not-a-number rather than a fabricated agreement of one.

## What it does not do

The diagnostic measures whether the methods agree, not which one is correct. The five aggregations encode different value judgements: TOPSIS rewards closeness to an ideal point, VIKOR seeks a compromise solution, PROMETHEE II nets pairwise outranking flows. A disagreement among them is a real disagreement about what a good composite is, not an error to be averaged away. The consensus ranking is a convenience summary, not a sixth aggregation with its own claim to correctness. When the methods disagree the right response is to report the disagreement and the value judgement behind the chosen method, not to hide it behind the mean.

## References

- Kendall, M. G. A new measure of rank correlation. Biometrika 30 (1938). DOI [10.1093/biomet/30.1-2.81](https://doi.org/10.1093/biomet/30.1-2.81).
- The five aggregations and their assumptions are covered in [Aggregation methods](aggregation-methods.md).
