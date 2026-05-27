"""Aggregate normalized scores into per-tool composite scores."""

from __future__ import annotations

import numpy as np
from pymcdm.methods import WSM

from ._missing import IncompleteMatrixError, require_complete


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

    On a complete matrix the computation is delegated to ``pymcdm.methods.WSM``
    with an identity normalization, so every aggregation in beam runs on the
    same engine. pymcdm runs directly on beam's already normalized matrix, with
    all criteria typed as profit (+1) because the matrix is oriented higher is
    better.

    SAW is the one aggregation with a well-defined form under missing cells that
    does not impute. When ``normalized`` has missing cells, each tool is scored
    on the metrics it was actually measured on, with the weights renormalized
    over that tool's observed support:

        composite(i) = sum_{j observed for i} w_j * x_ij / sum_{j observed for i} w_j

    A complete row reduces to the ordinary weighted sum, so this matches the
    pymcdm path exactly when no cell is missing and the weights sum to one. The
    composites then rest on different metric supports across tools, which the
    caller must surface; ``beam.mcda.run`` does so with a warning under
    ``missing="available"``. A row with no observed metric cannot be scored and
    raises, since there is nothing to average. The distance and pairwise methods
    (TOPSIS, VIKOR, PROMETHEE II, COMET) have no such form and refuse a matrix
    with missing cells outright.

    Parameters
    ----------
    normalized: 2D array, shape (n_tools, n_metrics), values in [0, 1].
    weights: 1D array, length n_metrics, non-negative; usually sums to 1.

    Returns
    -------
    1D array of length n_tools, the composite score per tool.

    Raises
    ------
    IncompleteMatrixError
        If a tool row has no observed metric, so its composite is undefined.
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

    if np.isnan(normalized).any():
        return _available_case_weighted_sum(normalized, weights)

    types = np.ones(normalized.shape[1])
    method = WSM(normalization_function=_identity_normalization)
    return method(normalized, weights, types, validation=False)


def _available_case_weighted_sum(normalized: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Weighted mean over each tool's observed metrics, weights renormalized per tool.

    A row with no observed metric has no value to average and raises an
    ``IncompleteMatrixError`` naming the offending tools.
    """
    observed = ~np.isnan(normalized)
    empty_rows = ~observed.any(axis=1)
    if empty_rows.any():
        rows = np.where(empty_rows)[0].tolist()
        raise IncompleteMatrixError(
            f"weighted_sum: tool rows {rows} have no observed metric, so an "
            "available-case composite is undefined for them. Drop those tools or "
            "analyze the feasible subset."
        )
    filled = np.where(observed, normalized, 0.0)
    weighted = filled * weights[None, :]
    support = (observed * weights[None, :]).sum(axis=1)
    return weighted.sum(axis=1) / support


def rank(scores: np.ndarray) -> np.ndarray:
    """Return 1-based ranks of ``scores``, with 1 = best (highest score).

    Ties share the lowest rank (competition ranking, "1224" style).
    """
    scores = np.asarray(scores, dtype=float)
    require_complete(scores, where="rank")
    order = np.argsort(-scores, kind="stable")
    ranks = np.empty(scores.shape[0], dtype=int)
    current_rank = 1
    for i, idx in enumerate(order):
        if i > 0 and scores[idx] < scores[order[i - 1]]:
            current_rank = i + 1
        ranks[idx] = current_rank
    return ranks
