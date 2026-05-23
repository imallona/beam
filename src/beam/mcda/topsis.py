"""TOPSIS aggregation: rank tools by their distance from the ideal solution."""

from __future__ import annotations

import numpy as np


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

    For a single tool, or when all tools are identical on every metric,
    D+ + D- is zero and closeness is undefined. The function returns 0.5
    in those rows so the caller still gets a usable vector.

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

    weighted = normalized * weights[None, :]
    ideal = weighted.max(axis=0)
    anti_ideal = weighted.min(axis=0)

    dist_to_ideal = np.sqrt(((weighted - ideal[None, :]) ** 2).sum(axis=1))
    dist_to_anti = np.sqrt(((weighted - anti_ideal[None, :]) ** 2).sum(axis=1))

    denom = dist_to_ideal + dist_to_anti
    safe_denom = np.where(denom > 0, denom, 1.0)
    return np.where(denom > 0, dist_to_anti / safe_denom, 0.5)
