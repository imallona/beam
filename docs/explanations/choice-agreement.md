# Choice agreement: aggregation and normalization

Two analyst choices can move a ranking with no change to the data: which [aggregation rule](aggregation-methods.md) combines the per-metric scores, and which [normalization](normalization-and-scales.md) rescales them first. beam has a paired diagnostic for each. Both re-rank the same matrix under the alternatives and report how far the rankings agree. They join the other checks on the analyst's degrees of freedom: leave-one-metric-out, leave-one-dataset-out, the weight sampling in stochastic multicriteria acceptability analysis (SMAA), and the [variance decomposition](rank-sensitivity.md) that splits a ranking across all of those choices at once.

## Measuring agreement

Each diagnostic runs the full pipeline once per alternative, collects the per-tool ranks, and compares every pair of rankings with the Kendall tau-b coefficient. tau-b counts the concordant and discordant pairs of tools and corrects for ties, which matters here because beam uses competition ranking, so ties are common. It is 1 for identical orderings, -1 for exact reversals, and near 0 when two orderings are unrelated. The report carries the full tau matrix, the mean of its off-diagonal entries as a summary, a consensus ranking (the ranking of the per-alternative mean ranks), and a flag for whether the top method holds across the alternatives. The per-tool smallest and largest rank become the rank span the [funky heatmap](funky-heatmaps-and-robustness.md) draws.

## Aggregation agreement

[`beam.mcda.aggregation_agreement`](../reference/aggregation_agreement.qmd) varies the aggregation rule across the five aggregations: SAW, TOPSIS, VIKOR, PROMETHEE II and [COMET](aggregation-methods.md#comet). Normalization and [weighting](weighting-schemes.md) happen before aggregation and do not depend on the rule, so the weight vector is the same across the five and only the aggregation step changes.

A high mean tau means the recommendation is stable under the aggregation choice. A low mean tau means the aggregation rule is itself deciding the order. On the [Duo 2018 clustering benchmark](../../examples/duo2018/duo2018.qmd), on the three-metric pooled matrix (the Adjusted Rand Index, runtime, Shannon entropy difference) under equal weights, the five aggregations agree at a mean pairwise tau-b of 0.65, and Seurat is the unanimous top under every one of them. PROMETHEE II still correlates only 0.34 to 0.54 with the others, so the middle of the ranking depends on which method is used.

Call `aggregation_agreement(scores, polarity)` with a tool by metric matrix and the per-metric polarity from [`beam.cards.polarities_for`](../reference/polarities_for.qmd), and pass the normalization context from `beam.mcda.registry_context` so the comparison rests on the same normalized matrix as the headline ranking. An aggregation that fails on the input is dropped rather than failing the analysis; at least two must produce a ranking. When every tool scores identically the orderings are all-ties, tau-b is undefined and the run fails.

The five aggregations encode different value judgements: TOPSIS rewards closeness to an ideal point, VIKOR seeks a compromise solution, PROMETHEE II nets pairwise outranking flows. A disagreement among them is a disagreement about what a composite metric should do.

## Normalization agreement

[`beam.mcda.normalization_agreement`](../reference/normalization_agreement.qmd) varies the normalization instead. By default it compares the four scale-agnostic strategies, `min_max`, `log_min_max`, `rank` and `zscore`, each applied to every column. `baseline_relative` and `target_relative` are left out of the uniform sweep: they need a per-metric reference or target from the card and are tied to the metric's meaning, so they are not a free choice the analyst makes column by column. The card-recommended per-metric normalization can be passed as one labelled candidate, and `beam.rank` passes it as the `recommended` column so the report compares the headline default against the uniform alternatives.

One difference from aggregation agreement: the objective [weights](weighting-schemes.md) (entropy, standard deviation, CRITIC, MEREC) are computed from the normalized matrix, so changing the normalization also changes those weights. That is intended, and the report shows the normalization's total effect on the order, not just the part that acts through the aggregation step.

On the same Duo 2018 matrix under equal weights, the card-recommended normalization and the four uniform strategies agree at a mean pairwise tau-b of 0.64, and Seurat is again the unanimous top. The recommended normalization agrees with `min_max` at tau-b 0.79 but with `rank` at only 0.36, because the rank normalization drops the gap sizes that the other strategies keep, so the ordering in the middle of the table moves.

Call `normalization_agreement(scores, polarity)` with `recommended=RegistryContext.normalization` and the same `bounds`, `baselines` and `targets` the headline ranking used. A candidate that cannot run is dropped: `log_min_max` needs strictly positive values, and a `target_value` metric admits only `target_relative`, so the uniform strategies all drop on a matrix that contains one. `beam.plot.normalization_agreement(run)` draws the tau-b heatmap and `beam.plot.normalization_effect(run)` a bump chart of each tool's rank across the strategies; the funky heatmap gains a normalization rank-span panel with `show_normalization_consensus=True`. [Normalization and scales](normalization-and-scales.md) covers why the card recommends what it does.

## References

- Kendall, M. G. A new measure of rank correlation. Biometrika 30 (1938). DOI [10.1093/biomet/30.1-2.81](https://doi.org/10.1093/biomet/30.1-2.81).
