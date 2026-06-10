# Internal-consistency reliability of a metric group

A benchmark often treats a group of metrics as one criterion. The scIB integration score groups its metrics into biological conservation and batch correction and weights the two groups 0.6 and 0.4, so each group is read as a single composite scale. The [convergent and discriminant validity](convergent-discriminant-validity.md) check asks whether that grouping is the right split. Reliability asks the next question: if a group is going to be read as one scale, how consistently do its metrics measure one thing? `beam.mcda.metric_reliability` answers it with standardized Cronbach's alpha, following Cronbach (1951).

## What it computes

Each method-by-dataset cell is one observation, and the metrics are the variables. The function orients every metric so that higher means better, reading the polarity from the cards, then computes the Spearman rank correlation between every pair of metrics over the observations they share. This is the same orientation and correlation step the validity check uses, so the two diagnostics rest on the same numbers.

For each group the report gives the standardized alpha

    alpha = k * r_bar / (1 + (k - 1) * r_bar)

where `k` is the number of metrics in the group and `r_bar` is their mean inter-item correlation. The standardized form, built from correlations rather than from raw covariances, is the right choice here because the metrics live on different scales. It is the rank-based analogue of classical alpha, in line with the way the rest of beam compares metrics by rank.

## Reading the value

Alpha runs up to 1. A common rule of thumb treats 0.7 as the point above which a group reads as one reliable scale, and `metric_reliability` flags any group below that cutoff. The cutoff is a convention, not a law, so the report carries `r_bar` and `k` next to each alpha rather than only the verdict.

The two inputs matter separately. Alpha rises with the mean correlation and with the number of metrics, so a long group can reach a high alpha on modest agreement, and a short group needs stronger agreement to clear the same bar. When two groups differ in size, the mean inter-item correlation is the cleaner comparison, because it does not carry the size effect.

## Alpha if a metric is dropped

For a group of three or more metrics, the report recomputes the group's alpha with each metric removed in turn. A metric whose removal raises the group's alpha is pulling against the rest of the group: it agrees with its labelled construct less than the others do. This is the per-metric handle on a low group alpha. It points at the metric to question first, whether to relabel it, drop it, or treat it as a separate criterion.

A metric in a group of two has no alpha-if-dropped entry, because dropping one leaves a single metric and alpha is undefined for one item.

## What it does not do

Alpha assumes the group is one reflective factor, a single underlying quantity that each metric reads with noise. A low alpha is evidence against that assumption, not a measurement of which metric is wrong; the alpha-if-dropped diagnostic narrows that down but does not settle it. Alpha is also not a validity check. A group can be reliable and still measure the wrong thing, which is why reliability reads alongside the convergent and discriminant validity rather than instead of it.

The result is descriptive of the methods and datasets in the input. A small benchmark gives a coarse estimate, and the grouping it scores is the analyst's, so the diagnostic informs that judgement rather than replacing it.

## How to read it on real data

On the OpenProblems batch integration scores, with the same bio/batch grouping the validity check uses, the biological group reads as one reliable scale: alpha 0.85 over seven metrics, mean inter-item correlation 0.45. The batch group does not clear the cutoff: alpha 0.62 over five metrics, mean inter-item correlation 0.24, the one group flagged as low reliability. Dropping `pcr` is the only batch removal that raises the batch alpha by more than a rounding step, from 0.62 to 0.67, so `pcr` is the batch metric least consistent with the rest of its group. The reading pairs with the validity finding: the bio/batch axis is the right split, and the biological side of it is a coherent scale while the batch side is a looser collection.

## References

- Cronbach, L. J.. Coefficient alpha and the internal structure of tests. Psychometrika (1951). DOI [10.1007/BF02310555](https://doi.org/10.1007/BF02310555).
