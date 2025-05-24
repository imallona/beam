"""Normalise a tool by metric score matrix to [0, 1], respecting polarity."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def min_max_normalize(
    scores: np.ndarray,
    polarity: Sequence[str],
) -> np.ndarray:
    """Min-max normalise each column of ``scores`` to [0, 1].

    Higher-is-better metrics map to (x - min) / (max - min). Lower-is-better
    metrics map to (max - x) / (max - min), so the result is always
    higher = better. A column with zero range maps to all 0.5 to avoid
    divide-by-zero and to signal that the column carries no discriminating
    information.

    Parameters
    ----------
    scores: 2D array, shape (n_tools, n_metrics).
    polarity: sequence of "higher_is_better" or "lower_is_better", one entry
        per metric column.

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

    result = np.empty_like(scores)
    for j, pol in enumerate(polarity):
        col = scores[:, j]
        lo, hi = col.min(), col.max()
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
