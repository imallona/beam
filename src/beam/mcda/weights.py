"""Weight vectors for MCDA aggregation.

These weighting schemes stay native to beam rather than delegating to pymcdm.
pymcdm's weight functions sum-normalize internally and reject zeros, but beam's
min-max normalization routinely maps the worst tool to zero, and AHP is not in
pymcdm.
"""

from __future__ import annotations

import warnings

import numpy as np

from ._missing import require_complete


def equal_weights(n_metrics: int) -> np.ndarray:
    """Return a vector of ``n_metrics`` equal weights that sum to 1."""
    if n_metrics < 1:
        raise ValueError(f"n_metrics must be at least 1; got {n_metrics}")
    return np.full(n_metrics, 1.0 / n_metrics)


def entropy_weights(normalized: np.ndarray) -> np.ndarray:
    """Shannon entropy weights for a [0, 1] normalized tool by metric matrix.

    The principle: a metric on which every tool scores the same offers no
    discrimination and should not influence the ranking. A metric on which
    the tools spread out widely should weigh more. Shannon entropy is the
    canonical way to measure that spread.

    Algorithm:

    1. Turn each column into a probability mass by dividing by its sum:
       ``p[i, j] = normalized[i, j] / sum_k normalized[k, j]``.
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
    normalized
        Shape ``(n_tools, n_metrics)``, values in [0, 1] (non-negative).

    Returns
    -------
    np.ndarray
        Shape ``(n_metrics,)``, non-negative weights summing to 1.

    Notes
    -----
    Because the algorithm normalizes each column to a probability mass
    before computing entropy, the weights are invariant under positive
    rescaling of any single column: multiplying column j by a positive
    constant leaves ``w`` unchanged.
    """
    normalized = np.asarray(normalized, dtype=float)
    if normalized.ndim != 2:
        raise ValueError(f"normalized must be 2D; got shape {normalized.shape}")
    require_complete(normalized, where="entropy_weights")
    n_tools, n_metrics = normalized.shape
    if n_tools < 2:
        raise ValueError(
            f"entropy_weights needs at least 2 tools to measure variability; got {n_tools}"
        )
    if np.any(normalized < 0):
        raise ValueError("normalized must contain non-negative values")

    col_sums = normalized.sum(axis=0)
    safe_sums = np.where(col_sums > 0, col_sums, 1.0)
    p = normalized / safe_sums[None, :]

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


def _check_objective_matrix(normalized: np.ndarray, caller: str) -> np.ndarray:
    """Validate a normalized tool by metric matrix for an objective weighting.

    Parameters
    ----------
    normalized
        Candidate matrix. Coerced to a float array.
    caller
        Name of the calling function, used in the error message.

    Returns
    -------
    np.ndarray
        The validated matrix as a float array of shape ``(n_tools, n_metrics)``.

    Raises
    ------
    ValueError
        If the matrix is not 2D, has fewer than two tools, or holds a
        negative value.
    """
    normalized = np.asarray(normalized, dtype=float)
    if normalized.ndim != 2:
        raise ValueError(f"normalized must be 2D; got shape {normalized.shape}")
    require_complete(normalized, where=caller)
    n_tools = normalized.shape[0]
    if n_tools < 2:
        raise ValueError(f"{caller} needs at least 2 tools to measure variability; got {n_tools}")
    if np.any(normalized < 0):
        raise ValueError("normalized must contain non-negative values")
    return normalized


