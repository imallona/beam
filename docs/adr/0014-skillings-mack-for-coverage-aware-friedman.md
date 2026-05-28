# 0014 - Skillings-Mack for coverage-aware Friedman

- Status: Accepted
- Date: 2026-05-28
- Deciders: Izaskun Mallona
- Supersedes: -
- Superseded by: -

## Context

[ADR 0013](0013-missing-data-policy.md) settles that beam never imputes a missing score by default and never silently fills a gap. The Friedman-Nemenyi critical-difference test in `beam.mcda.critical_difference` enforces that rule by refusing any tool by dataset matrix that has missing cells: the per-dataset ranks 1..k are only defined when every method ran on the column. The advice in the error message is to restrict the diagram to the complete block of methods and datasets.

That advice is fine when the complete block is large. On a wide benchmark with many partial methods it can collapse to a handful of datasets, and the test loses statistical power exactly when the user needs it. The published generalization of the Friedman test to unbalanced blocks is Skillings and Mack (1981), but it had been listed as future work since the missing-data policy landed; the ADR 0013 references record the omission.

## Decision

Implement the Skillings-Mack test as `beam.mcda.skillings_mack`. It takes the same tool by dataset matrix as `critical_difference` but accepts NaN. Within each block the present methods are ranked, the within-block deviations from the block centre are standardised by `sqrt(12 / (k + 1))`, the per-method sums `A_i` and their null covariance matrix `Sigma` are accumulated across blocks, and one row and column are dropped before the chi-squared form `T = A.T Sigma^{-1} A` is taken on the reduced system. The statistic is chi-squared with `n_methods - 1` degrees of freedom.

A convenience alias `coverage_aware_critical_difference` returns the same `SkillingsMackReport` for callers that branch on the critical-difference output. The Nemenyi post-hoc is not generalized: its critical-difference formula needs equal block sizes, and the user is told to restrict the matrix to the complete block for pairwise statements.

## Consequences

- The user now has a global test on the partial matrix without imputing. The "are the methods separable" question gets an answer even when the complete block is small.
- The Nemenyi post-hoc is still complete-case only. The user must consciously choose between two analyses: the global Skillings-Mack on every observed block, or the complete-case Friedman-Nemenyi with cliques on the restricted block. The trade-off (more data vs pairwise statements) is explicit, not buried.
- On a complete matrix the Skillings-Mack statistic equals the Friedman chi-squared statistic to machine precision when there are no ties; scipy's tie correction is the only allowed deviation. The test suite asserts the equality at every random seed it runs, so the implementation is anchored to the existing Friedman code as an oracle.
- The error from `critical_difference` is unchanged: it still names the offending cells and points to the complete-case block. The pointer now also names Skillings-Mack as the alternative.
- The implementation is pure NumPy and SciPy. No new dependency, no R subprocess. It composes with the missing-data policy because it does not need the policy: it adjusts the statistic rather than completing the matrix.

## Alternatives considered

- Keep refusing partial matrices and require the user to restrict to the complete block. Rejected: the complete block is often too small in benchmarks with broad method coverage, and the principled generalization exists.
- Generalize Nemenyi with a heuristic correction for unequal block sizes. Rejected: there is no standard procedure with the same controlled type-I error as Nemenyi, and a homemade one would not be defensible. The honest answer is to restrict the post-hoc to the complete block.
- Implement only the Skillings-Mack global test and not expose the `coverage_aware_critical_difference` alias. Rejected: the alias mirrors the `critical_difference` entry point and lets the user swap one call for the other when the matrix has gaps, with a clear note in the report that the cliques are not available.

## References

- Skillings JH, Mack GA. On the use of a Friedman-type statistic in balanced and unbalanced block designs. Technometrics 1981, 23(2):171-177. DOI 10.1080/00401706.1981.10486261.
- [ADR 0013 (missing-data policy)](0013-missing-data-policy.md) for the never-impute rule that motivates this test.
- [docs/explanations/skillings-mack.md](../explanations/skillings-mack.md) for the user-facing explanation.
- [docs/explanations/comparing-methods-across-datasets.md](../explanations/comparing-methods-across-datasets.md) for the complete-case Friedman-Nemenyi test.
