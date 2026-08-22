# Choice agreement: aggregation and normalization

Two analyst choices change a ranking without a change in the data: the [aggregation rule](aggregation-methods.md) and the [normalization](normalization-and-scales.md). beam re-ranks the same matrix under the alternatives of each and reports how far the rankings agree.

## Method

The pipeline runs once per alternative. Every pair of rankings is compared with Kendall tau-b, which corrects for ties; beam uses competition ranking, so ties are common. The report has the tau matrix, its off-diagonal mean, a consensus ranking (the ranking of the per-alternative mean ranks), and whether the top method is the same under every alternative. The smallest and largest rank per tool are the rank span of the [funky heatmap](funky-heatmaps-and-robustness.md).

## Aggregation agreement

[`beam.mcda.aggregation_agreement`](../reference/aggregation_agreement.qmd) compares the five aggregations: SAW, TOPSIS, VIKOR, PROMETHEE II and [COMET](aggregation-methods.md#comet). Normalization and [weighting](weighting-schemes.md) precede aggregation, so the weight vector is the same for the five.

`aggregation_agreement(scores, polarity)` takes a tool by metric matrix, the polarity from [`beam.cards.polarities_for`](../reference/polarities_for.qmd), and the normalization context from `beam.mcda.registry_context`. An aggregation that fails on the input is dropped; at least two must produce a ranking. When every tool scores identically the orderings are all-ties, tau-b is undefined and the mean tau is NaN.

## Normalization agreement

[`beam.mcda.normalization_agreement`](../reference/normalization_agreement.qmd) compares `min_max`, `log_min_max`, `rank` and `zscore`, each applied to every column. `baseline_relative` and `target_relative` need a per-metric reference or target from the card and are not part of the comparison. The card-recommended normalization can be passed as one more candidate; `beam.rank` passes it as `recommended`.

The objective [weights](weighting-schemes.md) (entropy, standard deviation, CRITIC, MEREC) are computed from the normalized matrix, so they change with the normalization. The report shows the total effect on the order.

`normalization_agreement(scores, polarity)` takes `recommended=RegistryContext.normalization` and the `bounds`, `baselines` and `targets` of the ranking. A candidate that cannot run is dropped: `log_min_max` needs strictly positive values, and a `target_value` metric admits only `target_relative`. `beam.plot.normalization_agreement(run)` draws the tau-b heatmap and `beam.plot.normalization_effect(run)` a bump chart of the ranks per strategy. `show_normalization_consensus=True` adds a rank-span panel to the funky heatmap.

## References

- Kendall, M. G. A new measure of rank correlation. Biometrika 30 (1938). DOI [10.1093/biomet/30.1-2.81](https://doi.org/10.1093/biomet/30.1-2.81).
