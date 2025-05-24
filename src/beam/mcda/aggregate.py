"""Aggregate normalised scores into per-tool composite scores."""

from __future__ import annotations

import numpy as np


def weighted_sum(
    normalised: np.ndarray,
    weights: np.ndarray,
) -> np.ndarray:
    """Simple additive weighting (SAW): per-tool dot product of scores and weights.

    Parameters
    ----------
    normalised: 2D array, shape (n_tools, n_metrics), values in [0, 1].
    weights: 1D array, length n_metrics, non-negative; usually sums to 1.

    Returns
    -------
    1D array of length n_tools, the composite score per tool.
    """
    normalised = np.asarray(normalised, dtype=float)
    weights = np.asarray(weights, dtype=float)
    if normalised.ndim != 2:
        raise ValueError(f"normalised must be 2D; got shape {normalised.shape}")
    if weights.ndim != 1:
        raise ValueError(f"weights must be 1D; got shape {weights.shape}")
    if weights.shape[0] != normalised.shape[1]:
        raise ValueError(
            f"weights length {weights.shape[0]} does not match number of "
            f"metrics {normalised.shape[1]}"
        )
    if np.any(weights < 0):
        raise ValueError("weights must be non-negative")
    return normalised @ weights


def rank(scores: np.ndarray) -> np.ndarray:
    """Return 1-based ranks of ``scores``, with 1 = best (highest score).

    Ties share the lowest rank (competition ranking, "1224" style).
    """
    scores = np.asarray(scores, dtype=float)
    order = np.argsort(-scores, kind="stable")
    ranks = np.empty(scores.shape[0], dtype=int)
    current_rank = 1
    for i, idx in enumerate(order):
        if i > 0 and scores[idx] < scores[order[i - 1]]:
            current_rank = i + 1
        ranks[idx] = current_rank
    return ranks
