"""Rescale a tool by metric score matrix to [0, 1], respecting polarity.

The pipeline picks one strategy per metric column from the card field
``comparability.recommended_normalization``. Each strategy answers a
different failure mode of plain min-max scaling:

- ``min_max``: linear rescale between the declared bounds, or the column
  extrema when a bound is missing. Simple, but one outlier sets the scale
  and the metric's meaningful zero is mapped to the column midpoint.
- ``log_min_max``: min-max on the natural log of the column. For ratio
  metrics whose values span orders of magnitude (runtime, peak memory)
  this keeps the multiplicative structure, so a single slow method no
  longer compresses the differences among the fast ones (Smith 1988).
  Requires strictly positive values.
- ``rank``: map the within-column position to [0, 1]. Scale-free and
  immune to outliers; it keeps the order of the methods but drops the
  size of the gaps between them.
- ``zscore``: standardize the column, then pass it through the logistic
  so the result is bounded in (0, 1). The mean method maps to 0.5 and an
  outlier is compressed smoothly instead of setting the scale.
- ``baseline_relative``: rescale relative to a declared reference score
  (the chance-level value of a corrected-for-chance metric), so a method
  no better than chance maps to 0 rather than to the column midpoint.
  Defined for higher-is-better metrics only.

``normalization_warnings`` is the matching guard. It flags min-max columns
that rest on an empirical bound (not comparable across method sets) or
that are heavy-tailed (one outlier dominates the rescale).
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

Bound = tuple[float | None, float | None]

STRATEGIES = ("min_max", "log_min_max", "rank", "zscore", "baseline_relative")

_HEAVY_TAIL_RATIO = 10.0


def min_max_normalize(
    scores: np.ndarray,
    polarity: Sequence[str],
    bounds: Sequence[Bound] | None = None,
) -> np.ndarray:
    """Min-max normalize every column of ``scores`` to [0, 1].

    Thin wrapper over ``normalize`` with the ``min_max`` strategy on every
    column. Higher-is-better columns map to ``(x - lo) / (hi - lo)``;
    lower-is-better columns map to ``(hi - x) / (hi - lo)``; a zero-range
    column maps to 0.5. When ``bounds`` declares both ends, observations
    outside the range raise.

    Parameters
    ----------
    scores
        2D array, shape (n_tools, n_metrics).
    polarity
        One ``"higher_is_better"`` or ``"lower_is_better"`` per column.
    bounds
        Optional per-column ``(lower, upper)``; either can be None to fall
        back to the empirical extremum for that side.

    Returns
    -------
    2D array of the same shape, every column in [0, 1].
    """
    n_metrics = np.asarray(scores).shape[1] if np.asarray(scores).ndim == 2 else 0
    return normalize(scores, polarity, ["min_max"] * n_metrics, bounds=bounds)


def normalize(
    scores: np.ndarray,
    polarity: Sequence[str],
    strategies: Sequence[str],
    bounds: Sequence[Bound] | None = None,
    baselines: Sequence[float | None] | None = None,
) -> np.ndarray:
    """Rescale each column of ``scores`` to [0, 1] under a per-column strategy.

    Parameters
    ----------
    scores
        2D array, shape (n_tools, n_metrics).
    polarity
        One ``"higher_is_better"`` or ``"lower_is_better"`` per column.
    strategies
        One entry per column, each from ``STRATEGIES``.
    bounds
        Optional per-column ``(lower, upper)`` declared range. Used by
        ``min_max`` and ``baseline_relative`` and for the out-of-range
        check applied to every strategy. ``log_min_max``, ``rank`` and
        ``zscore`` set their own anchors from the data.
    baselines
        Optional per-column reference score required by
        ``baseline_relative``.

    Returns
    -------
    2D array of the same shape, every column in [0, 1].
    """
    scores = np.asarray(scores, dtype=float)
    polarity = list(polarity)
    strategies = list(strategies)
    if scores.ndim != 2:
        raise ValueError(f"scores must be 2D; got shape {scores.shape}")
    n_metrics = scores.shape[1]
    if len(polarity) != n_metrics:
        raise ValueError(f"polarity has {len(polarity)} entries but scores has {n_metrics} columns")
    if len(strategies) != n_metrics:
        raise ValueError(
            f"strategies has {len(strategies)} entries but scores has {n_metrics} columns"
        )
    if bounds is not None and len(bounds) != n_metrics:
        raise ValueError(f"bounds has {len(bounds)} entries but scores has {n_metrics} columns")
    if baselines is not None and len(baselines) != n_metrics:
        raise ValueError(
            f"baselines has {len(baselines)} entries but scores has {n_metrics} columns"
        )

    result = np.empty_like(scores)
    for j in range(n_metrics):
        col = scores[:, j]
        pol = polarity[j]
        strat = strategies[j]
        lo, hi = (None, None) if bounds is None else bounds[j]
        base = None if baselines is None else baselines[j]
        if pol not in ("higher_is_better", "lower_is_better"):
            raise ValueError(f"unknown polarity {pol!r} for column {j}")
        _check_declared_range(col, j, lo, hi)
        if strat == "min_max":
            result[:, j] = _min_max_col(col, pol, lo, hi)
        elif strat == "log_min_max":
            result[:, j] = _log_min_max_col(col, pol, j)
        elif strat == "rank":
            result[:, j] = _rank_col(col, pol)
        elif strat == "zscore":
            result[:, j] = _zscore_col(col, pol)
        elif strat == "baseline_relative":
            result[:, j] = _baseline_relative_col(col, pol, base, hi, j)
        else:
            raise ValueError(f"unknown normalization strategy {strat!r} for column {j}")
    return result


def normalization_warnings(
    scores: np.ndarray,
    strategies: Sequence[str],
    bounds: Sequence[Bound] | None = None,
    metric_ids: Sequence[str] | None = None,
    heavy_tail_ratio: float = _HEAVY_TAIL_RATIO,
) -> list[str]:
    """Flag min-max columns whose rescale is fragile.

    Two checks, applied only to columns using the ``min_max`` strategy:

    1. Empirical bound. If a declared bound is missing on either side, the
       column max or min sets the scale, so the normalized values change
       when the method set changes. This breaks comparability across runs
       and across an incrementally built leaderboard.
    2. Heavy tail. If the positive values span more than ``heavy_tail_ratio``
       between their maximum and their median, one outlier compresses the
       rest toward a single value and erases real differences. The message
       points at ``log_min_max`` or ``rank``.

    Returns a list of human-readable strings, empty when nothing is flagged.
    """
    scores = np.asarray(scores, dtype=float)
    strategies = list(strategies)
    out: list[str] = []
    for j, strat in enumerate(strategies):
        if strat != "min_max":
            continue
        label = metric_ids[j] if metric_ids is not None else f"column {j}"
        lo, hi = (None, None) if bounds is None else bounds[j]
        if lo is None or hi is None:
            side = "lower" if lo is None else "upper"
            out.append(
                f"metric {label}: min_max used an empirical {side} bound; "
                "normalized values are not comparable across different method sets"
            )
        col = scores[:, j]
        positive = col[col > 0]
        if positive.size:
            median = float(np.median(positive))
            if median > 0 and float(positive.max()) / median > heavy_tail_ratio:
                ratio = float(positive.max()) / median
                out.append(
                    f"metric {label}: min_max on a heavy-tailed column "
                    f"(max/median {ratio:.0f}); one outlier compresses the rest. "
                    "Consider log_min_max or rank."
                )
    return out


def _check_declared_range(col: np.ndarray, j: int, lo: float | None, hi: float | None) -> None:
    if lo is not None and float(col.min()) < lo:
        raise ValueError(f"column {j} has value {col.min()} below declared lower bound {lo}")
    if hi is not None and float(col.max()) > hi:
        raise ValueError(f"column {j} has value {col.max()} above declared upper bound {hi}")


def _min_max_col(col: np.ndarray, pol: str, lo: float | None, hi: float | None) -> np.ndarray:
    low = float(col.min()) if lo is None else float(lo)
    high = float(col.max()) if hi is None else float(hi)
    if high == low:
        return np.full_like(col, 0.5)
    if pol == "higher_is_better":
        return (col - low) / (high - low)
    return (high - col) / (high - low)


def _log_min_max_col(col: np.ndarray, pol: str, j: int) -> np.ndarray:
    if np.any(col <= 0):
        raise ValueError(f"column {j}: log_min_max requires strictly positive values")
    logged = np.log(col)
    return _min_max_col(logged, pol, None, None)


def _rank_col(col: np.ndarray, pol: str) -> np.ndarray:
    n = col.shape[0]
    if n == 1:
        return np.full_like(col, 0.5)
    oriented = col if pol == "higher_is_better" else -col
    ranks = _average_rank(oriented)
    return (ranks - 1.0) / (n - 1.0)


def _zscore_col(col: np.ndarray, pol: str) -> np.ndarray:
    std = float(col.std())
    if std == 0.0:
        return np.full_like(col, 0.5)
    z = (col - float(col.mean())) / std
    if pol == "lower_is_better":
        z = -z
    return 1.0 / (1.0 + np.exp(-z))


def _baseline_relative_col(
    col: np.ndarray, pol: str, baseline: float | None, hi: float | None, j: int
) -> np.ndarray:
    if pol != "higher_is_better":
        raise ValueError(
            f"column {j}: baseline_relative is defined for higher_is_better metrics only"
        )
    if baseline is None:
        raise ValueError(
            f"column {j}: baseline_relative needs score_of_random_baseline on the card"
        )
    top = float(col.max()) if hi is None else float(hi)
    if top <= baseline:
        return np.full_like(col, 0.5)
    scaled = (col - baseline) / (top - baseline)
    return np.clip(scaled, 0.0, 1.0)


def _average_rank(values: np.ndarray) -> np.ndarray:
    """Ascending average ranks (1-based); tied values share their mean rank."""
    n = values.shape[0]
    order = np.argsort(values, kind="stable")
    ordered = values[order]
    ranks = np.empty(n, dtype=float)
    i = 0
    while i < n:
        j = i
        while j + 1 < n and ordered[j + 1] == ordered[i]:
            j += 1
        ranks[order[i : j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return ranks
