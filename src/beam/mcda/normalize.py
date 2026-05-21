"""Normalise a tool by metric score matrix to [0, 1], respecting polarity."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

Bound = tuple[float | None, float | None]


def min_max_normalize(
    scores: np.ndarray,
    polarity: Sequence[str],
    bounds: Sequence[Bound] | None = None,
) -> np.ndarray:
    """Min-max normalise each column of ``scores`` to [0, 1].

    Higher-is-better metrics map to (x - min) / (max - min). Lower-is-better
    metrics map to (max - x) / (max - min), so the result is always
    higher = better. A column with zero range maps to all 0.5 to avoid
    divide-by-zero and to signal that the column carries no discriminating
    information.

    Parameters
    ----------
    scores
        2D array, shape (n_tools, n_metrics).
    polarity
        Sequence of "higher_is_better" or "lower_is_better", one entry per
        metric column.
    bounds
        Optional sequence of (lower, upper) per metric. Either can be None
        to fall back to the empirical extremum for that side. When both
        bounds are provided, observations outside ``[lower, upper]`` are
        rejected. Typical use: pass the declared ``range_lower`` and
        ``range_upper`` from each metric card so that normalisation uses
        the theoretical scale of the metric rather than the empirical
        spread of the current score table.

    Returns
    -------
    2D array of the same shape, with every column in [0, 1].
    """
    scores = np.asarray(scores, dtype=float)
    polarity = list(polarity)
    if scores.ndim != 2:
        raise ValueError(f"scores must be 2D; got shape {scores.shape}")
    if len(polarity) != scores.shape[1]:
        raise ValueError(
            f"polarity has {len(polarity)} entries but scores has {scores.shape[1]} columns"
        )
    if bounds is not None and len(bounds) != scores.shape[1]:
        raise ValueError(
            f"bounds has {len(bounds)} entries but scores has {scores.shape[1]} columns"
        )

    result = np.empty_like(scores)
    for j, pol in enumerate(polarity):
        col = scores[:, j]
        declared_lo, declared_hi = (None, None) if bounds is None else bounds[j]
        lo = float(col.min()) if declared_lo is None else float(declared_lo)
        hi = float(col.max()) if declared_hi is None else float(declared_hi)
        if declared_lo is not None and col.min() < declared_lo:
            raise ValueError(
                f"column {j} has value {col.min()} below declared lower bound {declared_lo}"
            )
        if declared_hi is not None and col.max() > declared_hi:
            raise ValueError(
                f"column {j} has value {col.max()} above declared upper bound {declared_hi}"
            )
        if hi == lo:
            result[:, j] = 0.5
            continue
        if pol == "higher_is_better":
            result[:, j] = (col - lo) / (hi - lo)
        elif pol == "lower_is_better":
            result[:, j] = (hi - col) / (hi - lo)
        else:
            raise ValueError(f"unknown polarity {pol!r} for column {j}")
    return result
