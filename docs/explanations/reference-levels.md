# Reference levels: chance baseline and noise floor

A ranking always produces an order, even when the scores behind it are at chance level. beam reads two per-metric reference levels from the metric cards and reports where the order is based on uninterpretable differences. Both read the raw scores, before any [normalization](normalization-and-scales.md) or [weighting](weighting-schemes.md), and do not change the ranking.

## Chance baseline

`semantics.score_of_random_baseline` is the score a random method reaches on a metric, in native units. The Adjusted Rand Index (ARI) declares 0, because it is corrected for chance. [`beam.mcda.beats_random_baseline`](../reference/beats_random_baseline.qmd) counts, per metric, how many tools score better than that level. The direction follows the polarity: a `higher_is_better` metric beats chance above the baseline, a `lower_is_better` metric below it. A `target_value` metric has no chance level and is skipped.

The report lists the tools at or below chance on every metric with a declared baseline; whatever their rank, they are not distinguishable from a random method. A NaN score counts as unobserved, so a tool with no observed score on any baselined metric is left out of that list.

## Noise floor

`comparability.noise_floor` is the smallest interpretable difference on a metric, in native units. Differences below it are measurement noise. The ARI card declares 0.01 as a placeholder default. A measured value for a metric would come from a reproducibility study.

[`beam.mcda.noise_floor_separation`](../reference/noise_floor_separation.qmd) compares every pair of tools. A pair is separated when at least one metric distinguishes them by its noise floor or more. A pair with observed scores on a floored metric but no difference at or above the floor on any metric is recorded as indistinguishable: the metric set does not separate those two tools. When the ranking is available, the report flags whether the two top-ranked tools are indistinguishable, in which case the order between them is within noise.

## Usage

Both add to the [smallest-weight-perturbation analysis](rank-sensitivity.md), which finds the smallest weight change reversing the top pair. The noise floor shows whether the top tools are far enough apart to rank at all, the chance baseline whether they beat a random method. A flip that is fragile under weights, between two tools within the noise floor and barely above chance, is not interpretable.

Both fields are optional and independent of each other. `semantics.score_of_random_baseline` applies only to a metric with a defined chance level (corrected-for-chance metrics such as ARI, or a balanced-class accuracy at 1 over the number of classes). `comparability.noise_floor` applies when a measured value exists. If neither is defined on the metric card, beam reports no reference-level diagnostics.

## Limitations

The chance baseline is exact only for a metric with a well-defined chance level. For instance, the normalized mutual information (NMI) of random clusterings depends on the partition entropies and has no single scalar baseline, so its card leaves the field empty. 

## See also

- [Pairwise superiority](pairwise-method-comparison.md)
- [Bayesian comparison](pairwise-method-comparison.md#bayesian-sign-comparison)
