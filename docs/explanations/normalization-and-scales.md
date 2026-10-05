# Normalization and measurement scales

The multi-criteria decision analysis (MCDA) procedure rescales every metric to the unit interval before it [weights](weighting-schemes.md) and [aggregates](aggregation-methods.md). The default is min-max scaling, and whether it fits depends on the metric's [measurement scale](measurement-theory.md).

## Min-max

Min-max scaling maps the smallest value in a column to 0 and the largest to 1. It is simple and it keeps the order of the methods. It has three failure modes that matter for benchmarks.

1. One outlier sets the scale. Runtime and peak memory span orders of magnitude. If one method is a hundred times slower than the rest, it sets the top of the range, and every other method maps to a value near the same end. The speed differences among the fast methods then disappear, and the ranking then depends on whichever metric still has spread.
2. A meaningful zero is lost. The Adjusted Rand Index is corrected for chance, so a value of 0 means no better than random. Min-max against the declared range of -1 to 1 maps that 0 to 0.5, halfway to the top of the range. A method scoring at chance then looks average, and it can outrank a method with a modestly higher raw score once a second metric enters the sum.
3. An empirical bound is not stable. Runtime has no upper limit, so min-max uses the largest observed value as the top of the scale. Add a new method to the table and the scale shifts, which changes the normalized score of every method already there. A leaderboard that grows over time is not comparable from one version to the next.

## Measurement theory

Two of Stevens' four measurement scales matter for benchmarking.

- An interval scale has a zero by convention; differences are comparable and ratios are not. The Adjusted Rand Index and the silhouette coefficient are interval. An affine transform, $a x + b$, keeps its meaning.
- A ratio scale has a true zero and ratios are meaningful. Runtime and peak memory are ratio. Only multiplication by a positive constant keeps its meaning.

Min-max subtracts the minimum, an affine transform with an offset, so on a ratio metric it moves the true zero. For averages across datasets, only the geometric mean is meaningful for ratio data (Smith 1988).

Runtime and peak memory list `affine` among their allowed transforms: a change of unit is valid, and min-max stays available. Their cards default to a ratio-preserving normalization.

## The six strategies

Each metric card declares `comparability.recommended_normalization`, which the pipeline applies to that column.

- `min_max` is the default, for bounded metrics whose declared range is the scale, such as normalized mutual information (NMI) in 0 to 1.
- `log_min_max` takes the logarithm first, then min-max. It keeps the multiplicative structure of a ratio metric, so a single slow method no longer compresses the others. Runtime and peak memory use it. It needs strictly positive values.
- `rank` maps the position in the column to the unit interval. It drops the size of the gaps, resists outliers and makes no scale assumption.
- `zscore` standardizes the column and passes it through the logistic function, so the result stays in the open unit interval. The mean method maps to 0.5 and an outlier is compressed smoothly, so it does not set the scale.
- `baseline_relative` rescales against a declared chance score, so a method at chance maps to 0. The Adjusted Rand Index uses it, with a [chance baseline](reference-levels.md) of 0. It is defined for higher-is-better metrics.
- `target_relative` is for a metric whose ideal is a fixed value, such as a calibration slope of 1. It min-max scales the absolute deviation from `semantics.target` with flipped polarity: the method nearest the target maps to 1 and the farthest to 0.

A `polarity: target_value` column must use `target_relative`, and `target_relative` refuses a monotone polarity. Like min-max, it is relative to the methods in the table. It is the distance-to-a-reference normalization of the OECD handbook.

## Checks

For a min-max column the pipeline warns when a declared bound is missing or the column is heavy-tailed, and the warning suggests `log_min_max` or `rank`. The run continues. The [card and data consistency](card-data-consistency.md) audit makes the same checks over every metric.

## Examples

`beam.scenarios` has two cases. With a runtime outlier, min-max ranks a slower method first and `log_min_max` the fastest. With a method at chance, min-max ranks it above one with a higher raw score and `baseline_relative` does not.

## See also

- [Choice agreement](choice-agreement.md#normalization-agreement)
- [Weighting schemes](weighting-schemes.md)
- [Aggregation methods](aggregation-methods.md)

## References

- Stevens, S. S. On the theory of scales of measurement. Science (1946). DOI [10.1126/science.103.2684.677](https://doi.org/10.1126/science.103.2684.677).
- Smith, J. E. Characterizing computer performance with a single number. Communications of the ACM (1988). DOI [10.1145/63039.63043](https://doi.org/10.1145/63039.63043).
- OECD. Handbook on Constructing Composite Indicators (2008), on the choice of normalization method. DOI [10.1787/9789264043466-en](https://doi.org/10.1787/9789264043466-en).
- Van Calster, B., McLernon, D. J., van Smeden, M., Wynants, L., Steyerberg, E. W. Calibration: the Achilles heel of predictive analytics. BMC Medicine (2019), on the calibration slope and its ideal value of 1. DOI [10.1186/s12916-019-1466-7](https://doi.org/10.1186/s12916-019-1466-7).
