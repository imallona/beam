# Normalization and measurement scales

The MCDA pipeline rescales every metric to the unit interval before it weights and aggregates. The default way to do this is min-max scaling. This page explains where min-max goes wrong, why the right choice depends on the measurement scale of the metric, and how each metric card picks a normalization that fits.

## Why min-max is the default, and where it fails

Min-max scaling maps the smallest value in a column to 0 and the largest to 1. It is simple and it keeps the order of the methods. It has three failure modes that matter for benchmarks.

First, one outlier sets the scale. Runtime and peak memory span orders of magnitude. If one method is a hundred times slower than the rest, it defines the top of the range, and every other method maps to a value near the same end. The real speed differences among the good methods then disappear, and the ranking turns on whichever metric still has spread.

Second, a meaningful zero is lost. The Adjusted Rand Index is corrected for chance, so a value of 0 means no better than random. Min-max against the declared range of -1 to 1 maps that 0 to 0.5, half way to the best possible score. A method that learned nothing then looks average, and it can outrank a method that is genuinely, if modestly, better once a second metric enters the sum.

Third, an empirical bound is not stable. Runtime has no upper limit, so min-max uses the largest observed value as the top of the scale. Add a new method to the table and the scale shifts, which changes the normalized score of every method already there. A leaderboard that grows over time is not comparable from one version to the next.

## The scale of a metric decides what is allowed

Stevens described four measurement scales. Two of them matter here.

An interval scale has a meaningful zero only by convention, and equal differences are comparable but ratios are not. The Adjusted Rand Index and the silhouette coefficient are interval. An affine transform, of the form a times x plus b, preserves the meaning of an interval scale.

A ratio scale has a true zero and ratios are meaningful: twice as long is twice as long. Runtime and peak memory are ratio. Only a similarity transform, multiplication by a positive constant, preserves the meaning of a ratio scale. Adding a constant moves the zero and breaks it.

Min-max subtracts the minimum, so it is an affine transform with a nonzero offset. On an interval metric that is fine. On a ratio metric it moves the true zero, which is the formal reason min-max can mislead on runtime and memory. Smith (1988) makes the matching point for averaging across datasets: only the geometric mean is meaningful for ratio data.

## A note on the affine flag

Each metric card lists the transforms that are allowed on it. Runtime and peak memory list `affine` among them. Strictly, a pure ratio scale admits only multiplication by a positive constant, not the full affine family, so one could argue `affine` overstates what is meaning-preserving on these cards. We keep `affine` on the cards for two reasons. It records that a unit change, such as seconds to milliseconds, is a sensible operation, and removing it would block anyone who deliberately chooses min-max for a ratio metric. Instead of forbidding min-max on ratio metrics, the card steers the pipeline to a better default, and the guard warns when min-max is used on a heavy-tailed column. The decision stays with the analyst, and the card makes the safe choice the easy one.

## The five strategies

Each metric card declares `comparability.recommended_normalization`. The pipeline reads it and rescales that column accordingly.

- `min_max` is the default. Use it for bounded metrics whose declared range is the natural scale, such as NMI in 0 to 1.
- `log_min_max` takes the logarithm first, then min-max. It keeps the multiplicative structure of a ratio metric, so a single slow method no longer compresses the others. Runtime and peak memory use it. It needs strictly positive values.
- `rank` maps the position within the column to the unit interval. It drops the size of the gaps between methods but is immune to outliers and free of any scale assumption.
- `zscore` standardizes the column and passes it through the logistic function, so the result stays in the open unit interval. The mean method maps to 0.5 and an outlier is compressed smoothly rather than setting the scale.
- `baseline_relative` rescales relative to a declared chance score. A method no better than chance maps to 0 instead of the column midpoint. The Adjusted Rand Index uses it, with a chance baseline of 0. It is defined for higher-is-better metrics.

## The guard

The pipeline runs a check after it picks the strategies. For any column that still uses min-max, it warns in two cases: when a declared bound is missing, so the scale rests on the data and is not stable across method sets, and when the column is heavy-tailed, so one outlier dominates the rescale. The warnings travel on the result and point at `log_min_max` or `rank`. They do not block the run.

## The failures as scenarios

The `beam.scenarios` module ships two cases that make the failure concrete. In the heavy-tail case, plain min-max ranks a slower method first because a runtime outlier hides the speed ladder, while `log_min_max` ranks the fastest good method first. In the chance-baseline case, plain min-max ranks a random-level method above a better one, while `baseline_relative` restores the correct order. Both are used as regression tests, so the contrast stays true as the code changes.

## References

- Stevens, S. S. On the theory of scales of measurement. Science (1946).
- Smith, J. E. Characterizing computer performance with a single number. Communications of the ACM (1988).
- OECD. Handbook on Constructing Composite Indicators (2008), on the choice of normalization method.
