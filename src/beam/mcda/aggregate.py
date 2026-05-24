"""Aggregate normalized scores into per-tool composite scores."""

from __future__ import annotations

import numpy as np
from pymcdm.methods import WSM


def _identity_normalization(matrix: np.ndarray, cost: bool | None = None) -> np.ndarray:
    """Return the matrix unchanged.

    beam normalizes scores before aggregation, so the matrix already lies in
    [0, 1] with every column oriented higher is better. This passthrough lets
    pymcdm operate on that matrix directly instead of normalizing it again.
    """
    return matrix


def weighted_sum(
    normalized: np.ndarray,
    weights: np.ndarray,
) -> np.ndarray:
    """Simple additive weighting (SAW): per-tool dot product of scores and weights.

    The computation is delegated to ``pymcdm.methods.WSM`` with an identity
    normalization, so every aggregation in beam runs on the same engine.
    pymcdm runs directly on beam's already normalized matrix, with all criteria
    typed as profit (+1) because the matrix is oriented higher is better.

    Parameters
    ----------
    normalized: 2D array, shape (n_tools, n_metrics), values in [0, 1].
    weights: 1D array, length n_metrics, non-negative; usually sums to 1.

    Returns
    -------
    1D array of length n_tools, the composite score per tool.
    """
    normalized = np.asarray(normalized, dtype=float)
    weights = np.asarray(weights, dtype=float)
    if normalized.ndim != 2:
        raise ValueError(f"normalized must be 2D; got shape {normalized.shape}")
    if weights.ndim != 1:
        raise ValueError(f"weights must be 1D; got shape {weights.shape}")
    if weights.shape[0] != normalized.shape[1]:
        raise ValueError(
            f"weights length {weights.shape[0]} does not match number of "
            f"metrics {normalized.shape[1]}"
        )
    if np.any(weights < 0):
        raise ValueError("weights must be non-negative")
    types = np.ones(normalized.shape[1])
    method = WSM(normalization_function=_identity_normalization)
    return method(normalized, weights, types, validation=False)


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
