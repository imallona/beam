"""High-level entry point that runs a full MCDA pipeline in one call."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from ..cards import Registry, properties_for
from .aggregate import rank, weighted_sum
from .normalize import Bound, min_max_normalize
from .topsis import topsis
from .validate import validate_for_aggregation
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
    bounds: tuple[Bound, ...] | None = None
    metric_ids: tuple[str, ...] | None = None


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
    bounds: Sequence[Bound] | None = None,
    metric_ids: Sequence[str] | None = None,
) -> Result:
    """Run a full MCDA pipeline from raw scores to per-tool ranks.

    Three steps:

    1. Normalise each column of ``scores`` to [0, 1] using
       ``min_max_normalize``, respecting per-metric polarity and, when
       provided, declared per-metric bounds. After this step every column
       is oriented so higher is better.
    2. Build a weight vector. Pass ``"equal"`` or ``"entropy"`` for the
       built-in schemes, or pass an explicit array of length
       ``n_metrics``.
    3. Aggregate to one composite score per tool. Pass ``"saw"`` for
       simple additive weighting (the dot product of normalised scores
       and weights) or ``"topsis"`` for distance-to-ideal aggregation.

    Returns a ``Result`` with every intermediate output. Two runs over the
    same scores can be compared by their ``.ranks`` to see how much the
    choice of weighting or method matters.

    Use ``run_from_registry`` for the ontology-aware path: it pulls
    polarity and declared bounds from the metric cards, validates the
    requested method against the declared scale types, and feeds the
    result into this function.

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
    bounds
        Optional list of ``(lower, upper)`` per metric. Forwarded to
        ``min_max_normalize``. Either side can be ``None`` to fall back
        to the empirical extremum.
    metric_ids
        Optional list of metric ids, carried in the Result for labelling.
        Not consulted by the pipeline.

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

    bounds_tuple: tuple[Bound, ...] | None = (
        None if bounds is None else tuple((b[0], b[1]) for b in bounds)
    )

    normalised = min_max_normalize(scores, polarity, bounds=bounds_tuple)
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
        bounds=bounds_tuple,
        metric_ids=tuple(metric_ids) if metric_ids is not None else None,
    )


def run_from_registry(
    scores,
    metric_ids: Sequence[str],
    weights="equal",
    method: str = "saw",
    registry: Registry | None = None,
) -> Result:
    """Run the MCDA pipeline with polarity, bounds, and scale checks pulled from the registry.

    The ontology-aware entry point. For each id in ``metric_ids`` this
    function looks up the metric card via ``properties_for``, validates
    the requested aggregation against the declared scale type and allowed
    transformations, and feeds polarity plus the declared lower and upper
    bounds into ``run``.

    Use this when the columns of ``scores`` correspond to known metric
    cards. Use the lower-level ``run`` when you want to drive the pipeline
    by hand-typed polarity strings, for example in a unit test.

    Parameters
    ----------
    scores
        Array-like of shape ``(n_tools, n_metrics)``. The columns must
        match ``metric_ids`` in order.
    metric_ids
        Length ``n_metrics`` sequence of metric ids to look up in the
        registry.
    weights
        Forwarded to ``run``.
    method
        Forwarded to ``run``.
    registry
        Optional ``Registry`` instance. Defaults to a fresh registry over
        the bundled metrics/ directory.

    Returns
    -------
    Result

    Raises
    ------
    IncompatibleScaleError
        If any metric's declared scale type or allowed transformations
        forbid the requested aggregation.
    """
    metric_ids = list(metric_ids)
    properties = properties_for(metric_ids, registry=registry)
    validate_for_aggregation(properties, method)

    polarity = [p.polarity for p in properties]
    bounds = [(p.range_lower, p.range_upper) for p in properties]

    return run(
        scores,
        polarity=polarity,
        weights=weights,
        method=method,
        bounds=bounds,
        metric_ids=metric_ids,
    )
