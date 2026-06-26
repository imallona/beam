# Reference levels: chance baseline and noise floor

A ranking always produces an order, even when the scores behind it carry no real signal. beam reads two per-metric reference levels from the cards and reports where the order rests on differences that are not interpretable. Both checks read the raw scores, before any normalization or weighting. They evaluate the ranking; they do not change it.

## Chance baseline

`semantics.score_of_random_baseline` is the score a random method reaches on a metric, in native units. The Adjusted Rand Index (ARI) declares 0, because it is corrected for chance. `beam.mcda.beats_random_baseline` counts, per metric, how many tools score better than that level. The direction follows the polarity: a `higher_is_better` metric beats chance above the baseline, a `lower_is_better` metric below it. A `target_value` metric has no chance level and is skipped.

The report names the tools that beat chance on no metric that declares a baseline. On the evidence given, those tools are not distinguishable from a random method, whatever their rank in the table. A NaN score counts as unobserved, not as a failure to beat chance, so a tool with no observed score on any baselined metric is left out of that list.

## Noise floor

`comparability.noise_floor` is the smallest difference in native units that is interpretable on a metric. Differences below it are measurement noise. The ARI card declares 0.01 as a placeholder default, not a measured value. A real value for a metric comes from a reproducibility study.

`beam.mcda.noise_floor_separation` compares every pair of tools. A pair is separated when at least one metric tells them apart by its noise floor or more. A pair that has observed scores on a floored metric but reaches no floor on any metric is recorded as indistinguishable: the metric set cannot tell those two tools apart. When the ranking is available, the report flags whether the two top-ranked tools are indistinguishable, in which case the order between them is within noise.

## Why the two belong together

Both checks read a raw score against a declared reference value, and both inform the same caution as the smallest-weight-perturbation analysis. The perturbation analysis already finds the smallest weight change that flips the top pair. The noise floor adds the prior question: are the top tools far enough apart to rank at all? The chance baseline adds another: do they beat a random method in the first place? A flip that is fragile under weights, between two tools that are within the noise floor and barely beat chance, is not a real result.

## How to populate the fields

Both fields are optional and additive. Set `semantics.score_of_random_baseline` only where a metric has a defined chance level (corrected-for-chance metrics such as ARI, or a balanced-class accuracy at 1 over the number of classes). Set `comparability.noise_floor` only where a reproducibility figure exists. A card that declares neither is simply absent from both reports, and the report sections are drawn only when at least one metric declares the matching field.

## Limitations

The chance baseline is exact only where a metric has a clean analytical chance level. The normalized mutual information (NMI) of random clusterings depends on the partition entropies and has no single scalar baseline, so its card leaves the field empty. The noise floor is a single scalar per metric and does not vary with dataset size or class balance, so it is a coarse threshold, not a per-cell standard error. For a tensor input, beam applies the native-unit floor to the per-tool scores after the cross-dataset reduction, which is an approximation when the reduction is not a plain mean.

## See also

- [Pairwise superiority](pairwise-superiority.md)
- [Bayesian comparison](bayesian-comparison.md)
