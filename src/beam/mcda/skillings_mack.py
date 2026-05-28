"""Skillings-Mack (1981) test: coverage-aware Friedman for incomplete blocks.

The Friedman test in ``beam.mcda.cd`` refuses any tool by dataset matrix with
missing cells, because the per-dataset ranks 1..k only make sense over a
complete column. Skillings and Mack (1981) generalize the Friedman statistic
to unbalanced block designs by ranking within each block over only the methods
that are present, standardizing each within-block rank deviation by the block
size, and assembling a chi-squared form from the resulting per-method sums.
The test gives a global "are the methods separable" answer on a partial matrix
without imputing the missing scores.

Reference: Skillings JH, Mack GA. On the use of a Friedman-type statistic in
balanced and unbalanced block designs. Technometrics 1981, 23(2):171-177.
DOI 10.1080/00401706.1981.10486261.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from scipy.stats import chi2, rankdata


@dataclass(frozen=True)
class SkillingsMackReport:
    """Outcome of a Skillings-Mack test on a tool by dataset matrix with NaN.

    Fields:
        statistic: chi-squared test statistic.
        df: degrees of freedom, ``n_methods - 1``.
        p_value: tail probability under the null that the methods rank equally.
        adjusted_rank_sums: length ``n_methods`` array of the centered
            standardized per-method statistics ``A_i``. They sum to zero by
            construction; a large absolute value flags a method whose
            within-block ranks systematically deviate from the block centre.
        coverage: length ``n_methods`` integer array recording the number of
            blocks (columns with at least two methods present) each method
            appears in.
        n_methods, n_blocks: matrix shape.
        method_names: optional labels carried for reporting.
        nemenyi_cliques: always ``None``. The Nemenyi post-hoc needs a
            complete matrix and is not generalized here; the field exists to
            mirror :class:`beam.mcda.cd.CriticalDifferenceReport` for callers
            that branch on the test's output.
        note: a short message explaining the lack of pairwise post-hoc and
            pointing to the complete-case block.
    """

    statistic: float
    df: int
    p_value: float
    adjusted_rank_sums: np.ndarray
    coverage: np.ndarray
    n_methods: int
    n_blocks: int
    method_names: tuple[str, ...] | None = None
    nemenyi_cliques: None = None
    note: str = (
        "Skillings-Mack is a global test on incomplete blocks. The Nemenyi "
        "pairwise post-hoc needs a complete matrix; restrict the comparison "
        "to the block of methods and datasets where all of them ran."
    )


def skillings_mack(
    scores: np.ndarray,
    higher_is_better: bool = True,
    method_names: Sequence[str] | None = None,
) -> SkillingsMackReport:
    """Run the Skillings-Mack test on a tool by dataset matrix that may have NaN.

    Parameters
    ----------
    scores
        2D array of shape ``(n_methods, n_blocks)``. NaN marks a method that
        did not run on a block. Blocks with fewer than two observed methods
        contribute nothing.
    higher_is_better
        Whether a larger score is better. When ``False`` the ranking is
        reversed inside each block so the better method earns the higher
        within-block rank. The chi-squared statistic itself does not depend
        on the direction.
    method_names
        Optional length ``n_methods`` labels, carried in the report.

    Returns
    -------
    SkillingsMackReport

    Notes
    -----
    Within each block ``j`` with ``k_j >= 2`` observed methods, the present
    scores are ranked from 1 (lowest) to ``k_j`` (highest) with ties averaged.
    For each method ``i``, the per-block contribution is

        ``(R_ij - (k_j + 1) / 2) * sqrt(12 / (k_j + 1))``

    and ``A_i`` is the sum of these contributions over the blocks where
    method ``i`` is present. The covariance matrix of ``A`` is

        ``Sigma_ii = sum over blocks j containing i of (k_j - 1)``
        ``Sigma_ij = -(count of blocks containing both i and j)``

    The full ``Sigma`` is rank-deficient (every row sums to zero), so one row
    and column are dropped before inverting the reduced submatrix. The test
    statistic ``T = A_red.T @ Sigma_red^-1 @ A_red`` is chi-squared with
    ``n_methods - 1`` degrees of freedom under the null that the methods rank
    identically. On a complete matrix the result equals the Friedman
    chi-squared statistic from :func:`beam.mcda.cd.critical_difference`.
    """
    scores = np.asarray(scores, dtype=float)
    if scores.ndim != 2:
        raise ValueError(f"scores must be 2D; got shape {scores.shape}")
    n_methods, n_blocks = scores.shape
    if n_methods < 3:
        raise ValueError(f"Skillings-Mack needs at least 3 methods; got {n_methods}")
    if n_blocks < 2:
        raise ValueError(f"Skillings-Mack needs at least 2 blocks; got {n_blocks}")
    if method_names is not None and len(method_names) != n_methods:
        raise ValueError(
            f"method_names has {len(method_names)} entries but scores has {n_methods} rows"
        )

    all_nan_rows = np.where(np.all(np.isnan(scores), axis=1))[0]
    if all_nan_rows.size:
        labels = (
            [method_names[i] for i in all_nan_rows]
            if method_names is not None
            else [int(i) for i in all_nan_rows]
        )
        raise ValueError(
            f"skillings_mack: methods with no observed block: {labels}. "
            "Drop them from the input or rerun those methods first."
        )

    oriented = scores if higher_is_better else -scores

    a = np.zeros(n_methods)
    sigma = np.zeros((n_methods, n_methods))
    coverage = np.zeros(n_methods, dtype=int)

    for j in range(n_blocks):
        column = oriented[:, j]
        present = np.where(~np.isnan(column))[0]
        k = present.size
        if k < 2:
            continue
        block_ranks = rankdata(column[present], method="average")
        factor = np.sqrt(12.0 / (k + 1))
        centred = (block_ranks - (k + 1) / 2.0) * factor
        a[present] += centred
        coverage[present] += 1
        sigma[np.ix_(present, present)] -= 1.0
        sigma[present, present] += k

    isolated = np.where(coverage == 0)[0]
    if isolated.size:
        labels = (
            [method_names[i] for i in isolated]
            if method_names is not None
            else [int(i) for i in isolated]
        )
        raise ValueError(
            f"skillings_mack: methods appear only in singleton blocks (no co-runner): {labels}. "
            "Each method needs at least one block where another method also ran."
        )

    keep = np.ones(n_methods, dtype=bool)
    keep[-1] = False
    a_red = a[keep]
    sigma_red = sigma[np.ix_(keep, keep)]
    solved = np.linalg.solve(sigma_red, a_red)
    statistic = float(a_red @ solved)
    df = n_methods - 1
    p_value = float(chi2.sf(statistic, df))

    return SkillingsMackReport(
        statistic=statistic,
        df=df,
        p_value=p_value,
        adjusted_rank_sums=a,
        coverage=coverage,
        n_methods=n_methods,
        n_blocks=n_blocks,
        method_names=tuple(method_names) if method_names is not None else None,
    )


def coverage_aware_critical_difference(
    scores: np.ndarray,
    higher_is_better: bool = True,
    method_names: Sequence[str] | None = None,
) -> SkillingsMackReport:
    """Convenience wrapper around :func:`skillings_mack` for the CD use case.

    A drop-in for :func:`beam.mcda.cd.critical_difference` when the matrix has
    missing cells. Returns a :class:`SkillingsMackReport` with the global
    chi-squared test only; ``nemenyi_cliques`` is ``None`` and the ``note``
    field explains that the pairwise post-hoc needs a complete matrix. On a
    matrix with no NaN this gives the same chi-squared statistic as
    :func:`critical_difference`, so the global "are the methods separable"
    answer is unchanged; only the cliques are missing.
    """
    return skillings_mack(
        scores,
        higher_is_better=higher_is_better,
        method_names=method_names,
    )
