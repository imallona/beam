# Normalization and measurement scales

The multi-criteria decision analysis (MCDA) procedure rescales every metric to the unit interval before it [weights](weighting-schemes.md) and [aggregates](aggregation-methods.md). The default is min-max scaling. This page explains where min-max goes wrong, why the choce depends on the [measurement scale](measurement-theory.md) of the metric, and how each metric card picks a normalization that fits.

## Min-max

Min-max scaling maps the smallest value in a column to 0 and the largest to 1. It is simple and it keeps the order of the methods. It has three failure modes that matter for benchmarks.

1. One outlier sets the scale. Runtime and peak memory span orders of magnitude. If one method is a hundred times slower than the rest, it sets the top of the range, and every other method maps to a value near the same end. The speed differences among the fast methods then disappear, and the ranking turns on whichever metric still has spread.
2. A meaningful zero is lost. The Adjusted Rand Index is corrected for chance, so a value of 0 means no better than random. Min-max against the declared range of -1 to 1 maps that 0 to 0.5, half way to the best possible score. A method scoring at chance then looks average, and it can outrank a method that is modestly better once a second metric enters the sum.
3. an empirical bound is not stable. Runtime has no upper limit, so min-max uses the largest observed value as the top of the scale. Add a new method to the table and the scale shifts, which changes the normalized score of every method already there. A leaderboard that grows over time is not comparable from one version to the next.

## Measurement theory

Stevens described four measurement scales. For benchmarking, we find two of them particularly relevant.

- An interval scale has a meaningful zero only by convention, and equal differences are comparable but ratios are not. The Adjusted Rand Index and the silhouette coefficient are interval. An affine transform, of the form $a x + b$, keeps the meaning of an interval scale.

- A ratio scale has a true zero and ratios are meaningful: twice as long is twice as long. Runtime and peak memory are ratio. Only a similarity transform, multiplication by a positive constant, keeps the meaning of a ratio scale. Adding a constant moves the zero and breaks it.

Min-max subtracts the minimum, so it is an affine transform with a nonzero offset. On an interval metric that is fine. On a ratio metric it moves the true zero, which is the formal reason min-max can mislead on runtime and memory. Smith (1988) makes the matching point for averaging across datasets: only the geometric mean is meaningful for ratio data.

## On affines

Each metric card lists the transforms allowed on it. Runtime and peak memory list `affine` among them. Strictly, a pure ratio scale allows only multiplication by a positive constant, not the full affine family, so one could argue `affine` overstates what is meaning-preserving on these cards. We keep `affine` on the cards for two reasons. It records that a unit change, such as seconds to milliseconds, is valid, and removing it would block anyone who picks min-max for a ratio metric on purpose. The card defaults to a normalization that keeps ratio structure, and the guard warns when min-max is used on a heavy-tailed column. The decision stays with the analyst.

## The six strategies

Each metric card declares `comparability.recommended_normalization`. The pipeline reads it and rescales that column accordingly.

- `min_max` is the default. Use it for bounded metrics whose declared range is the natural scale, such as normalized mutual information (NMI) in 0 to 1.
- `log_min_max` takes the logarithm first, then min-max. It keeps the multiplicative structure of a ratio metric, so a single slow method no longer compresses the others. Runtime and peak memory use it. It needs strictly positive values.
- `rank` maps the position within the column to the unit interval. It drops the size of the gaps between methods but resists outliers and makes no scale assumption.
- `zscore` standardizes the column and passes it through the logistic function, so the result stays in the open unit interval. The mean method maps to 0.5 and an outlier is compressed smoothly rather than setting the scale.
- `baseline_relative` rescales against a declared chance score. A method no better than chance maps to 0 instead of the column midpoint. The Adjusted Rand Index uses it, with a [chance baseline](reference-levels.md) of 0. It is defined for higher-is-better metrics.
- `target_relative` is for a metric whose ideal is a fixed value, not the highest or the lowest score. The calibration slope is the example: a value of 1 means the predicted risks match the target, below 1 means they are too extreme, above 1 means they are too moderate. The strategy takes the absolute deviation from the target and min-max scales it with flipped polarity, so the method nearest the target maps to 1 and the farthest to 0. It needs the card to declare `semantics.target`.

## Metrics whose ideal is a fixed point

The first five strategies all assume one direction is better: higher for the Adjusted Rand Index, lower for runtime. Some metrics break that assumption. A calibration slope of 1 is ideal, and a slope of 0.5 is as wrong as a slope of 2 is in the other direction. These carry `polarity: target_value` with a declared `target`, and the only strategy that fits them is `target_relative`. The pipeline enforces the pairing in both directions: a `target_value` column must use `target_relative`, and `target_relative` refuses a column that declares a monotone polarity, because there is no preferred direction for it to orient by.

The deviation-then-min-max form is the distance-to-a-reference normalization of the OECD composite-indicators handbook. It is relative to the observed method set, like plain min-max, so the same caution applies: the scale rests on the spread of the methods in the table, not on an absolute tolerance. A tolerance-based variant, dividing the deviation by an acceptable error declared on the card, is a later option once a metric needs it.

## Checks

The pipeline runs a check after it picks the strategies. For any column that still uses min-max, it warns in two cases: when a declared bound is missing, so the scale rests on the data and is not stable across method sets, and when the column is heavy-tailed, so one outlier sets the rescale. The warnings are attached to the result and name `log_min_max` or `rank`. They do not block the run. The standalone [card and data consistency](card-data-consistency.md) audit makes the same checks over every metric in one pass.

## Examples

The `beam.scenarios` module ships two cases that make the failure concrete. In the heavy-tail case, plain min-max ranks a slower method first because a runtime outlier hides the speed ladder, while `log_min_max` ranks the fastest method first. In the chance-baseline case, plain min-max ranks a random-level method above one with a higher raw score, while `baseline_relative` puts back the correct order. Both are used as regression tests, so the contrast stays true as the code changes.

## See also

- [Choice agreement](choice-agreement.md#normalization-agreement)
- [Weighting schemes](weighting-schemes.md)
- [Aggregation methods](aggregation-methods.md)

## References

- Stevens, S. S. On the theory of scales of measurement. Science (1946). DOI [10.1126/science.103.2684.677](https://doi.org/10.1126/science.103.2684.677).
- Smith, J. E. Characterizing computer performance with a single number. Communications of the ACM (1988). DOI [10.1145/63039.63043](https://doi.org/10.1145/63039.63043).
- OECD. Handbook on Constructing Composite Indicators (2008), on the choice of normalization method. DOI [10.1787/9789264043466-en](https://doi.org/10.1787/9789264043466-en).
- Van Calster, B., McLernon, D. J., van Smeden, M., Wynants, L., Steyerberg, E. W. Calibration: the Achilles heel of predictive analytics. BMC Medicine (2019), on the calibration slope and its ideal value of 1. DOI [10.1186/s12916-019-1466-7](https://doi.org/10.1186/s12916-019-1466-7).
