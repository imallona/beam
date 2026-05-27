"""COMET aggregation: rank tools by triangular fuzzy interpolation over characteristic objects.

COMET is the Characteristic Objects METhod of Salabun 2015. It is rank
reversal free: adding or removing an alternative cannot change the relative
order of the others, because the model is fit on a fixed grid of
characteristic objects and not on the alternatives themselves.

The method needs an expert who, for every pair of characteristic objects,
says which one is preferred. In an automated pipeline there is no human
expert, so beam uses the simple additive weighting (weighted sum) of a
characteristic object's coordinates as the expert rule: characteristic
object a is preferred to b when its weighted sum is larger, and the two are
equal when their weighted sums are equal. This is a deterministic, auditable
stand-in for the human pairwise judgement.

The COMET machinery is delegated to ``pymcdm.methods.COMET``. beam supplies
the characteristic values and a ``pymcdm.methods.comet_tools.FunctionExpert``
that applies the weighted-sum rule above. pymcdm then builds the Matrix of
Expert Judgement, the Summed Judgement, the per-object preference, and the
triangular fuzzy interpolation. The native implementation of those steps has
been replaced by that call.

Reference: Salabun, W. (2015). The Characteristic Objects Method: A New
Distance-based Approach to Multicriteria Decision-making Problems. Journal of
Multi-Criteria Decision Analysis, 22(1-2), 37-50.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from pymcdm.methods import COMET
from pymcdm.methods.comet_tools import FunctionExpert

from ._missing import require_complete


def _weighted_sum_expert(weights: np.ndarray) -> Callable[[np.ndarray, np.ndarray], float]:
    """Build the pairwise expert function used by COMET.

    The returned function compares two characteristic objects by the weighted
    sum of their coordinates. It returns 1.0 when the first object scores
    higher, 0.0 when it scores lower, and 0.5 on a tie. This is the rule
    ``pymcdm.methods.comet_tools.FunctionExpert`` expects, and it reproduces
    beam's automated weighted-sum judgement.

    Parameters
    ----------
    weights
        Shape ``(n_metrics,)``, non-negative.

    Returns
    -------
    Callable
        A function ``(object_a, object_b) -> float`` in {0.0, 0.5, 1.0}.
    """

    def expert(object_a: np.ndarray, object_b: np.ndarray) -> float:
        difference = float(object_a @ weights - object_b @ weights)
        if difference > 0:
            return 1.0
        if difference < 0:
            return 0.0
        return 0.5

    return expert


def comet(
    normalized: np.ndarray,
    weights: np.ndarray,
    characteristic_values: np.ndarray | list[list[float]] | None = None,
) -> np.ndarray:
    """Compute COMET preference scores per tool.

    The input is the matrix produced by ``min_max_normalize``: values in
    [0, 1] with every column oriented so higher is better. COMET first fixes a
    small set of characteristic values per criterion and forms characteristic
    objects as their Cartesian product. A weighted-sum expert (see
    ``_weighted_sum_expert``) ranks the objects and assigns each a preference
    P. Each criterion value is then turned into triangular fuzzy memberships
    over its characteristic values, and an alternative's score is the sum over
    characteristic objects of P times the product of the matching memberships
    across criteria. Higher is better. These steps are carried out by
    ``pymcdm.methods.COMET``.

    Because the model is fit on the fixed grid of characteristic objects,
    COMET is rank reversal free: adding or removing an alternative does not
    change the scores of the others.

    Parameters
    ----------
    normalized
        Shape ``(n_tools, n_metrics)``, values in [0, 1].
    weights
        Shape ``(n_metrics,)``, non-negative; typically sums to 1.
    characteristic_values
        Optional characteristic values per criterion. Either a 2D array-like
        of shape ``(n_metrics, k)`` or a list of ``n_metrics`` sequences, each
        with the same length k of 2 or 3. When omitted, the endpoints of the
        normalized scale, ``[0.0, 1.0]`` for every criterion, are used. Values
        per criterion must be sorted and strictly increasing.

    Returns
    -------
    np.ndarray
        Shape ``(n_tools,)``, COMET preference in [0, 1].

    Notes
    -----
    The expert function is the weighted sum of a characteristic object's
    coordinates, a deterministic stand-in for the human pairwise judgement
    that COMET assumes. See the module docstring and
    docs/explanations/comet.md.

    References
    ----------
    Salabun, W. (2015). The Characteristic Objects Method: A New
    Distance-based Approach to Multicriteria Decision-making Problems. Journal
    of Multi-Criteria Decision Analysis, 22(1-2), 37-50.
    """
    normalized = np.asarray(normalized, dtype=float)
    weights = np.asarray(weights, dtype=float)

    if normalized.ndim != 2:
        raise ValueError(f"normalized must be 2D; got shape {normalized.shape}")
    if weights.ndim != 1:
        raise ValueError(f"weights must be 1D; got shape {weights.shape}")
    n_metrics = normalized.shape[1]
    if weights.shape[0] != n_metrics:
        raise ValueError(
            f"weights length {weights.shape[0]} does not match number of metrics {n_metrics}"
        )
    if np.any(weights < 0):
        raise ValueError("weights must be non-negative")
    require_complete(normalized, where="comet")

    per_criterion_values = _resolve_characteristic_values(characteristic_values, n_metrics)

    expert = FunctionExpert(_weighted_sum_expert(weights))
    with np.errstate(invalid="ignore"):
        model = COMET(per_criterion_values, expert)
        scores = model(normalized)

    # When every characteristic object falls in one preference group, pymcdm
    # divides by a zero range and returns not-a-number. That happens when the
    # weighted-sum expert cannot separate the objects, for example with
    # all-zero weights. beam returns 0.5 there so the result stays usable.
    return np.where(np.isfinite(scores), scores, 0.5)


def _resolve_characteristic_values(
    characteristic_values: np.ndarray | list[list[float]] | None, n_metrics: int
) -> list[np.ndarray]:
    """Validate caller-supplied characteristic values or build the default grid.

    Parameters
    ----------
    characteristic_values
        The argument passed to ``comet``; see that function.
    n_metrics
        Number of criteria the values must cover.

    Returns
    -------
    list of np.ndarray
        One sorted 1D array of characteristic values per criterion.
    """
    if characteristic_values is None:
        return [np.array([0.0, 1.0]) for _ in range(n_metrics)]

    per_criterion = [np.asarray(values, dtype=float) for values in characteristic_values]
    if len(per_criterion) != n_metrics:
        raise ValueError(
            f"characteristic_values must have {n_metrics} entries, one per "
            f"metric; got {len(per_criterion)}"
        )
    for criterion, values in enumerate(per_criterion):
        if values.ndim != 1 or values.shape[0] < 2:
            raise ValueError(
                f"characteristic_values for metric {criterion} must be a 1D "
                f"sequence of at least 2 values"
            )
        if np.any(np.diff(values) <= 0):
            raise ValueError(
                f"characteristic_values for metric {criterion} must be strictly increasing"
            )
    return per_criterion