def standard_deviation_weights(normalized: np.ndarray) -> np.ndarray:
    """Standard deviation weights for a [0, 1] normalized tool by metric matrix.

    The principle is the same as for entropy: a metric that spreads the tools
    out should weigh more than one on which they all score alike. Standard
    deviation measures that spread directly, without converting the column to
    a probability mass first. The weight of each metric is its sample standard
    deviation divided by the sum of the standard deviations across metrics.

    If every column is constant the total spread is zero and the weight vector
    would otherwise be 0 / 0. In that case the function falls back to equal
    weights.

    Parameters
    ----------
    normalized
        Shape ``(n_tools, n_metrics)``, values in [0, 1] (non-negative).

    Returns
    -------
    np.ndarray
        Shape ``(n_metrics,)``, non-negative weights summing to 1.

    Notes
    -----
    The standard deviation is the sample version (``ddof=1``). Unlike entropy,
    these weights are not invariant under rescaling of a column, so the input
    is expected to be already normalized to a common scale.

    References
    ----------
    Diakoulaki, D., Mavrotas, G., Papayannakis, L. Determining objective
    weights in multiple criteria problems: the CRITIC method. Computers and
    Operations Research 22 (1995), which reviews the standard deviation
    approach as the simpler precursor to CRITIC.
    """
    normalized = _check_objective_matrix(normalized, "standard_deviation_weights")
    n_metrics = normalized.shape[1]

    std = np.std(normalized, axis=0, ddof=1)
    total = std.sum()
    if total <= 1e-12:
        return np.full(n_metrics, 1.0 / n_metrics)
    return std / total


def critic_weights(normalized: np.ndarray) -> np.ndarray:
    """CRITIC weights for a [0, 1] normalized tool by metric matrix.

    CRITIC (CRiteria Importance Through Intercriteria Correlation) combines two
    ideas. A metric should weigh more when its scores spread out, measured by
    standard deviation, and when it conflicts with the other metrics, measured
    by low correlation. A metric that merely repeats information already carried
    by another metric should not be counted twice, so a high positive
    correlation lowers the weight.

    Algorithm:

    1. Min-max rescale each column to [0, 1] so the contrast measure does not
       depend on the original units.
    2. Compute the per-column sample standard deviation.
    3. Compute the Pearson correlation matrix across columns.
    4. For each metric, sum ``1 - correlation`` over all metrics, including the
       self term which contributes ``1 - 1 = 0``. This is the conflict score.
    5. Multiply the standard deviation by the conflict score to get the
       information content, then normalize the information content to sum to 1.

    If every column is constant there is no spread and no contrast, and the
    function falls back to equal weights.

    Parameters
    ----------
    normalized
        Shape ``(n_tools, n_metrics)``, values in [0, 1] (non-negative).

    Returns
    -------
    np.ndarray
        Shape ``(n_metrics,)``, non-negative weights summing to 1.

    Notes
    -----
    A single metric (one column) has no other metric to conflict with, so the
    conflict score is zero and the method cannot assign a weight. The function
    returns equal weights in that case, which for one column is just ``[1.0]``.

    References
    ----------
    Diakoulaki, D., Mavrotas, G., Papayannakis, L. Determining objective
    weights in multiple criteria problems: the CRITIC method. Computers and
    Operations Research 22 (1995).
    """
    normalized = _check_objective_matrix(normalized, "critic_weights")
    n_metrics = normalized.shape[1]

    col_min = normalized.min(axis=0)
    col_max = normalized.max(axis=0)
    spread = col_max - col_min
    constant = spread <= 1e-12
    # A constant column min-max maps to all ones, matching the standard CRITIC
    # convention and giving that column zero standard deviation.
    safe_spread = np.where(constant, 1.0, spread)
    rescaled = np.where(constant, 1.0, (normalized - col_min) / safe_spread)

    std = np.std(rescaled, axis=0, ddof=1)
    # A constant column has zero variance, so its correlation with anything is
    # undefined and numpy returns nan. Such a column also has std 0, so its
    # information content is zero regardless of conflict; treat the undefined
    # correlation as zero conflict so the arithmetic stays finite.
    with np.errstate(invalid="ignore", divide="ignore"):
        correlation = np.corrcoef(rescaled, rowvar=False)
    correlation = np.atleast_2d(correlation)
    correlation = np.where(np.isfinite(correlation), correlation, 1.0)
    conflict = np.sum(1.0 - correlation, axis=0)

    information = std * conflict
    total = information.sum()
    if total <= 1e-12:
        return np.full(n_metrics, 1.0 / n_metrics)
    return information / total


