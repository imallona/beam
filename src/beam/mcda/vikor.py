"""VIKOR aggregation: rank tools by a compromise between group utility and individual regret."""

from __future__ import annotations

import numpy as np
from pymcdm.methods import VIKOR

from ._missing import require_complete


def vikor(normalized: np.ndarray, weights: np.ndarray, v: float = 0.5) -> np.ndarray:
    """Compute VIKOR compromise scores per tool.

    VIKOR (Opricovic 1998; Opricovic and Tzeng 2004) ranks tools by how
    close they sit to an ideal solution, balancing two views. The group
    utility S is the weighted Manhattan distance from the ideal, so it
    rewards a tool that does well summed across all metrics. The individual
    regret R is the weighted Chebyshev distance, so it penalizes a tool's
    single worst metric. The compromise index Q blends the two:

        Q_i = v * (S_i - S_star) / (S_minus - S_star)
              + (1 - v) * (R_i - R_star) / (R_minus - R_star)

    where S_star and R_star are the column minima of S and R, S_minus and
    R_minus their maxima, and v in [0, 1] weights group utility against
    regret. With v = 1 the index follows S alone (majority rule, maximum
    group utility); with v = 0 it follows R alone (minimum individual
    regret); v = 0.5 is the usual consensus default.

    The input is already normalized to [0, 1] with every column oriented so
    higher is better, so per metric the best value f_star is the column max
    and the worst f_minus is the column min. The per-criterion distance for
    tool i on metric j is

        d_ij = (f_star_j - x_ij) / (f_star_j - f_minus_j)

    weighted by the metric weight. A criterion with zero range
    (f_star == f_minus) carries no information between tools and contributes
    nothing.

    The compromise index Q is computed by ``pymcdm.methods.VIKOR`` with its
    normalization disabled, so pymcdm runs on beam's already normalized
    matrix. The native S, R and Q loop has been replaced by that call.

    Orientation convention. The canonical VIKOR Q is lower is better: the
    tool with the smallest Q is the preferred compromise. beam aggregations
    must return a higher-is-better preference score so that ``beam.mcda.rank``
    (1 = highest score) gives the ranking. This function therefore returns
    ``-Q``. Negating preserves the order exactly: the tool with the smallest
    Q has the largest ``-Q`` and so ranks first. We return ``-Q`` rather than
    a rescaled ``1 - Q`` to avoid a second normalization step that would
    discard the absolute spacing of the Q values.

    Degenerate cases are guarded. If every tool is identical on a metric the
    column range is zero and that metric carries no information. pymcdm
    rejects a constant column, so beam drops such columns before the call.
    When every column is constant, which happens for a single tool or for
    rows identical on every metric, there is nothing to separate the tools,
    so beam returns a constant score and leaves all tools tied.

    Parameters
    ----------
    normalized
        Shape ``(n_tools, n_metrics)``, values in [0, 1], higher is better.
    weights
        Shape ``(n_metrics,)``, non-negative; typically sums to 1.
    v
        Compromise parameter in [0, 1]. Weight on group utility S versus
        individual regret R. Default 0.5.

    Returns
    -------
    np.ndarray
        Shape ``(n_tools,)``, the higher-is-better preference score ``-Q``.

    References
    ----------
    Opricovic, S. Multicriteria optimization of civil engineering systems.
    Faculty of Civil Engineering, Belgrade (1998).

    Opricovic, S. and Tzeng, G.-H. Compromise solution by MCDM methods: a
    comparative analysis of VIKOR and TOPSIS. European Journal of
    Operational Research 156(2), 445-455 (2004).
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
    if not 0.0 <= v <= 1.0:
        raise ValueError(f"v must be in [0, 1]; got {v}")
    require_complete(normalized, where="vikor")

    column_range = normalized.max(axis=0) - normalized.min(axis=0)
    informative = column_range > 0
    if not informative.any():
        return np.zeros(normalized.shape[0])

    kept = normalized[:, informative]
    kept_weights = weights[informative]
    types = np.ones(kept.shape[1])
    with np.errstate(invalid="ignore"):
        q = VIKOR(normalization_function=None, v=v)(kept, kept_weights, types, validation=False)

    # pymcdm divides by the range of the group utility S and the regret R. When
    # either range is zero, for example when several rows are identical, it
    # returns not-a-number. beam then treats every tool as tied by returning a
    # constant score, the same outcome as the previous native guard.
    if not np.all(np.isfinite(q)):
        return np.zeros(normalized.shape[0])
    return -q
