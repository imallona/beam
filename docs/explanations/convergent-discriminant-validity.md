# Convergent and discriminant validity of a metric set

A benchmark scores every method on several metrics, and the metrics are usually grouped. The scIB integration score groups its metrics into biological conservation and batch correction and weights the two groups 0.6 and 0.4. The grouping carries an assumption: the metrics in one group measure the same thing, and the metrics in different groups measure different things. `beam.mcda.metric_validity` tests that assumption against the scores, following Campbell and Fiske (1959).

## What it computes

Each method-by-dataset cell is one observation, and the metrics are the variables. The function orients every metric so that higher means better, reading the polarity from the cards and negating a lower-is-better metric. It then computes the Spearman rank correlation between every pair of metrics over the observations they share.

Spearman, a rank correlation, is the right tool here. The metrics live on different scales, and the question is whether two metrics order the methods the same way, not whether their raw values track on a line. The correlation is pairwise-complete: each pair is computed on the cells where both metrics are observed, so a sparse benchmark is not thrown away. A coverage matrix records how many observations sit behind each correlation, and a pair with too few shared observations is left as NaN.

## Convergent and discriminant evidence

The analyst supplies a construct label per metric. This is a domain judgement, so beam takes it as an argument rather than reading it from the cards. Grouping the correlations by that label splits them in two.

Within-group correlations are the convergent evidence. Metrics that claim to measure one construct should agree with each other. Between-group correlations are the discriminant evidence. Metrics that claim to measure different constructs should agree less. When the mean within-group correlation is higher than the mean between-group correlation, the grouping holds up, and treating the groups as separate criteria in the weighting is supported by the data rather than asserted. `discriminant_ok` records that comparison.

## Two flags

The report names two kinds of problem metric.

A redundant pair is two metrics in the same group whose correlation is at or above a threshold (0.9 by default). They order the methods almost identically, so carrying both adds little and double-counts one construct. One is a candidate to drop.

A crossloading metric correlates more, on average, with another group than with its own. It behaves more like a different construct than the one its label claims. This is the per-metric form of a discriminant-validity failure, and it points at a metric that is mislabelled or genuinely ambiguous.

## What it does not do

This is the trait facet of a multitrait-multimethod matrix, not the full design. The full matrix also varies the method of measurement, holding the trait fixed, to separate true convergence from shared method artefact. beam records one measurement per metric per cell, so there is no separate method facet to vary. The diagnostic is the convergent and discriminant reading of the metric correlations, and the docs and the report do not claim more.

The result is descriptive of the methods and datasets in the input. A small benchmark gives a coarse correlation, and the grouping it tests is the analyst's, so the diagnostic informs that judgement rather than replacing it.

## How to read it on real data

On the OpenProblems batch integration scores, the bio/batch grouping is supported but weak: mean within-group correlation 0.38 against mean between-group correlation 0.30. The biological metrics agree more among themselves (0.45) than the batch metrics do (0.24), and `graph_connectivity`, a batch metric, correlates more with the biological group than with its own. The reading is that the two axes are separable rather than cleanly distinct, so the 0.6/0.4 weighting is a softer modelling choice than a split of two independent things.

## References

- Campbell, D. T., Fiske, D. W.. Convergent and discriminant validation by the multitrait-multimethod matrix. Psychological Bulletin (1959). DOI [10.1037/h0046016](https://doi.org/10.1037/h0046016).
