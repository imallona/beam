"""TOPSIS aggregation: rank tools by their distance from the ideal solution."""

from __future__ import annotations

import numpy as np
from pymcdm.methods import TOPSIS

from ._missing import require_complete


def _identity_normalization(matrix: np.ndarray, cost: bool | None = None) -> np.ndarray:
    """Return the matrix unchanged.

    beam normalizes scores before aggregation, so the matrix already lies in
    [0, 1] with every column oriented higher is better. This passthrough lets
    pymcdm operate on that matrix directly instead of normalizing it again.
    """
    return matrix


def topsis(normalized: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Compute TOPSIS relative-closeness scores per tool.

    The input is the matrix produced by ``min_max_normalize``: values in
    [0, 1] with every column oriented so higher is better. The function
    multiplies each column by its weight to obtain the weighted matrix V.
    The ideal solution A+ is the per-metric maximum of V; the anti-ideal
    A- is the per-metric minimum. Each tool's score is its relative
    closeness to the ideal:

        closeness(i) = D-(i) / (D+(i) + D-(i))

    where D+(i) and D-(i) are the Euclidean distances from tool i to A+
    and A-. Higher closeness is better.

    The computation is delegated to ``pymcdm.methods.TOPSIS`` with an
    identity normalization, so pymcdm runs directly on beam's already
    normalized matrix, and with all criteria typed as profit (+1) because the
    matrix is oriented higher is better. The native loop has been replaced by
    that call.

    For a single tool, or when all tools are identical on every metric,
    D+ + D- is zero and closeness is undefined. pymcdm returns a not-a-number
    there, so beam intercepts that case and returns 0.5 in those rows, the
    same convention as before, so the caller still gets a usable vector.

    Parameters
    ----------
    normalized
        Shape ``(n_tools, n_metrics)``, values in [0, 1].
    weights
        Shape ``(n_metrics,)``, non-negative; typically sums to 1.

    Returns
    -------
    np.ndarray
        Shape ``(n_tools,)``, closeness in [0, 1].
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
    require_complete(normalized, where="topsis")

    types = np.ones(normalized.shape[1])
    method = TOPSIS(normalization_function=_identity_normalization)
    with np.errstate(invalid="ignore"):
        closeness = method(normalized, weights, types, validation=False)

    # pymcdm yields a not-a-number when the ideal and anti-ideal coincide for a
    # row, which happens for a single tool or for rows identical on every
    # metric. beam fills those with 0.5 so the result stays usable.
    return np.where(np.isfinite(closeness), closeness, 0.5)
