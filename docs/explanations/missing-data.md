# Missing data in benchmark scores

A method crashes on one dataset, times out on another, or was not run for one metric. beam does not impute by default: the column mean, a zero or the scale midpoint are values the method did not produce, and each changes the ranking differently.

## Missing datasets

A method that ran on eight of ten datasets for a metric is summarized over those eight, with the rule on the metric card (arithmetic mean, geometric mean, or median). No value is filled.

`beam.mcda.reduce_tensor` does this before ranking. A method with no dataset for a metric raises; `reduce_tensor(..., on_zero_coverage="nan")` leaves the cell missing for the next step.

## Policy

The tool by metric matrix can still have missing cells. The `missing` argument of `beam.rank` and `run`, the CLI `beam rank --on-missing`, and the `missing` key in beam.yaml set the policy. The default is `error`.

`error` refuses any missing cell and names the alternatives.

`available` ranks each tool on the metrics it has, with the weights renormalized over them, and warns that the composites use different metric sets. Only SAW supports it. [TOPSIS, VIKOR, PROMETHEE II](aggregation-methods.md) and [COMET](aggregation-methods.md#comet) need every tool on every criterion, and the objective [weight schemes](weighting-schemes.md) (entropy, standard deviation, CRITIC, MEREC) need complete columns.

`worst` sets each missing cell to 0 after normalization, the worst score, and warns. It suits a method that could not run.

`impute` fills each missing cell with the per-metric mean of the observed normalized scores and warns. It biases the ranking toward the column mean.

## Critical difference

The [Friedman test and its Nemenyi post-hoc](critical-difference.md) need a complete matrix; beam restricts them to the complete cases. The [Skillings-Mack (1981) test](critical-difference.md#skillings-mack-for-incomplete-blocks), [`beam.mcda.skillings_mack`](../reference/skillings_mack.qmd), takes an incomplete one.

## See also

- [Normalization and scales](normalization-and-scales.md)

## References

- Skillings, J. H., Mack, G. A. On the use of a Friedman-type statistic in balanced and unbalanced block designs. Technometrics (1981). DOI [10.1080/00401706.1981.10486261](https://doi.org/10.1080/00401706.1981.10486261).
