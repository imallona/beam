"""High-level entry point that runs a full MCDA pipeline in one call."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from .aggregate import rank, weighted_sum
from .normalize import min_max_normalize
from .topsis import topsis
from .weights import entropy_weights, equal_weights


@dataclass(frozen=True)
class Result:
    """Outcome of an MCDA run.

    Holds every intermediate output so the caller can inspect each step,
    compare runs side by side, or feed them into sensitivity analysis. The
    ``weighting`` and ``method`` fields record which named scheme was used,
    or ``"user-supplied"`` when the caller passed an explicit array.
    """

    scores: np.ndarray
    polarity: tuple[str, ...]
    normalised: np.ndarray
    weights: np.ndarray
    composite: np.ndarray
    ranks: np.ndarray
    weighting: str
    method: str


_KNOWN_WEIGHTINGS = ("equal", "entropy")
_KNOWN_METHODS = ("saw", "topsis")


def _resolve_weights(
    weighting,
    normalised: np.ndarray,
) -> tuple[np.ndarray, str]:
    if isinstance(weighting, str):
        if weighting == "equal":
            return equal_weights(normalised.shape[1]), "equal"
        if weighting == "entropy":
            return entropy_weights(normalised), "entropy"
        raise ValueError(f"unknown weighting {weighting!r}; supported: {_KNOWN_WEIGHTINGS}")
    w = np.asarray(weighting, dtype=float)
    if w.shape != (normalised.shape[1],):
        raise ValueError(f"weights array has shape {w.shape}; expected ({normalised.shape[1]},)")
    if np.any(w < 0):
        raise ValueError("weights must be non-negative")
    return w, "user-supplied"


def _resolve_method(method: str):
    if method == "saw":
        return weighted_sum
    if method == "topsis":
        return topsis
    raise ValueError(f"unknown method {method!r}; supported: {_KNOWN_METHODS}")


def run(
    scores,
    polarity: Sequence[str],
    weights="equal",
    method: str = "saw",
) -> Result:
    """Run a full MCDA pipeline from raw scores to per-tool ranks.

    Three steps:

    1. Normalise each column of ``scores`` to [0, 1] using
       ``min_max_normalize``, respecting per-metric polarity. After this
       step every column is oriented so higher is better.
    2. Build a weight vector. Pass ``"equal"`` or ``"entropy"`` for the
       built-in schemes, or pass an explicit array of length
       ``n_metrics``.
    3. Aggregate to one composite score per tool. Pass ``"saw"`` for
       simple additive weighting (the dot product of normalised scores
       and weights) or ``"topsis"`` for distance-to-ideal aggregation.

    Returns a ``Result`` with every intermediate output. Two runs over the
    same scores can be compared by their ``.ranks`` to see how much the
    choice of weighting or method matters.

    The metric card registry is consulted exactly once, before this
    function is called, to look up the polarity per metric. Inside ``run``
    the polarity strings drive normalisation; after that step the
    aggregator (SAW or TOPSIS) sees only the [0, 1] matrix and the weights.
    No other field from the metric cards (``scale_type``, ``range``,
    ``allowed_transformations``, etc.) is currently enforced by the
    pipeline. Use ``beam.cards.polarities_for(metric_ids)`` to source the
    polarity list from the registry rather than hand-typing it.

    Parameters
    ----------
    scores
        Array-like of shape ``(n_tools, n_metrics)``.
    polarity
        Length ``n_metrics`` sequence of ``"higher_is_better"`` or
        ``"lower_is_better"``. Get this from
        ``beam.cards.polarities_for(metric_ids)``.
    weights
        ``"equal"`` (default), ``"entropy"``, or an explicit array of
        length ``n_metrics``.
    method
        ``"saw"`` (default) or ``"topsis"``.

    Returns
    -------
    Result

    Examples
    --------
    >>> import numpy as np
    >>> from beam.mcda import run
    >>> scores = np.array([[0.9, 30.0], [0.7, 50.0]])
    >>> result = run(scores, ["higher_is_better", "lower_is_better"])
    >>> result.ranks.tolist()
    [1, 2]
    """
    scores = np.asarray(scores, dtype=float)
    polarity = tuple(polarity)

    if scores.ndim != 2:
        raise ValueError(f"scores must be 2D; got shape {scores.shape}")
    if len(polarity) != scores.shape[1]:
        raise ValueError(
            f"polarity has {len(polarity)} entries but scores has {scores.shape[1]} columns"
        )

    normalised = min_max_normalize(scores, polarity)
    weight_array, weighting_name = _resolve_weights(weights, normalised)
    aggregate_fn = _resolve_method(method)
    composite = aggregate_fn(normalised, weight_array)
    ranks_arr = rank(composite)

    return Result(
        scores=scores,
        polarity=polarity,
        normalised=normalised,
        weights=weight_array,
        composite=composite,
        ranks=ranks_arr,
        weighting=weighting_name,
        method=method,
    )
