"""Weight vectors for MCDA aggregation."""

from __future__ import annotations

import numpy as np


def equal_weights(n_metrics: int) -> np.ndarray:
    """Return a vector of ``n_metrics`` equal weights that sum to 1."""
    if n_metrics < 1:
        raise ValueError(f"n_metrics must be at least 1; got {n_metrics}")
    return np.full(n_metrics, 1.0 / n_metrics)


def entropy_weights(normalised: np.ndarray) -> np.ndarray:
    """Shannon entropy weights for a [0, 1] normalised tool by metric matrix.

    The principle: a metric on which every tool scores the same offers no
    discrimination and should not influence the ranking. A metric on which
    the tools spread out widely should weigh more. Shannon entropy is the
    canonical way to measure that spread.

    Algorithm:

    1. Turn each column into a probability mass by dividing by its sum:
       ``p[i, j] = normalised[i, j] / sum_k normalised[k, j]``.
    2. Compute the per-column entropy
       ``E[j] = -(1 / ln n_tools) * sum_i p[i, j] * ln p[i, j]``,
       using the convention ``0 * ln 0 = 0``.
    3. Compute the per-column divergence ``d[j] = 1 - E[j]``.
    4. Return weights ``w[j] = d[j] / sum_k d[k]``.

    The 1 / ln n_tools factor scales E into [0, 1], so d is also in [0, 1].

    If every column has uniform variation, every divergence is zero and the
    weight vector would otherwise be 0 / 0. In that case the function falls
    back to equal weights.

    Parameters
    ----------
    normalised
        Shape ``(n_tools, n_metrics)``, values in [0, 1] (non-negative).

    Returns
    -------
    np.ndarray
        Shape ``(n_metrics,)``, non-negative weights summing to 1.

    Notes
    -----
    Because the algorithm normalises each column to a probability mass
    before computing entropy, the weights are invariant under positive
    rescaling of any single column: multiplying column j by a positive
    constant leaves ``w`` unchanged.
    """
    normalised = np.asarray(normalised, dtype=float)
    if normalised.ndim != 2:
        raise ValueError(f"normalised must be 2D; got shape {normalised.shape}")
    n_tools, n_metrics = normalised.shape
    if n_tools < 2:
        raise ValueError(
            f"entropy_weights needs at least 2 tools to measure variability; got {n_tools}"
        )
    if np.any(normalised < 0):
        raise ValueError("normalised must contain non-negative values")

    col_sums = normalised.sum(axis=0)
    safe_sums = np.where(col_sums > 0, col_sums, 1.0)
    p = normalised / safe_sums[None, :]

    # 0 * ln 0 = 0 by convention. np.where eagerly evaluates both branches,
    # so we silence the harmless log(0) warning rather than rewrite with a mask.
    with np.errstate(divide="ignore", invalid="ignore"):
        log_p = np.where(p > 0, np.log(p), 0.0)
    k = 1.0 / np.log(n_tools)
    entropy = -k * (p * log_p).sum(axis=0)

    divergence = 1.0 - entropy
    total = divergence.sum()
    if total <= 1e-12:
        return np.full(n_metrics, 1.0 / n_metrics)
    return divergence / total
