# Skillings-Mack: coverage-aware Friedman

The Demsar Friedman-Nemenyi test in `beam.mcda.critical_difference` only runs on a complete tool by dataset matrix. Real benchmarks rarely give one: methods time out, error on an input, or were not run on every dataset. beam's missing-data policy refuses to fill those gaps, so the critical-difference test refuses the matrix and points the user to the complete-case block. On a wide table with many partial methods, that block can shrink to nothing.

The Skillings-Mack (1981) test fills the gap with a Friedman-type statistic that does not need a complete matrix. It is exposed as `beam.mcda.skillings_mack` and as the convenience alias `beam.mcda.coverage_aware_critical_difference`.

## What the test does

The input is the same tool by dataset matrix the Friedman test takes, with NaN allowed. The test answers the same global question, "are the methods separable across the datasets, or does the apparent ranking sit within noise". It does not give pairwise comparisons; the Nemenyi post-hoc needs the complete-matrix construction it generalizes.

## Construction

Within each block (column) `j` the methods that are present are ranked from 1 (lowest score) to `k_j` (highest score), with average ranks for ties. The within-block rank for method `i` is then centred and standardized by the block size:

```
A_ij = (R_ij - (k_j + 1) / 2) * sqrt(12 / (k_j + 1))
```

The factor `sqrt(12 / (k_j + 1))` makes the variance of `A_ij` under the null (the method's rank is uniformly distributed over 1..k_j) equal to `k_j - 1`, whatever the block size. Summing over the blocks where method `i` appears gives the per-method statistic `A_i`. The vector `A` has length equal to the number of methods and sums to zero.

The covariance matrix of `A` under the null is

```
Sigma_ii = sum over blocks j containing method i of (k_j - 1)
Sigma_ij = -(count of blocks containing both i and j) for i != j
```

Every row of `Sigma` sums to zero, so `Sigma` is rank-deficient by one. Dropping any single row and column gives a positive definite `(n - 1) x (n - 1)` submatrix that can be inverted. The test statistic is the quadratic form

```
T = A_reduced.T @ Sigma_reduced^{-1} @ A_reduced
```

which is chi-squared distributed with `n_methods - 1` degrees of freedom under the null. The choice of which row and column to drop does not affect the statistic, because `A` lies in the column space of `Sigma`.

## Why the post-hoc is lost

The Nemenyi critical difference depends on every pair of methods being ranked on every dataset. With incomplete blocks the per-method "average rank" no longer has the same denominator across methods, and the studentized range distribution that justifies Nemenyi assumes equal block sizes. beam returns the global Skillings-Mack test only; for pairwise statements the user must restrict the matrix to the block of methods and datasets where all of them ran and run `critical_difference` there.

## Equivalence with Friedman on complete inputs

On a complete matrix Skillings-Mack collapses to the Friedman chi-squared statistic. Every block has the same `k`, the standardizing factor is constant, and the covariance structure becomes the same as the rank-sum formulation in Friedman. beam tests this equivalence at every random seed in the test suite to within 1e-10.

There is one caveat. scipy's `friedmanchisquare` applies a tie correction that divides the statistic by `1 - T / (k (k^2 - 1) N)` where `T` is the standard ties term. The standard Skillings-Mack formulation in the 1981 paper does not include this correction. The two statistics differ when there are within-block ties; without ties they agree to machine precision.

## When to use which test

Two consistent strategies:

- Restrict the matrix to the complete block of methods and datasets where every method ran, and call `critical_difference`. This gives a global test and the Nemenyi cliques but drops every dataset where any method failed to run. Use it when the complete block is large enough.
- Keep every observed score and call `skillings_mack` on the partial matrix. This gives a global test only, with no pairwise cliques. Use it when restricting to the complete block throws away most of the data.

The mixed-effects model in `beam.heterogeneity.mixed_effects` runs on partial data too, and answers a different question: how much of the score variance is due to the dataset rather than the method. Skillings-Mack tests the null that the methods are equivalent across the observed blocks; the mixed-effects model splits the variance assuming the methods do differ.

## References

- Skillings JH, Mack GA. On the use of a Friedman-type statistic in balanced and unbalanced block designs. Technometrics 1981, 23(2):171-177. DOI 10.1080/00401706.1981.10486261.
- Demsar J. Statistical comparisons of classifiers over multiple data sets. Journal of Machine Learning Research 7 (2006).
- The companion essay [Comparing methods across datasets](comparing-methods-across-datasets.md) covers the complete-case Friedman-Nemenyi test, which Skillings-Mack generalizes.
