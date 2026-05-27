"""Demsar (2006) Friedman test with a Nemenyi critical-difference diagram.

Given a tool by dataset score matrix, this module answers a question the
MCDA composite cannot: across the datasets, are the methods separable at
all, or does the apparent ranking sit within noise? It runs the Friedman
test on the per-dataset rankings and, alongside it, the Nemenyi post-hoc,
whose critical difference says how far two average ranks must be apart to
count as different.

The output is the data behind a critical-difference diagram: the average
rank per tool (1 is best), the Friedman statistic and p-value, the
critical difference at the chosen alpha, and the cliques of tools that are
not significantly different from one another.

Reference: Demsar, J. Statistical comparisons of classifiers over multiple
data sets. Journal of Machine Learning Research 7 (2006).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from scipy.stats import friedmanchisquare, studentized_range

from ._missing import IncompleteMatrixError


@dataclass(frozen=True)
class CriticalDifferenceReport:
    """Outcome of a Friedman test and Nemenyi post-hoc on a tool by dataset matrix.

    Fields:
        average_ranks: (n_tools,) mean rank across datasets, 1 is best.
        order: tool indices sorted from best (lowest rank) to worst.
        friedman_statistic: the Friedman chi-square statistic.
        friedman_pvalue: its p-value under the null that all methods rank
            equally across datasets.
        alpha: the significance level used for the Nemenyi critical difference.
        critical_difference: the smallest average-rank gap that is significant
            at ``alpha`` under the Nemenyi post-hoc.
        cliques: groups of tool indices (in rank order) whose pairwise average
            rank differences are all within the critical difference, so they
            are not significantly different. Only groups of two or more are
            reported.
        n_tools, n_datasets: matrix shape.
        tool_names: optional labels carried for reporting.
    """

    average_ranks: np.ndarray
    order: np.ndarray
    friedman_statistic: float
    friedman_pvalue: float
    alpha: float
    critical_difference: float
    cliques: tuple[tuple[int, ...], ...]
    n_tools: int
    n_datasets: int
    tool_names: tuple[str, ...] | None = None


def nemenyi_critical_difference(n_tools: int, n_datasets: int, alpha: float = 0.05) -> float:
    """Nemenyi critical difference for ``n_tools`` methods over ``n_datasets`` datasets.

    ``CD = q_alpha * sqrt(n_tools * (n_tools + 1) / (6 * n_datasets))`` where
    ``q_alpha`` is the Studentized range critical value at infinite degrees of
    freedom divided by sqrt(2). Matches Demsar (2006) Table 5: for n_tools=5
    and alpha=0.05 the q term is 2.728.
    """
    if n_tools < 2:
        raise ValueError(f"n_tools must be at least 2; got {n_tools}")
    if n_datasets < 1:
        raise ValueError(f"n_datasets must be at least 1; got {n_datasets}")
    q = float(studentized_range.ppf(1.0 - alpha, n_tools, np.inf)) / math.sqrt(2.0)
    return q * math.sqrt(n_tools * (n_tools + 1) / (6.0 * n_datasets))


def critical_difference(
    scores: np.ndarray,
    higher_is_better: bool = True,
    alpha: float = 0.05,
    tool_names: Sequence[str] | None = None,
) -> CriticalDifferenceReport:
    """Run the Friedman test and Nemenyi post-hoc on a tool by dataset matrix.

    Parameters
    ----------
    scores
        2D array of shape ``(n_tools, n_datasets)`` for one metric or for an
        MCDA composite. Each column holds the scores of every tool on one
        dataset.
    higher_is_better
        Whether a larger score is better. When ``False`` the ranking is
        reversed before ranks are taken, so the reported average ranks always
        put the better tool nearer 1. The Friedman statistic itself does not
        depend on the direction.
    alpha
        Significance level for the Nemenyi critical difference.
    tool_names
        Optional labels, length ``n_tools``, carried in the report.

    Returns
    -------
    CriticalDifferenceReport

    Notes
    -----
    Friedman needs at least three tools and two datasets, and a complete tool
    by dataset table: every tool ranked on every dataset. A missing cell is
    refused rather than dropped or filled, since the Friedman ranks per dataset
    are only defined over a complete column. The missing-data generalization is
    the Skillings-Mack (1981) test, which is not implemented here; restrict the
    diagram to the block of tools and datasets where all of them ran.
    """
    scores = np.asarray(scores, dtype=float)
    if scores.ndim != 2:
        raise ValueError(f"scores must be 2D; got shape {scores.shape}")
    if np.isnan(scores).any():
        raise IncompleteMatrixError(
            "critical_difference: the tool by dataset table has missing cells. "
            "The Friedman ranks are only defined over a complete column, so beam "
            "neither drops nor fills the gaps. Restrict the diagram to the block "
            "of tools and datasets where all of them ran (the Skillings-Mack 1981 "
            "test generalizes Friedman to missing data and is not implemented here)."
        )
    n_tools, n_datasets = scores.shape
    if n_tools < 3:
        raise ValueError(f"Friedman test needs at least 3 tools; got {n_tools}")
    if n_datasets < 2:
        raise ValueError(f"Friedman test needs at least 2 datasets; got {n_datasets}")
    if tool_names is not None and len(tool_names) != n_tools:
        raise ValueError(f"tool_names has {len(tool_names)} entries but scores has {n_tools} rows")

    oriented = scores if higher_is_better else -scores
    ranks = np.empty_like(oriented)
    for d in range(n_datasets):
        ranks[:, d] = _ranks_best_first(oriented[:, d])
    average_ranks = ranks.mean(axis=1)

    statistic, pvalue = friedmanchisquare(*[scores[i, :] for i in range(n_tools)])

    cd = nemenyi_critical_difference(n_tools, n_datasets, alpha=alpha)
    order = np.argsort(average_ranks, kind="stable")
    cliques = _cliques(average_ranks, order, cd)

    return CriticalDifferenceReport(
        average_ranks=average_ranks,
        order=order,
        friedman_statistic=float(statistic),
        friedman_pvalue=float(pvalue),
        alpha=alpha,
        critical_difference=cd,
        cliques=cliques,
        n_tools=n_tools,
        n_datasets=n_datasets,
        tool_names=tuple(tool_names) if tool_names is not None else None,
    )


def _ranks_best_first(column: np.ndarray) -> np.ndarray:
    """Average ranks of one dataset column, 1 for the largest value, ties averaged."""
    n = column.shape[0]
    order = np.argsort(-column, kind="stable")
    ordered = column[order]
    ranks = np.empty(n, dtype=float)
    i = 0
    while i < n:
        j = i
        while j + 1 < n and ordered[j + 1] == ordered[i]:
            j += 1
        ranks[order[i : j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return ranks


def _cliques(
    average_ranks: np.ndarray,
    order: np.ndarray,
    cd: float,
) -> tuple[tuple[int, ...], ...]:
    sorted_ranks = average_ranks[order]
    n = order.shape[0]
    spans: list[tuple[int, int]] = []
    for i in range(n):
        hi = i
        while hi + 1 < n and sorted_ranks[hi + 1] - sorted_ranks[i] <= cd:
            hi += 1
        spans.append((i, hi))

    def is_contained(span: tuple[int, int]) -> bool:
        return any(other != span and other[0] <= span[0] and span[1] <= other[1] for other in spans)

    maximal = [span for span in spans if span[1] > span[0] and not is_contained(span)]
    return tuple(tuple(int(order[k]) for k in range(lo, hi + 1)) for lo, hi in maximal)
