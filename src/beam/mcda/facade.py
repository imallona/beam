"""High-level entry point that runs a full MCDA pipeline in one call."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from ..cards import Registry, properties_for
from .aggregate import rank, weighted_sum
from .comet import comet
from .normalize import Bound, normalization_warnings, normalize
from .promethee import promethee_ii
from .topsis import topsis
from .validate import validate_for_aggregation
from .vikor import vikor
from .weights import (
    critic_weights,
    entropy_weights,
    equal_weights,
    merec_weights,
    standard_deviation_weights,
)


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
    normalized: np.ndarray
    weights: np.ndarray
    composite: np.ndarray
    ranks: np.ndarray
    weighting: str
    method: str
    bounds: tuple[Bound, ...] | None = None
    metric_ids: tuple[str, ...] | None = None
    normalization: tuple[str, ...] | None = None
    warnings: tuple[str, ...] = ()


_KNOWN_WEIGHTINGS = ("equal", "entropy", "std", "critic", "merec")
_KNOWN_METHODS = ("saw", "topsis", "vikor", "promethee_ii", "comet")

_OBJECTIVE_WEIGHTS = {
    "std": standard_deviation_weights,
    "critic": critic_weights,
    "merec": merec_weights,
}


def _resolve_weights(
    weighting,
    normalized: np.ndarray,
) -> tuple[np.ndarray, str]:
    if isinstance(weighting, str):
        if weighting == "equal":
            return equal_weights(normalized.shape[1]), "equal"
        if weighting == "entropy":
            return entropy_weights(normalized), "entropy"
        if weighting in _OBJECTIVE_WEIGHTS:
            return _OBJECTIVE_WEIGHTS[weighting](normalized), weighting
        raise ValueError(f"unknown weighting {weighting!r}; supported: {_KNOWN_WEIGHTINGS}")
    w = np.asarray(weighting, dtype=float)
    if w.shape != (normalized.shape[1],):
        raise ValueError(f"weights array has shape {w.shape}; expected ({normalized.shape[1]},)")
    if np.any(w < 0):
        raise ValueError("weights must be non-negative")
    return w, "user-supplied"


def _resolve_method(method: str):
    methods = {
        "saw": weighted_sum,
        "topsis": topsis,
        "vikor": vikor,
        "promethee_ii": promethee_ii,
        "comet": comet,
    }
    if method in methods:
        return methods[method]
    raise ValueError(f"unknown method {method!r}; supported: {_KNOWN_METHODS}")


def _resolve_strategies(normalization, n_metrics: int) -> list[str]:
    if normalization is None:
        return ["min_max"] * n_metrics
    if isinstance(normalization, str):
        return [normalization] * n_metrics
    strategies = list(normalization)
    if len(strategies) != n_metrics:
        raise ValueError(
            f"normalization has {len(strategies)} entries but scores has {n_metrics} columns"
        )
    return strategies


def run(
    scores,
    polarity: Sequence[str],
    weights="equal",
    method: str = "saw",
    bounds: Sequence[Bound] | None = None,
    metric_ids: Sequence[str] | None = None,
    normalization=None,
    baselines: Sequence[float | None] | None = None,
) -> Result:
    """Run a full MCDA pipeline from raw scores to per-tool ranks.

    Three steps:

    1. Normalize each column of ``scores`` to [0, 1] using the per-metric
       strategy in ``normalization`` (default ``min_max`` on every column),
       respecting per-metric polarity and, when provided, declared bounds.
       After this step every column is oriented so higher is better.
    2. Build a weight vector. Pass ``"equal"``, ``"entropy"``, ``"std"``,
       ``"critic"`` or ``"merec"`` for the built-in objective schemes, or
       pass an explicit array of length ``n_metrics``. For a subjective
       scheme, call ``beam.mcda.ahp_weights`` on a pairwise comparison
       matrix and pass the returned array. ``"merec"`` takes logarithms and
       needs a normalization bounded away from zero, so it rejects a column
       carrying a hard zero (plain min-max maps the worst tool to zero).
    3. Aggregate to one composite score per tool. Pass ``"saw"`` for simple
       additive weighting (the dot product of normalized scores and
       weights), ``"topsis"`` for distance-to-ideal aggregation, ``"vikor"``
       for the compromise ranking, ``"promethee_ii"`` for the net
       outranking flow, or ``"comet"`` for the characteristic-objects model.

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
        ``"equal"`` (default), ``"entropy"``, ``"std"``, ``"critic"``,
        ``"merec"``, or an explicit array of length ``n_metrics``.
    method
        ``"saw"`` (default), ``"topsis"``, ``"vikor"``, ``"promethee_ii"``
        or ``"comet"``.
    bounds
        Optional list of ``(lower, upper)`` per metric. Forwarded to
        ``min_max_normalize``. Either side can be ``None`` to fall back
        to the empirical extremum.
    metric_ids
        Optional list of metric ids, carried in the Result for labelling
        and used to name columns in any normalization warning.
    normalization
        ``None`` (min_max on every column), a single strategy name applied
        to all columns, or a per-column sequence. Strategy names are listed
        in ``beam.mcda.normalize.STRATEGIES``.
    baselines
        Optional per-column reference score required by the
        ``baseline_relative`` strategy. Forwarded to ``normalize``.

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
    strategies = _resolve_strategies(normalization, scores.shape[1])

    normalized = normalize(scores, polarity, strategies, bounds=bounds_tuple, baselines=baselines)
    warnings = normalization_warnings(
        scores, strategies, bounds=bounds_tuple, metric_ids=metric_ids
    )
    weight_array, weighting_name = _resolve_weights(weights, normalized)
    aggregate_fn = _resolve_method(method)
    composite = aggregate_fn(normalized, weight_array)
    ranks_arr = rank(composite)

    return Result(
        scores=scores,
        polarity=polarity,
        normalized=normalized,
        weights=weight_array,
        composite=composite,
        ranks=ranks_arr,
        weighting=weighting_name,
        method=method,
        bounds=bounds_tuple,
        metric_ids=tuple(metric_ids) if metric_ids is not None else None,
        normalization=tuple(strategies),
        warnings=tuple(warnings),
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
    function looks up the metric card via ``properties_for``, picks the
    normalization strategy from ``comparability.recommended_normalization``
    (default ``min_max``), validates the requested aggregation and that
    strategy against the declared scale type and allowed transformations,
    and feeds polarity, declared bounds, and any chance baseline into
    ``run``.

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
    strategies = [p.recommended_normalization or "min_max" for p in properties]
    validate_for_aggregation(properties, method, strategies)

    polarity = [p.polarity for p in properties]
    bounds = [(p.range_lower, p.range_upper) for p in properties]
    baselines = [p.score_of_random_baseline for p in properties]

    return run(
        scores,
        polarity=polarity,
        weights=weights,
        method=method,
        bounds=bounds,
        metric_ids=metric_ids,
        normalization=strategies,
        baselines=baselines,
    )
