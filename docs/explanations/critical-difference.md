# Critical difference: Friedman, Nemenyi, Skillings-Mack

A [composite ranking](aggregation-methods.md) does not test whether the methods differ. Demsar (2006) ranks the methods on each dataset and tests the ranks. beam implements it in [`beam.mcda.critical_difference`](../reference/critical_difference.qmd).

## Method

The input is a tool by dataset matrix for one metric or for a composite. The methods are ranked on each dataset, 1 for the best, and averaged across datasets. The Friedman test asks whether the average ranks differ more than expected if all methods were equivalent.

The Nemenyi post-hoc gives the critical difference, the smallest gap between two average ranks that is significant at the chosen alpha: $q \sqrt{k (k + 1) / (6 N)}$, with $k$ methods, $N$ datasets, and $q$ the Studentized range value for $k$ divided by the square root of two. beam computes $q$ with scipy. For five methods at alpha 0.05, $q$ is 2.728, as in Demsar's Table 5.

The critical difference decreases with more datasets and with fewer methods.

## Cliques

A clique is a maximal run of methods, consecutive in rank order, whose first and last average ranks are within the critical difference. Two methods that share no clique are significantly different.

## Usage

`critical_difference(scores, higher_is_better=True)` takes a tool by dataset matrix; `higher_is_better=False` is for cost metrics such as runtime. The report has the average ranks, the Friedman statistic and p-value, the critical difference, and the cliques. The test needs at least three methods and two datasets, and a complete matrix.

## Skillings-Mack for incomplete blocks

`critical_difference` reduces the matrix to its complete cases, since beam's [missing-data policy](missing-data.md) does not impute. The Skillings-Mack (1981) test is a Friedman-type statistic for an incomplete matrix, in [`beam.mcda.skillings_mack`](../reference/skillings_mack.qmd), alias [`beam.mcda.coverage_aware_critical_difference`](../reference/coverage_aware_critical_difference.qmd). It is a global test only, with no pairwise comparisons or cliques.

Within each block (column) $j$ the methods present are ranked from 1 (lowest score) to $k_j$, with average ranks for ties. The rank of method $i$ is centred and standardized by the block size:

$$
A_{ij} = \left(R_{ij} - \frac{k_j + 1}{2}\right) \sqrt{\frac{12}{k_j + 1}}
$$

$A_i$ is the sum over the blocks where method $i$ appears. Its null covariance is

$$
\Sigma_{ii} = \sum_{\text{blocks } j \text{ containing method } i} (k_j - 1)
$$

$$
\Sigma_{ij} = -(\text{number of blocks containing both } i \text{ and } j), \quad i \neq j
$$

$\Sigma$ is rank-deficient by one. With any one row and column dropped, the statistic is

$$
T = A_{\text{reduced}}^{\top} \, \Sigma_{\text{reduced}}^{-1} \, A_{\text{reduced}}
$$

which is $\chi^2$ distributed with $n_{\text{methods}} - 1$ degrees of freedom under the null.

On a complete matrix without within-block ties, Skillings-Mack equals the Friedman $\chi^2$; the test suite checks this to within $10^{-10}$. With ties they differ, because scipy's `friedmanchisquare` applies a tie correction.

## Limits

The all-pairs Nemenyi post-hoc is conservative. Comparison of one method to a control with the Bonferroni-Dunn correction has more power (Demsar 2006) and is not implemented.

## See also

- [Pairwise method comparison](pairwise-method-comparison.md)

## References

- Demsar, J. Statistical comparisons of classifiers over multiple data sets. Journal of Machine Learning Research 7 (2006).
- Skillings, J. H., Mack, G. A. On the use of a Friedman-type statistic in balanced and unbalanced block designs. Technometrics 23(2), 171-177 (1981). DOI [10.1080/00401706.1981.10486261](https://doi.org/10.1080/00401706.1981.10486261).
