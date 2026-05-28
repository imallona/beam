# Comparing methods across datasets: Friedman and Nemenyi

The MCDA composite gives one ranking of the methods. It does not say whether that ranking is real. If the methods are close and the datasets disagree, the order at the top can be an artifact of which datasets happened to be included. Demsar (2006) gives the standard answer for this setting: rank the methods on each dataset, then test the ranks. beam implements it in `beam.mcda.critical_difference`.

## What the test does

The input is a tool by dataset matrix for one metric or for an MCDA composite. On each dataset the methods are ranked, with 1 for the best. Each method then has an average rank across the datasets. The Friedman test asks whether these average ranks differ more than chance would produce if all methods were equivalent. A small p-value means at least one method is consistently ahead or behind.

The Friedman test does not say which methods differ from which. For that, beam runs the Nemenyi post-hoc. Its critical difference is the smallest gap between two average ranks that counts as significant at the chosen level. Two methods whose average ranks differ by less than the critical difference cannot be told apart from the data at hand.

## The critical difference

The Nemenyi critical difference is `q * sqrt(k (k + 1) / (6 N))`, where `k` is the number of methods, `N` the number of datasets, and `q` the Studentized range value for `k` at the chosen alpha, divided by the square root of two. beam computes `q` exactly with scipy, so it is correct for any number of methods, not only the small tables printed in the paper. As a check, for five methods at alpha 0.05 the `q` term is 2.728, the value in Demsar's Table 5.

The formula shows the two ways to earn power: more datasets shrink the critical difference, and fewer methods shrink it. With many methods and few datasets the critical difference is large, and most pairs come out unseparable. That is the honest reading, not a defect.

## Cliques

A critical-difference diagram draws the methods along a rank axis and connects the ones that are not significantly different. beam returns these groups as cliques: maximal runs of methods, consecutive in rank order, whose first and last average ranks lie within the critical difference. A method that shares no clique with another is significantly separated from it. The cliques are the data behind the diagram; the vignette draws the bars.

## How to use it

Call `critical_difference(scores, higher_is_better=True)` with a tool by dataset matrix. Set `higher_is_better=False` for a cost metric such as runtime, so the faster method still ranks near 1. The report carries the average ranks, the Friedman statistic and p-value, the critical difference, and the cliques.

The test needs at least three methods and at least two datasets. It adds to the MCDA composite rather than replacing it: the composite says which method to prefer under a stated weighting, and the Friedman-Nemenyi result says whether the data support drawing a line between the methods at all.

When the matrix has missing cells the Friedman ranks are no longer defined. The Skillings-Mack (1981) test generalizes the global statistic to incomplete blocks at the cost of the Nemenyi cliques; see [Skillings-Mack: coverage-aware Friedman](skillings-mack.md).

## A caveat

The Nemenyi post-hoc compares every pair of methods and is conservative. When the question is whether one new method beats a fixed set of baselines, comparing to a single control with the Bonferroni-Dunn correction has more power, as Demsar notes. beam currently implements the all-pairs Nemenyi case.

## References

- Demsar, J. Statistical comparisons of classifiers over multiple data sets. Journal of Machine Learning Research 7 (2006).
