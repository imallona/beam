"""How much each dataset separates the methods it scores.

Cross-benchmark comparisons that compare method orders need shared methods. When
the method sets are disjoint, that comparison is unavailable. A property defined
per dataset is still available: how much a dataset separates the methods it
scores. Every benchmark can report it for every dataset.

``dataset_discrimination`` computes it from the scores. A dataset on which the
methods score about the same cannot rank them; a dataset on which they differ
can. This is the per-dataset form of the metric-level notion in the weighting
code, where a metric on which methods do not differ has no discrimination. It
complements :func:`dataset_concordance`, which asks whether datasets agree on the
order.

Two values per dataset.

- Spread, the effect size. Each metric is oriented to higher-is-better and
  min-max scaled across the benchmark's cells, so metrics are comparable and a
  dataset on which every method scores near the maximum keeps a small spread. The
  metrics are pooled to one score per method, and the spread is the standard
  deviation across methods.
- Concordance, the consistency. Kendall's W over the dataset's method-by-metric
  matrix, with its Friedman p value. A high W means the metrics order the methods
  the same way; a low W means they do not, so a single ranking on that dataset is
  unstable.

The scaling is per benchmark, so spreads are comparable within a benchmark and
only roughly across benchmarks.
"""

from __future__ import annotations

import warnings
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from scipy.stats import chi2, rankdata

_ORIENTATION = {"higher_is_better": 1.0, "lower_is_better": -1.0}


@dataclass(frozen=True)
class DatasetDiscriminationReport:
    """How strongly each dataset separates the methods it scores.

    Attributes
    ----------
    dataset_ids
        Dataset labels in input order, or ``None`` when the input carried none.
    spread
        Per-dataset standard deviation across methods of the pooled normalized
        score, the effect size. ``nan`` when fewer than two methods are observed
        on the dataset.
    kendall_w
        Per-dataset Kendall's W over the method-by-metric matrix, in ``[0, 1]``,
        the consistency. ``nan`` when fewer than ``min_methods`` methods or two
        metrics form a complete block on the dataset.
    p_value
        Per-dataset Friedman p value for the null that the metrics order the
        methods independently. ``nan`` where ``kendall_w`` is ``nan``.
    significant
        ``p_value < alpha``, per dataset.
    n_methods_used, n_metrics_used
        Methods and metrics in the complete block behind ``kendall_w``.
    pooled_score
        ``(n_methods, n_datasets)`` pooled normalized score per method per
        dataset, the input to ``spread``. ``nan`` where a method is unobserved.
    order
        Dataset indices sorted by descending ``spread`` (``nan`` spreads last).
    mean_spread, mean_kendall_w
        Means over the datasets with a finite value.
    most_discriminating, least_discriminating
        Dataset ids with the largest and smallest finite ``spread``, or ``None``.
    """

    dataset_ids: tuple[str, ...] | None
    spread: np.ndarray
    kendall_w: np.ndarray
    p_value: np.ndarray
    significant: np.ndarray
    n_methods_used: np.ndarray
    n_metrics_used: np.ndarray
    pooled_score: np.ndarray
    order: np.ndarray
    mean_spread: float
    mean_kendall_w: float
    most_discriminating: str | None
    least_discriminating: str | None


def _oriented(scores: np.ndarray, polarity: Sequence[str]) -> np.ndarray:
    signs = np.array([_ORIENTATION[p] for p in polarity], dtype=float)
    return scores * signs


def _minmax_per_metric(oriented: np.ndarray) -> np.ndarray:
    """Scale each metric to [0, 1] across all method-by-dataset cells.

    A metric that is constant over every observed cell carries no separation and
    maps to all-``nan`` so it drops out of the pooled mean.
    """
    out = np.full_like(oriented, np.nan)
    n_metrics = oriented.shape[2]
    for k in range(n_metrics):
        col = oriented[:, :, k]
        finite = col[np.isfinite(col)]
        if finite.size == 0:
            continue
        lo, hi = float(finite.min()), float(finite.max())
        if hi == lo:
            continue
        out[:, :, k] = (col - lo) / (hi - lo)
    return out


def _kendall_w(block: np.ndarray) -> tuple[float, float]:
    """Kendall's W and Friedman p for a complete method-by-metric block.

    Rows are methods (items), columns are metrics (raters); every cell is finite.
    Returns ``(W, p)`` with a tie correction, or ``(nan, nan)`` when the block is
    too small to rank.
    """
    n, m = block.shape  # n methods (items), m metrics (raters)
    if n < 2 or m < 1:
        return float("nan"), float("nan")
    ranks = np.vstack([rankdata(block[:, j]) for j in range(m)]).T  # (n methods, m metrics)
    rank_sums = ranks.sum(axis=1)
    s = float(((rank_sums - rank_sums.mean()) ** 2).sum())
    tie = 0.0
    for j in range(m):
        _, counts = np.unique(ranks[:, j], return_counts=True)
        tie += float(((counts**3) - counts).sum())
    denom = (m**2) * (n**3 - n) - m * tie
    if denom <= 0:
        return float("nan"), float("nan")
    w = 12.0 * s / denom
    chi_stat = m * (n - 1) * w
    p = float(chi2.sf(chi_stat, n - 1))
    return float(w), p