def merec_weights(normalized: np.ndarray) -> np.ndarray:
    """MEREC weights for a [0, 1] normalized tool by metric matrix.

    MEREC (Method based on the Removal Effects of Criteria) weights each metric
    by how much the overall performance scores change when that metric is
    dropped. A metric whose removal barely moves the scores carries little
    information and gets a small weight. A metric whose removal shifts the
    scores a lot gets a large weight.

    Algorithm, treating every metric as higher is better:

    1. Linear cost normalization of each column: divide the column minimum by
       each entry, which maps the best tool toward a small value and keeps the
       multiplicative structure of the scores.
    2. Aggregate each tool with a logarithmic measure
       ``S[i] = ln(1 + (1 / n_metrics) * sum_j |ln nmatrix[i, j]|)``.
    3. For each metric j, recompute the same aggregate with column j removed,
       giving ``S_without_j[i]``.
    4. The removal effect of metric j is the total absolute change it causes,
       ``E[j] = sum_i |S_without_j[i] - S[i]|``.
    5. Return weights ``w[j] = E[j] / sum_k E[k]``.

    If every metric has the same removal effect of zero, the function falls
    back to equal weights.

    Parameters
    ----------
    normalized
        Shape ``(n_tools, n_metrics)``, values in (0, 1] (strictly positive).

    Returns
    -------
    np.ndarray
        Shape ``(n_metrics,)``, non-negative weights summing to 1.

    Raises
    ------
    ValueError
        If any value is zero. MEREC takes the logarithm of the normalized
        scores, which is undefined at zero, so the input must be strictly
        positive. Normalizations that can emit a hard zero, such as plain
        min-max, should be replaced by one bounded away from zero, for example
        the logistic z-score strategy, before calling MEREC.

    References
    ----------
    Keshavarz-Ghorabaee, M., Amiri, M., Zavadskas, E. K., Turskis, Z.,
    Antucheviciene, J. Determination of Objective Weights Using a New Method
    Based on the Removal Effects of Criteria (MEREC). Symmetry 13 (2021).
    """
    normalized = _check_objective_matrix(normalized, "merec_weights")
    if np.any(normalized == 0):
        raise ValueError(
            "merec_weights takes the logarithm of the scores and cannot handle "
            "zero values; use a normalization bounded away from zero"
        )
    n_metrics = normalized.shape[1]

    col_min = normalized.min(axis=0)
    cost_normalized = col_min[None, :] / normalized
    log_terms = np.abs(np.log(cost_normalized))

    full = np.log1p(log_terms.sum(axis=1) / n_metrics)
    removal_effect = np.zeros(n_metrics)
    for j in range(n_metrics):
        without_j = np.delete(log_terms, j, axis=1)
        reduced = np.log1p(without_j.sum(axis=1) / n_metrics)
        removal_effect[j] = np.sum(np.abs(reduced - full))

    total = removal_effect.sum()
    if total <= 1e-12:
        return np.full(n_metrics, 1.0 / n_metrics)
    return removal_effect / total


# Saaty's random consistency index, the average consistency index of many
# randomly generated reciprocal matrices, indexed by matrix order n. Index 0
# and 1 are 0 because a matrix of order 1 or 2 is always consistent. From
# Saaty (1980). Order 1 to 10 covers the practical range of pairwise sets.
_SAATY_RANDOM_INDEX = (
    0.0,
    0.0,
    0.0,
    0.58,
    0.90,
    1.12,
    1.24,
    1.32,
    1.41,
    1.45,
    1.49,
)


class InconsistentPairwiseMatrixError(ValueError):
    """Raised when an AHP pairwise comparison matrix is too inconsistent.

    The consistency ratio exceeds the 0.1 threshold from Saaty (1980), so the
    judgments are not coherent enough to trust the derived weights.
    """


