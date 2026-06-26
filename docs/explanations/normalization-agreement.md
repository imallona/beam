# Normalization agreement: does the recommendation depend on the rescaling?

Before any weighting or aggregation, beam rescales each metric column to the unit interval so the metrics can be combined. The strategy is read per metric from the card field `comparability.recommended_normalization`, but it is a real analyst choice. A rank normalization keeps the order of the methods and drops the size of the gaps between them. `log_min_max` keeps the multiplicative structure of a ratio metric, so one slow method no longer compresses the differences among the fast ones. `zscore` standardizes the column and compresses an outlier smoothly. These can produce different orders from the same raw scores. `beam.mcda.normalization_agreement` asks how much that choice moves the ranking, the same question [`aggregation_agreement`](aggregation-agreement.md) asks about the aggregation rule.

This is a choice-sensitivity diagnostic, the same family as the others beam ships. Leave-one-metric-out and leave-one-dataset-out vary the inputs, stochastic multicriteria acceptability analysis (SMAA) varies the weights, `aggregation_agreement` varies the aggregation rule, and this varies the normalization. The normalization is the one analyst choice the others leave untested.

## Rationale

The diagnostic re-ranks the same matrix under several normalizations, holding the weighting and the aggregation fixed. It runs the full pipeline once per candidate, collects the per-tool ranks, and compares every pair of rankings.

One point separates this from `aggregation_agreement`. Objective weights (entropy, standard deviation, CRITIC, MEREC) are computed from the normalized matrix, so changing the normalization also changes those weights. That is intended. The normalization choice propagates through the whole pipeline, and the report shows its total effect on the order, not just the part that acts through the aggregation step.

Agreement between two rankings is measured with the Kendall tau-b coefficient. tau-b counts the concordant and discordant pairs of tools and corrects for ties, which matters because beam uses competition ranking, so ties are common. tau-b is 1 for identical orderings, -1 for exact reversals, and near 0 when the two orderings are unrelated. The report carries the full label-by-label tau matrix and the mean of its off-diagonal entries as a summary. It also gives a consensus ranking, the ranking of the per-label mean ranks, and a flag that is true only when every normalization puts the same tool first. The per-tool smallest and largest rank across the labels are the rank span the [funky heatmap](funky-heatmaps-and-robustness.md) draws in its normalization panel.

## Which normalizations are compared

By default the diagnostic compares the four scale-agnostic strategies: `min_max`, `log_min_max`, `rank` and `zscore`, each applied to every metric column. `baseline_relative` and `target_relative` are left out of this uniform sweep. They need a per-metric reference or target value from the card and are tied to the metric's meaning, so they are not a free choice the analyst makes column by column.

The card-recommended per-metric normalization can be passed in as one labelled candidate. When `beam.rank` runs the diagnostic for the HTML report it passes the recommended strategies as the `recommended` column, so the report compares the headline default against the uniform alternatives rather than comparing only the uniform ones with each other.

A candidate that cannot run on the input is dropped rather than failing the whole analysis. `log_min_max` requires strictly positive values, so a column with a zero or a negative value drops that candidate. A `target_value` metric admits only `target_relative`, so the uniform strategies all drop on a matrix that contains one. At least two candidates must produce a ranking, otherwise there is nothing to compare and the call raises.

## Interpreting results

A high mean tau means the recommendation is stable under the normalization choice: whichever rescaling a reader prefers, they reach about the same order. A low mean tau means the rescaling is itself deciding the order, and a ranking presented under one normalization should be read with that in mind.

The [Duo 2018 clustering benchmark](../../examples/duo2018/duo2018.qmd) is a worked example. On the three-metric pooled matrix (the Adjusted Rand Index, runtime, Shannon entropy difference) under equal weights, the card-recommended normalization and the four uniform strategies agree at a mean pairwise tau-b of 0.64, and Seurat is the unanimous top under every one of them. So the top recommendation does not depend on the rescaling. The agreement is not complete. The recommended normalization agrees with `min_max` at tau-b 0.79 but with `rank` at only 0.36, because the rank normalization drops the gap sizes that the other strategies keep, so the ordering in the middle of the table moves. This is the typical pattern. The leader is often stable while the mid-tier is not, and a report that prints one full ordering without this caveat overstates how settled the middle is.

## How to run

Call `normalization_agreement(scores, polarity)` with a tool by metric matrix and the per-metric polarity from `beam.cards.polarities_for`. Pass `recommended=RegistryContext.normalization` so the card default is compared against the uniform strategies, and pass the same `bounds`, `baselines` and `targets` the headline ranking used. The weighting and the aggregation are held fixed at whatever you pass; the defaults are equal weights and weighted sum.

For plotting, `beam.plot.normalization_agreement(run)` generates the tau-b heatmap and `beam.plot.normalization_effect(run)` gives a bump chart of each tool's rank across the strategies, so you can follow which methods move. The funky heatmap gains a normalization rank-span panel when you pass `show_normalization_consensus=True`.

## Limitations

The diagnostic measures whether the normalizations agree, not which one is correct. The strategies encode different decisions about what a comparable score is: `min_max` treats the observed range as the scale, `rank` treats only the order as meaningful, `log_min_max` treats ratios as the meaningful structure. A disagreement among them is a real disagreement about how the metric should be read, not an error to be averaged away. The consensus ranking is a convenience summary, not a preferred normalization. When the strategies disagree the right response is to report the disagreement and the reason the card recommends what it does, covered in [Normalization and scales](normalization-and-scales.md).

## References

- Kendall, M. G. A new measure of rank correlation. Biometrika 30 (1938). DOI [10.1093/biomet/30.1-2.81](https://doi.org/10.1093/biomet/30.1-2.81).
- The normalization strategies and when each is appropriate are covered in [Normalization and scales](normalization-and-scales.md).
- The companion diagnostic on the aggregation rule is [Aggregation agreement](aggregation-agreement.md).
