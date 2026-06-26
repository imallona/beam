# Measurement theory in beam

This page explains two fields every metric card must declare: `scale_type` and `polarity`.

## Stevens scales

Stevens (1946) proposed a four-level taxonomy of measurement scales, ordered by which math operations are allowed on the values:

- Nominal: labels without order. Examples: cluster identifier, cell type. Only equality is meaningful. Means, distances, and ratios are not.
- Ordinal: ordered labels. Examples: Likert scale, ranks. Comparison is meaningful. Differences and ratios are not.
- Interval: numeric, with a meaningful unit but no meaningful zero. Example: temperature in Celsius. Differences are meaningful. Ratios are not, since twice the Celsius reading is not twice as hot.
- Ratio: numeric, with both a meaningful unit and a meaningful zero. Examples: runtime in seconds, peak memory in bytes. All four arithmetic operations are allowed.

A benchmark performance metric has a scale type. The Adjusted Rand Index (ARI) is at the interval level. It has a meaningful zero (chance-corrected agreement) but its unit length depends on the partition pair. Runtime is ratio: zero seconds means zero elapsed time, and a 10x speedup is meaningful.

## Relevance in benchmarking

When a benchmark reports many metrics for many methods, the next question is usually "which method ranks first, given my preferences over these metrics?". [Multi-criteria decision analysis](aggregation-methods.md) treats every metric as an axis and combines them into one ranking. Not every aggregation is allowed on every scale:

- Arithmetic mean: allowed on interval and ratio scales; meaningless on ordinal or nominal.
- Geometric mean: allowed only on ratio scales, and only for positive values.
- Rank aggregation (Borda, Copeland): allowed on any scale that supports ordering, including ordinal.
- [Min-max normalization](normalization-and-scales.md): produces values in [0, 1] but assumes the input is at least interval.

If a metric card hides its scale, beam cannot tell whether the chosen aggregation step is meaningful. Velleman and Wilkinson (1993) argue against treating Stevens scales as a rigid taxonomy in statistical practice. They are right that real metrics sit in fuzzy zones. beam takes a practical line: every card declares its scale type and a free-text `scale_rationale` where the author can explain corner cases. The polarity field (`higher_is_better`, `lower_is_better`, `target_value`) tells beam how to orient normalization and ranking.

## Reading

- Stevens, S. S. (1946). On the theory of scales of measurement. Science, 103(2684), 677-680. DOI [10.1126/science.103.2684.677](https://doi.org/10.1126/science.103.2684.677).
- Velleman, P. F., and Wilkinson, L. (1993). Nominal, ordinal, interval, and ratio typologies are misleading. The American Statistician, 47(1), 65-72. DOI [10.1080/00031305.1993.10475938](https://doi.org/10.1080/00031305.1993.10475938).
