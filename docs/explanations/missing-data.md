# Missing data in benchmark scores

Benchmark tables have gaps. A method crashes on one dataset, times out on another, does not accept a given input shape, or was never run for one metric. beam has to decide what a gap means before it ranks, and by default it does not impute.



Any filler for a missing value (the column mean, a zero, the scale midpoint) is a value the method never generated, and it changes the ranking: the mean pulls a score toward average, a zero treats a crash as the worst result, the midpoint flatters a method that did not run. Which one is right depends on the benchmark, so beam will not pick one without asking. A missing value often means the method could not run, so counting it as the worst outcome is reasonable.

Data can be missing in two places, and beam handles them differently.

## Missing datasets

Most missing data are at the dataset level. A method ran on eight of ten datasets for a metric. beam summarizes that method over the eight datasets where it ran, using the per-metric rule on the metric card (arithmetic mean, geometric mean, or median). This is an available-case summary from the runs that exist, not imputation: no missing value is filled.

`beam.mcda.reduce_tensor` runs first, before any ranking. A method that ran on no dataset at all for a metric has zero coverage, and there is nothing to summarize. By default that raises. If you want the leftover gap handled by a policy instead, `reduce_tensor(..., on_zero_coverage="nan")` leaves the cell missing for the tool by metric step below.

## Choosing a policy

Once the datasets are summarized, what remains is a tool by metric matrix that may still have holes (a method with zero coverage on a metric, or a wide table that came with blanks). Here beam asks you to choose, through the `missing` argument on `beam.rank`, `run`, the CLI `beam rank --on-missing`, and the `missing` key in beam.yaml. The default is `error`.

`error` refuses any missing cell and names the alternatives. This is the default because a recommendation must not rest on a choice you did not make.

`available` is available-case ranking with simple additive weighting. Each tool is scored on the metrics it was measured on, with the weights renormalized over that tool's observed metrics. The composites then rest on different metric sets across tools, so the result carries a warning. Only SAW supports this, because its composite is a sum you can take over a subset of metrics. [TOPSIS, VIKOR, PROMETHEE II](aggregation-methods.md) and [COMET](aggregation-methods.md#comet) cannot: they each need every tool placed on every criterion to define an ideal point, a pairwise comparison, or a fuzzy membership. The objective [weight schemes](weighting-schemes.md) (entropy, standard deviation, CRITIC, MEREC) measure the spread of a metric across the tools, which needs a complete column. So under `available` these methods and weightings refuse and point you to a policy that completes the matrix or to a per-subset analysis.

`worst` is the explicit decision that a missing cell means the method did not run and should count as the worst outcome. After normalization each gap is set to 0, the worst score on the higher-is-better scale, the matrix is complete, and every method runs. Many benchmarkers prefer this: a tool that fails to run ranks lower than one that runs and scores poorly. It is a statement about the benchmark, not a guess at an unknown value, and beam records it in a warning.

`impute` fills each gap with the per-metric mean of the observed normalized scores. It is discouraged and never a default, and it warns that it fabricates values and biases the ranking toward the column mean.

## The critical-difference test

The [Friedman test and its Nemenyi post-hoc](critical-difference.md) rank the methods within each dataset, which is only defined over a complete column. beam does not drop or fill the missing cells to force a complete table, and suggests restricting the diagram to the complete cases. The missing-data generalization of the Friedman test is the [Skillings-Mack (1981) test](critical-difference.md#skillings-mack-for-incomplete-blocks), available as [`beam.mcda.skillings_mack`](../reference/skillings_mack.qmd).

## No silent filling

beam never fills a gap by default, and never without a warning. A missing value is imputed only under the explicit `worst` and `impute` policies, both of which the user chooses by name and both of which warn. Everywhere else, a missing cell is summarized across datasets, carried through untouched by normalization, or refused with a warning.

## See also

- [Normalization and scales](normalization-and-scales.md)

## References

- Skillings, J. H., Mack, G. A.. On the use of a Friedman-type statistic in balanced and unbalanced block designs. Technometrics (1981). DOI [10.1080/00401706.1981.10486261](https://doi.org/10.1080/00401706.1981.10486261).