def dataset_discrimination(
    scores,
    polarity: Sequence[str],
    dataset_ids: Sequence[str] | None = None,
    min_methods: int = 3,
    alpha: float = 0.05,
) -> DatasetDiscriminationReport:
    """Measure how strongly each dataset separates the methods it scores.

    Works on a benchmark with any method set, so benchmarks with disjoint methods
    can each be measured and then compared. Reports a spread (effect size) and a
    Kendall's W (consistency) per dataset; see the module docstring.

    Parameters
    ----------
    scores
        Tensor of shape ``(n_methods, n_datasets, n_metrics)``. A method or metric
        not observed on a dataset is ``nan``; nothing is imputed. Pass one
        benchmark's scores per call (the min-max scaling is within the tensor).
    polarity
        Length ``n_metrics`` sequence of ``"higher_is_better"`` or
        ``"lower_is_better"``. A ``"target_value"`` metric has no monotone quality
        direction; drop it before calling.
    dataset_ids
        Optional length ``n_datasets`` labels carried into the report.
    min_methods
        Minimum methods in a dataset's complete method-by-metric block for
        Kendall's W to be computed. Default 3.
    alpha
        Significance level for ``significant``. Default 0.05.

    Returns
    -------
    DatasetDiscriminationReport

    Raises
    ------
    ValueError
        If ``scores`` is not three-dimensional, or ``polarity`` length does not
        match the metric axis.
    """
    scores = np.asarray(scores, dtype=float)
    if scores.ndim != 3:
        raise ValueError(f"scores must be (n_methods, n_datasets, n_metrics); got {scores.shape}")
    _n_methods, n_datasets, n_metrics = scores.shape
    if len(polarity) != n_metrics:
        raise ValueError(f"polarity length {len(polarity)} does not match {n_metrics} metrics")
    if dataset_ids is not None and len(dataset_ids) != n_datasets:
        raise ValueError(f"dataset_ids length {len(dataset_ids)} does not match {n_datasets}")

    oriented = _oriented(scores, polarity)
    normalized = _minmax_per_metric(oriented)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        pooled = np.nanmean(normalized, axis=2)  # (n_methods, n_datasets)

    spread = np.full(n_datasets, np.nan)
    kendall_w = np.full(n_datasets, np.nan)
    p_value = np.full(n_datasets, np.nan)
    n_methods_used = np.zeros(n_datasets, dtype=int)
    n_metrics_used = np.zeros(n_datasets, dtype=int)

    for d in range(n_datasets):
        col = pooled[:, d]
        observed = col[np.isfinite(col)]
        if observed.size >= 2:
            spread[d] = float(np.std(observed, ddof=1))

        slab = oriented[:, d, :]  # (n_methods, n_metrics) for this dataset
        metric_ok = np.isfinite(slab).any(axis=0)
        slab = slab[:, metric_ok]
        method_ok = np.isfinite(slab).all(axis=1)
        block = slab[method_ok]
        n_metrics_used[d] = block.shape[1]
        n_methods_used[d] = block.shape[0]
        if block.shape[0] >= min_methods and block.shape[1] >= 2:
            w, p = _kendall_w(block)
            kendall_w[d] = w
            p_value[d] = p

    significant = np.where(np.isfinite(p_value), p_value < alpha, False)

    finite_spread = np.isfinite(spread)
    order = np.argsort(np.where(finite_spread, -spread, np.inf), kind="stable")
    mean_spread = float(np.nanmean(spread)) if finite_spread.any() else float("nan")
    mean_kendall_w = float(np.nanmean(kendall_w)) if np.isfinite(kendall_w).any() else float("nan")

    most = least = None
    if dataset_ids is not None and finite_spread.any():
        idx_sorted = np.argsort(np.where(finite_spread, spread, np.nan))
        finite_sorted = [i for i in idx_sorted if finite_spread[i]]
        least = dataset_ids[finite_sorted[0]]
        most = dataset_ids[finite_sorted[-1]]

    return DatasetDiscriminationReport(
        dataset_ids=tuple(dataset_ids) if dataset_ids is not None else None,
        spread=spread,
        kendall_w=kendall_w,
        p_value=p_value,
        significant=significant,
        n_methods_used=n_methods_used,
        n_metrics_used=n_metrics_used,
        pooled_score=pooled,
        order=order,
        mean_spread=mean_spread,
        mean_kendall_w=mean_kendall_w,
        most_discriminating=most,
        least_discriminating=least,
    )
