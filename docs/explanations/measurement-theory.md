# Measurement theory in beam

This is the why behind two fields every metric card must declare:
`scale_type` and `polarity`.

## Stevens scales

Stevens (1946) proposed a four-level taxonomy of measurement scales,
ordered by which mathematical operations are licit on the values:

- Nominal: labels without order. Examples: cluster identifier, cell type.
  Only equality is meaningful. Means, distances, and ratios are not.
- Ordinal: ordered labels. Examples: Likert scale, ranks. Comparison is
  meaningful. Differences and ratios are not.
- Interval: numeric, with a meaningful unit but no meaningful zero.
  Example: temperature in Celsius. Differences are meaningful. Ratios are
  not, since twice the Celsius reading is not twice as hot.
- Ratio: numeric, with both a meaningful unit and a meaningful zero.
  Examples: runtime in seconds, peak memory in bytes. All four arithmetic
  operations are licit.

A benchmark performance metric has a scale type. ARI sits at the interval
level: it has a meaningful zero (the chance-corrected value of zero
agreement) but its unit length depends on the partition pair. Runtime is
ratio: zero seconds means zero elapsed time, and a 10x speedup is
meaningful.

## Why beam asks for this

When a benchmark reports many metrics for many methods, the downstream
question is usually "which method is best, given my preferences over
these metrics?" Multi-criteria decision analysis treats every metric as
an axis and combines them into a single ranking. But not every
aggregation is licit on every scale:

- Arithmetic mean: licit on interval and ratio scales; meaningless on
  ordinal or nominal.
- Geometric mean: licit only on ratio scales, and only for positive
  values.
- Rank aggregation (Borda, Copeland): licit on any scale that supports
  ordering, including ordinal.
- Min-max normalisation: produces values in [0, 1] but assumes the input
  is at least interval.

If a metric card hides its scale, beam cannot tell whether the chosen
aggregation step is meaningful. Velleman and Wilkinson (1993) push back
against treating Stevens scales as a rigid taxonomy in statistical
practice, and they are right that real metrics sit in fuzzy zones. beam
takes a pragmatic line: every card declares its scale type plus a
free-text `scale_rationale` field where the author can explain corner
cases. The polarity field (`higher_is_better`, `lower_is_better`,
`target_value`) then tells beam how to orient normalisation and ranking.

## Reading

- Stevens, S. S. (1946). On the theory of scales of measurement.
  Science, 103(2684), 677-680.
- Velleman, P. F., and Wilkinson, L. (1993). Nominal, ordinal, interval,
  and ratio typologies are misleading. The American Statistician, 47(1),
  65-72.
