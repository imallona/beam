"""PROMETHEE II aggregation: rank tools by net outranking flow over pairwise comparisons."""

from __future__ import annotations

import numpy as np
from pymcdm.methods import PROMETHEE_II

from ._missing import require_complete


def promethee_ii(normalized: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Compute PROMETHEE II net outranking flows per tool.

    PROMETHEE II (Brans and Vincke 1985) compares every ordered pair of
    tools on each metric and aggregates the comparisons into one net flow
    per tool. For an ordered pair (a, b) and metric j the difference is
    d_j(a, b) = x_aj - x_bj on a higher-is-better column. A preference
    function P maps that difference to a degree of preference for a over b
    in [0, 1]. The default is the Type I (usual) preference function, which
    expresses strict dominance per criterion:

        P(d) = 1 if d > 0, else 0

    so a strictly outscores b on metric j as soon as it scores higher,
    regardless of the size of the gap, and an equal score yields no
    preference. The aggregated preference of a over b is the weighted sum
    over metrics:

        pi(a, b) = sum_j w_j * P(d_j(a, b))

    The positive flow phi_plus(a) averages pi(a, b) over the other tools,
    measuring how much a outranks the rest. The negative flow phi_minus(a)
    averages pi(b, a), measuring how much the rest outrank a. Both divide by
    n_tools - 1. The net flow is

        phi(a) = phi_plus(a) - phi_minus(a)

    and is the PROMETHEE II preference score. It is already higher is better
    (the most-preferred tool has the largest net flow) and lies in
    [-1, 1], so this function returns phi unchanged and ``beam.mcda.rank``
    (1 = highest score) gives the ranking.

    The net flow is computed by ``pymcdm.methods.PROMETHEE_II`` with the
    ``"usual"`` preference function and all criteria typed as profit (+1),
    because the matrix is oriented higher is better. The native pairwise loop
    has been replaced by that call.

    The diagonal pair (a, a) has d = 0, so P(0) = 0 contributes nothing and
    a tool never outranks itself. With a single tool there is no other tool
    to compare against; the function returns a single zero in that case.

    Extension point. Brans and Vincke define six preference functions. The
    other five (U-shape, V-shape, level, linear with indifference and
    preference thresholds, Gaussian) introduce an indifference threshold q,
    below which a difference is treated as no preference, and a preference
    threshold p, above which preference is full, with a shape in between.
    These soften the all-or-nothing behavior of the usual function and need
    per-metric q and p in the metric's own units. To add them, pass the chosen
    preference function name and its thresholds to ``PROMETHEE_II`` through a
    new argument; the rest of this function does not change. The usual function
    is the default because it needs no thresholds and so makes no scale
    assumption beyond the higher-is-better orientation already imposed on the
    input.

    Parameters
    ----------
    normalized
        Shape ``(n_tools, n_metrics)``, values in [0, 1], higher is better.
    weights
        Shape ``(n_metrics,)``, non-negative; typically sums to 1.

    Returns
    -------
    np.ndarray
        Shape ``(n_tools,)``, the net outranking flow phi, higher is better.

    References
    ----------
    Brans, J.-P. and Vincke, P. A preference ranking organisation method:
    the PROMETHEE method for multiple criteria decision-making. Management
    Science 31(6), 647-656 (1985).
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
    require_complete(normalized, where="promethee_ii")

    n_tools = normalized.shape[0]
    if n_tools < 2:
        return np.zeros(n_tools)

    types = np.ones(normalized.shape[1])
    return PROMETHEE_II("usual")(normalized, weights, types, validation=False)