def ahp_weights(
    pairwise_comparison_matrix: np.ndarray,
    raise_on_inconsistency: bool = False,
) -> tuple[np.ndarray, float]:
    """Analytic Hierarchy Process weights from a pairwise comparison matrix.

    AHP is a subjective scheme. Unlike the objective schemes in this module,
    which read the spread of the score matrix, AHP needs a user-supplied square
    matrix of pairwise judgments. Entry ``A[i, j]`` states how many times more
    important metric i is than metric j, on Saaty's 1 to 9 scale. The matrix
    must be positive and reciprocal, meaning ``A[j, i] = 1 / A[i, j]`` and a
    unit diagonal.

    The weights are the principal right eigenvector of the matrix, normalized
    to sum to 1. The function also returns a consistency ratio that measures
    how coherent the judgments are. A perfectly consistent matrix gives a ratio
    of 0. Saaty advises that a ratio above 0.1 means the judgments should be
    revised.

    Algorithm:

    1. Compute the eigenvalues and right eigenvectors of the matrix.
    2. Take the eigenvector belonging to the largest real eigenvalue
       ``lambda_max``, drop any tiny imaginary part, take the absolute value so
       the weights are positive, and normalize it to sum to 1.
    3. Compute the consistency index ``CI = (lambda_max - n) / (n - 1)``.
    4. Compute the consistency ratio ``CR = CI / RI``, where ``RI`` is Saaty's
       random index for order n. For n of 1 or 2 the matrix is always
       consistent and the ratio is defined as 0.

    Parameters
    ----------
    pairwise_comparison_matrix
        Shape ``(n, n)``, positive and reciprocal, with a unit diagonal.
    raise_on_inconsistency
        If True, raise ``InconsistentPairwiseMatrixError`` when the consistency
        ratio exceeds 0.1. If False (the default), return the ratio so the
        caller can decide, and emit a warning.

    Returns
    -------
    tuple of (np.ndarray, float)
        The weight vector of shape ``(n,)`` summing to 1, and the consistency
        ratio.

    Raises
    ------
    ValueError
        If the matrix is not square, not strictly positive, or not reciprocal.
    InconsistentPairwiseMatrixError
        If ``raise_on_inconsistency`` is True and the consistency ratio exceeds
        0.1.

    Warns
    -----
    UserWarning
        If ``raise_on_inconsistency`` is False and the consistency ratio
        exceeds 0.1.

    References
    ----------
    Saaty, T. L. The Analytic Hierarchy Process. McGraw-Hill (1980).
    """
    matrix = np.asarray(pairwise_comparison_matrix, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError(f"pairwise matrix must be square; got shape {matrix.shape}")
    n = matrix.shape[0]
    if n < 1:
        raise ValueError("pairwise matrix must have at least one row")
    if np.any(matrix <= 0):
        raise ValueError("pairwise matrix must be strictly positive")
    if not np.allclose(matrix * matrix.T, 1.0, atol=1e-8):
        raise ValueError("pairwise matrix must be reciprocal: A[j, i] must equal 1 / A[i, j]")

    if n > len(_SAATY_RANDOM_INDEX) - 1:
        raise ValueError(
            f"no Saaty random index tabulated for order {n}; "
            f"supported up to {len(_SAATY_RANDOM_INDEX) - 1}"
        )

    eigenvalues, eigenvectors = np.linalg.eig(matrix)
    principal = int(np.argmax(eigenvalues.real))
    lambda_max = eigenvalues[principal].real
    weights = np.abs(eigenvectors[:, principal].real)
    weights = weights / weights.sum()

    if n <= 2:
        consistency_ratio = 0.0
    else:
        consistency_index = (lambda_max - n) / (n - 1)
        random_index = _SAATY_RANDOM_INDEX[n]
        consistency_ratio = consistency_index / random_index

    if consistency_ratio > 0.1:
        message = (
            f"AHP consistency ratio {consistency_ratio:.3f} exceeds 0.1; "
            "the pairwise judgments are inconsistent and should be revised"
        )
        if raise_on_inconsistency:
            raise InconsistentPairwiseMatrixError(message)
        warnings.warn(message, UserWarning, stacklevel=2)

    return weights, consistency_ratio
