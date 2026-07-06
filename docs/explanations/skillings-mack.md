# Skillings-Mack: coverage-aware Friedman

The Demsar [Friedman-Nemenyi test](comparing-methods-across-datasets.md) in [`beam.mcda.critical_difference`](../reference/critical_difference.qmd) only runs on a complete tool by dataset matrix. Real benchmarks rarely give one: methods time out, error on an input, or were not run on every dataset. beam's [missing-data policy](missing-data.md) refuses to fill those gaps by imputation, so the critical-difference test does not run on the matrix and reduces it to the complete observations. On a wide table with many partial methods, there might be no complete observations.

The Skillings-Mack (1981) test fills the gap with a Friedman-type statistic that does not need a complete matrix. It is provided as [`beam.mcda.skillings_mack`](../reference/skillings_mack.qmd) and as the convenience alias [`beam.mcda.coverage_aware_critical_difference`](../reference/coverage_aware_critical_difference.qmd).

## Rationale

The input is the same tool by dataset matrix the Friedman test takes, with NaN allowed. The test answers the same global question, "are the methods separable across the datasets, or does the apparent ranking fall within noise". It does not give pairwise comparisons; the Nemenyi post-hoc needs the complete-matrix construction that Skillings-Mack generalizes.

Within each block (column) $j$ the methods that are present are ranked from 1 (lowest score) to $k_j$ (highest score), with average ranks for ties. The within-block rank for method $i$ is then centred and standardized by the block size:

$$
A_{ij} = \left(R_{ij} - \frac{k_j + 1}{2}\right) \sqrt{\frac{12}{k_j + 1}}
$$

The factor $\sqrt{12 / (k_j + 1)}$ makes the variance of $A_{ij}$ under the null (the method's rank is uniformly distributed over $1, \dots, k_j$) equal to $k_j - 1$, whatever the block size. Summing over the blocks where method $i$ appears gives the per-method statistic $A_i$. The vector $A$ has length equal to the number of methods and sums to zero.

The covariance matrix of $A$ under the null is

$$
\Sigma_{ii} = \sum_{\text{blocks } j \text{ containing method } i} (k_j - 1)
$$

$$
\Sigma_{ij} = -(\text{number of blocks containing both } i \text{ and } j), \quad i \neq j
$$

Every row of $\Sigma$ sums to zero, so $\Sigma$ is rank-deficient by one. Dropping any single row and column gives a positive definite $(n - 1) \times (n - 1)$ submatrix that can be inverted. The test statistic is the quadratic form

$$
T = A_{\text{reduced}}^{\top} \, \Sigma_{\text{reduced}}^{-1} \, A_{\text{reduced}}
$$

which is $\chi^2$ distributed with $n_{\text{methods}} - 1$ degrees of freedom under the null. The choice of which row and column to drop does not affect the statistic, because $A$ lies in the column space of $\Sigma$.

## Implications

The Nemenyi critical difference depends on every pair of methods being ranked on every dataset. With incomplete blocks the per-method "average rank" no longer has the same denominator across methods, and the studentized range distribution that justifies Nemenyi assumes equal block sizes. beam returns the global Skillings-Mack test only. For pairwise statements the user must restrict the matrix to the block of methods and datasets where all of them ran and run `critical_difference` there.

On a complete matrix Skillings-Mack collapses to the Friedman $\chi^2$ statistic. Every block has the same $k$, the standardizing factor is constant, and the covariance structure becomes the same as the rank-sum formulation in Friedman. beam tests this equivalence at every random seed in the test suite to within $10^{-10}$. With a caveat. scipy's `friedmanchisquare` applies a tie correction that divides the statistic by $1 - T / (k (k^2 - 1) N)$ where $T$ is the standard ties term. The standard Skillings-Mack formulation in the 1981 paper does not include this correction. So the two statistics differ when there are within-block ties. Without ties they agree to machine precision.

## Choosing `skillings_mack` vs `critical_difference`

- Restrict the matrix to the complete block of methods and datasets where every method ran, and call `critical_difference`. This gives a global test and the Nemenyi cliques but drops every dataset where any method failed to run. It fits when the complete block is large enough.
- Keep every observed score and call `skillings_mack` on the partial matrix. This gives a global test only, with no pairwise cliques. It fits when restricting to the complete block drops most of the data.

## See also

- [Comparing methods across datasets](comparing-methods-across-datasets.md)
- [Mixed-effects model](heterogeneity-mixed-effects.md)

## References

- Skillings JH, Mack GA. On the use of a Friedman-type statistic in balanced and unbalanced block designs. Technometrics 1981, 23(2):171-177. DOI [10.1080/00401706.1981.10486261](https://doi.org/10.1080/00401706.1981.10486261).
- Demsar J. Statistical comparisons of classifiers over multiple data sets. Journal of Machine Learning Research 7 (2006).
