# Measurement theory in beam

Every metric card declares a `scale_type` and a `polarity`.

## Stevens scales

Stevens (1946) orders four measurement scales by the operations they allow:

- Nominal: labels without order, such as a cell type. Only equality is meaningful.
- Ordinal: ordered labels, such as ranks. Comparison is meaningful; differences and ratios are not.
- Interval: numeric, with a unit but no true zero, such as temperature in Celsius. Differences are meaningful; ratios are not.
- Ratio: numeric, with a unit and a true zero, such as runtime in seconds. Ratios are meaningful.

The Adjusted Rand Index (ARI) is interval: its zero is chance-corrected agreement, but its unit depends on the partition pair. Runtime is ratio.

## Relevance in benchmarking

[Multi-criteria decision analysis](aggregation-methods.md) combines the metrics into one ranking, and not every operation is allowed on every scale:

- Arithmetic mean: interval and ratio scales.
- Geometric mean: ratio scales with positive values.
- Rank aggregation (Borda, Copeland): any ordered scale.
- [Min-max normalization](normalization-and-scales.md): at least interval.

Velleman and Wilkinson (1993) argue against a rigid use of the Stevens scales. Each card has a free-text `scale_rationale` for such cases. The polarity (`higher_is_better`, `lower_is_better`, `target_value`) orients normalization and ranking.

## References

- Stevens, S. S. (1946). On the theory of scales of measurement. Science, 103(2684), 677-680. DOI [10.1126/science.103.2684.677](https://doi.org/10.1126/science.103.2684.677).
- Velleman, P. F., and Wilkinson, L. (1993). Nominal, ordinal, interval, and ratio typologies are misleading. The American Statistician, 47(1), 65-72. DOI [10.1080/00031305.1993.10475938](https://doi.org/10.1080/00031305.1993.10475938).
