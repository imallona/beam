# Critical difference: Friedman, Nemenyi, Skillings-Mack

The [multi-criteria decision analysis (MCDA) aggregation](aggregation-methods.md) builds a metric composite to give a rank and consolidated score to each method. It does not say whether that ranking is real. If the methods are close and the influence of the datasets is large, the order at the top can be an artifact of which datasets happened to be included. Demsar (2006) gives the standard answer for this setting: rank the methods on each dataset, then test the ranks. beam implements it in [`beam.mcda.critical_difference`](../reference/critical_difference.qmd).

## Implementation

The input is a tool by dataset matrix for one metric or for an MCDA composite. On each dataset the methods are ranked, with 1 for the best. Each method then has an average rank across the datasets. The Friedman test asks whether these average ranks differ more than chance would produce if all methods were equivalent. A small p-value means at least one method is consistently ahead or behind.

The Friedman test does not say which methods differ from which. For that, beam runs the Nemenyi post-hoc. Its critical difference is the smallest gap between two average ranks that counts as significant at the chosen level. Two methods whose average ranks differ by less than the critical difference cannot be told apart from the data at hand.

## The critical difference

The Nemenyi critical difference is $q \sqrt{k (k + 1) / (6 N)}$, where $k$ is the number of methods, $N$ the number of datasets, and $q$ the Studentized range value for $k$ at the chosen alpha, divided by the square root of two. beam computes $q$ exactly with scipy, so it is correct for any number of methods, not only the small tables printed in the paper. As a check, for five methods at alpha 0.05 the $q$ term is 2.728, the value in Demsar's Table 5.

More datasets shrink the critical difference, and fewer methods shrink it; with many methods and few datasets it is large, and most pairs come out unseparable.

## Cliques

A critical-difference diagram draws the methods along a rank axis and connects the ones that are not significantly different. beam returns these groups as cliques: maximal runs of methods, consecutive in rank order, whose first and last average ranks lie within the critical difference. A method that shares no clique with another is significantly separated from it.

## How to use it

Call `critical_difference(scores, higher_is_better=True)` with a tool by dataset matrix. Set `higher_is_better=False` for a cost metric such as runtime, so the faster method still ranks near 1. The report carries the average ranks, the Friedman statistic and p-value, the critical difference, and the cliques.

The test needs at least three methods and at least two datasets. It adds to the MCDA composite rather than replacing it: the composite says which method to prefer under a stated [weighting](weighting-schemes.md), and the Friedman-Nemenyi result says whether the data support drawing a line between the methods at all.

When the matrix has missing cells the Friedman ranks are no longer defined. The Skillings-Mack (1981) test generalizes the global statistic to incomplete blocks at the cost of the Nemenyi cliques, covered below.

## Skillings-Mack for incomplete blocks

Real benchmarks rarely give a complete matrix: methods time out, error on an input, or were not run on every dataset. beam's [missing-data policy](missing-data.md) does not fill those gaps by imputation, so `critical_difference` reduces the matrix to its complete observations, and on a wide table with many partial methods there may be none. The Skillings-Mack (1981) test fills the gap with a Friedman-type statistic that does not need a complete matrix, in [`beam.mcda.skillings_mack`](../reference/skillings_mack.qmd) and under the alias [`beam.mcda.coverage_aware_critical_difference`](../reference/coverage_aware_critical_difference.qmd).

It answers the same global question, whether the methods are separable across the datasets, on the same tool by dataset matrix with NaN allowed. It gives no pairwise comparisons. The Nemenyi critical difference assumes every pair is ranked on every dataset with equal block sizes; with incomplete blocks the per-method average rank no longer shares a denominator, so beam returns the global test only and leaves pairwise statements to a `critical_difference` run on the complete cases.

Within each block (column) $j$ the methods present are ranked from 1 (lowest score) to $k_j$ (highest score), with average ranks for ties. The within-block rank for method $i$ is centred and standardized by the block size:

$$
A_{ij} = \left(R_{ij} - \frac{k_j + 1}{2}\right) \sqrt{\frac{12}{k_j + 1}}
$$

The factor $\sqrt{12 / (k_j + 1)}$ makes the variance of $A_{ij}$ under the null (the method's rank is uniform over $1, \dots, k_j$) equal to $k_j - 1$, whatever the block size. Summing over the blocks where method $i$ appears gives the per-method statistic $A_i$. The vector $A$ has length equal to the number of methods and sums to zero. Its null covariance is

$$
\Sigma_{ii} = \sum_{\text{blocks } j \text{ containing method } i} (k_j - 1)
$$

$$
\Sigma_{ij} = -(\text{number of blocks containing both } i \text{ and } j), \quad i \neq j
$$

Every row of $\Sigma$ sums to zero, so $\Sigma$ is rank-deficient by one. Dropping any single row and column gives a positive definite $(n - 1) \times (n - 1)$ submatrix that can be inverted, and the test statistic is the quadratic form

$$
T = A_{\text{reduced}}^{\top} \, \Sigma_{\text{reduced}}^{-1} \, A_{\text{reduced}}
$$

which is $\chi^2$ distributed with $n_{\text{methods}} - 1$ degrees of freedom under the null. Which row and column is dropped does not affect the statistic, because $A$ lies in the column space of $\Sigma$.

On a complete matrix Skillings-Mack collapses to the Friedman $\chi^2$: every block has the same $k$, the standardizing factor is constant, and the covariance structure matches the rank-sum formulation. beam tests this equivalence at every random seed in the test suite to within $10^{-10}$, with one caveat. scipy's `friedmanchisquare` applies a tie correction that divides the statistic by $1 - T / (k (k^2 - 1) N)$, where $T$ is the standard ties term; the 1981 Skillings-Mack formulation does not. The two statistics differ when there are within-block ties, and agree to machine precision without them.

Two ways to use the pair:

- Restrict the matrix to the complete cases, the methods and datasets where every method ran, and call `critical_difference`. This gives a global test and the Nemenyi cliques but drops every dataset where any method failed to run. It fits when the complete cases are enough.
- Keep every observed score and call `skillings_mack` on the partial matrix. This gives a global test only, with no pairwise cliques. It fits when restricting to the complete cases drops most of the data.

## Limitations

The Nemenyi post-hoc compares every pair of methods and is conservative. When the question is whether one new method beats a fixed set of baselines, comparing to a single control with the Bonferroni-Dunn correction has more power, as Demsar notes. beam currently implements the all-pairs Nemenyi case.

## See also

- [Pairwise method comparison](pairwise-method-comparison.md)

## References

- Demsar, J. Statistical comparisons of classifiers over multiple data sets. Journal of Machine Learning Research 7 (2006).
- Skillings, J. H., Mack, G. A. On the use of a Friedman-type statistic in balanced and unbalanced block designs. Technometrics 23(2), 171-177 (1981). DOI [10.1080/00401706.1981.10486261](https://doi.org/10.1080/00401706.1981.10486261).
