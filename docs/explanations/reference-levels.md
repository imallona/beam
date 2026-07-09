# Reference levels: chance baseline and noise floor

A ranking always produces an order, even when the scores behind it are at chance level. beam reads two per-metric reference levels from the metric cards and reports where the order rests on differences that are not interpretable. Both checks read the raw scores, before any [normalization](normalization-and-scales.md) or [weighting](weighting-schemes.md). They evaluate the ranking without changing it.

## Chance baseline

`semantics.score_of_random_baseline` is the score a random method reaches on a metric, in native units. The Adjusted Rand Index (ARI) declares 0, because it is corrected for chance. [`beam.mcda.beats_random_baseline`](../reference/beats_random_baseline.qmd) counts, per metric, how many tools score better than that level. The direction follows the polarity: a `higher_is_better` metric beats chance above the baseline, a `lower_is_better` metric below it. A `target_value` metric has no chance level and is skipped.

The report names the tools that beat chance on no metric that declares a baseline. On the evidence given, those tools are not distinguishable from a random method, whatever their rank in the table. A NaN score counts as unobserved, not as a failure to beat chance, so a tool with no observed score on any baselined metric is left out of that list.

## Noise floor

`comparability.noise_floor` is the smallest difference in native units that is interpretable on a metric. Differences below it are measurement noise. The ARI card declares 0.01 as a placeholder default, not a measured value. A measured value for a metric comes from a reproducibility study.

[`beam.mcda.noise_floor_separation`](../reference/noise_floor_separation.qmd) compares every pair of tools. A pair is separated when at least one metric distinguishes them by its noise floor or more. A pair that has observed scores on a floored metric but reaches no floor on any metric is recorded as indistinguishable: the metric set cannot tell those two tools apart. When the ranking is available, the report flags whether the two top-ranked tools are indistinguishable, in which case the order between them is within noise.

## Usage

Both checks read a raw score against a declared reference value, and both inform the same caution as the [smallest-weight-perturbation analysis](rank-sensitivity.md). The perturbation analysis already finds the smallest weight change that flips the top pair. The noise floor adds the prior question: are the top tools far enough apart to rank at all? The chance baseline adds another: do they beat a random method in the first place? A flip that is fragile under weights, between two tools that are within the noise floor and barely above chance, is not interpretable.

Both fields are optional and additive. Set `semantics.score_of_random_baseline` only where a metric has a defined chance level (corrected-for-chance metrics such as ARI, or a balanced-class accuracy at 1 over the number of classes). Set `comparability.noise_floor` when existing. If neither are defined on the metric card beam does not report reference-levels-related diagnostics.

## Limitations

The chance baseline is exact only where a metric has a well-defined chance level. This is not trivial to get. For instance, the normalized mutual information (NMI) of random clusterings depends on the partition entropies and has no single scalar baseline, so its card leaves the field empty. 

## See also

- [Pairwise superiority](pairwise-method-comparison.md)
- [Bayesian comparison](pairwise-method-comparison.md#bayesian-sign-comparison)
