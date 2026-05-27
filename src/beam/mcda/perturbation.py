"""Triantaphyllou-Sanchez weight perturbation sensitivity.

The analysis asks, for every ordered pair of tools, the smallest single-weight
change that flips the pair ordering. The Triantaphyllou-Sanchez convention
perturbs one weight, leaves the others unchanged, and requires the new weight
to stay non-negative.

For SAW the composite score is linear in the weights, so the smallest
single-weight change that swaps a given pair has a closed form. This module
keeps that exact path for SAW.

For the non-linear methods (TOPSIS, VIKOR, PROMETHEE II, COMET) the composite
is not linear in the weights, so there is no closed form. For these methods the
module uses a numeric path: for each ordered pair and each criterion it brackets
the smallest single-weight change that drives the signed rank gap of the pair to
zero, then bisects to a tolerance. The search range is capped, and the criterion
is reported as -1 when no single-weight change within range flips the pair.

Both paths report the most fragile pair, the criterion responsible for it, and
the new weight after the perturbation.

Reference: Triantaphyllou and Sanchez, A sensitivity analysis approach
for some deterministic multi-criteria decision-making methods. Decision
Sciences (1997).
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np

from .facade import _KNOWN_METHODS, Result, _resolve_method, run


@dataclass(frozen=True)
class PairPerturbation:
    """Smallest single-weight perturbation that swaps one pair of tools.

    Fields:
        higher: index of the tool currently ranked above the other
        lower: index of the tool currently ranked below
        criterion: index of the criterion that gives the smallest |delta|
            among feasible criteria, or -1 if no single-criterion change
            can flip the pair
        delta: signed change to apply to weights[criterion]
        absolute_delta: ``abs(delta)``, ``inf`` when ``criterion == -1``
        new_weight: ``weights[criterion] + delta``, ``nan`` when
            ``criterion == -1``
    """

    higher: int
    lower: int
    criterion: int
    delta: float
    absolute_delta: float
    new_weight: float


@dataclass(frozen=True)
class WeightPerturbationReport:
    """Outcome of a Triantaphyllou-Sanchez weight perturbation analysis.

    Holds the base run, the per-pair smallest perturbations, and three
    summary fields: the most fragile pair (smallest absolute delta over
    all pairs), the smallest perturbation that swaps the top-ranked tool
    with any other tool, and a boolean flag indicating whether the top
    rank is fragile under any single-weight change.
    """

    base: Result
    per_pair: tuple[PairPerturbation, ...]
    most_fragile_pair: PairPerturbation | None
    top_rank_perturbation: PairPerturbation | None
    top_rank_is_fragile: bool


def smallest_weight_perturbation(
    scores,
    polarity: Sequence[str],
    weights="equal",
    method: str = "saw",
    bounds=None,
    fragility_threshold: float = 0.05,
    search_range: float = 1.0,
    tolerance: float = 1e-9,
    normalization=None,
    baselines=None,
    targets=None,
    missing: str = "error",
) -> WeightPerturbationReport:
    """Compute the smallest single-weight change that swaps each pair of tools.

    For every ordered pair where tool ``a`` is currently above tool ``b``, the
    function looks for the criterion whose weight, when changed alone (and kept
    non-negative), flips the pair ordering with the smallest absolute change. It
    reports that criterion, the signed change, and the resulting weight.

    SAW path (exact). For SAW the composite difference between two tools is a
    linear function of the weights:

        C_a - C_b = sum_k w_k * (x_ak - x_bk)

    where ``x`` is the normalized matrix. The smallest change to weight ``k``
    alone that brings this difference to zero is

        delta_k = (C_b - C_a) / (x_ak - x_bk)

    when the denominator is non-zero. This closed form is exact and fast.

    Numeric path (to a tolerance). For TOPSIS, VIKOR, PROMETHEE II and COMET the
    composite is not linear in the weights, so no closed form exists. For each
    criterion the function defines the signed rank gap

        g(delta) = C_a(w + delta * e_k) - C_b(w + delta * e_k)

    where ``e_k`` is the unit vector on criterion ``k`` and the composite comes
    from the actual aggregation. The pair is currently ordered so ``g(0) > 0``.
    The search scans ``delta`` over a capped range on both sides, in the
    feasible direction that keeps ``w_k + delta >= 0``, to find a sign change of
    ``g``. When a sign change is bracketed, bisection refines the crossing to
    ``tolerance`` on ``delta``. The criterion with the smallest feasible
    ``|delta|`` is reported. When no single-weight change within ``search_range``
    flips the pair on any criterion the criterion is reported as -1.

    Parameters
    ----------
    scores
        Array-like of shape ``(n_tools, n_metrics)``.
    polarity
        Length ``n_metrics`` sequence of polarity strings.
    weights
        Forwarded to ``run``. ``"equal"``, ``"entropy"``, or an explicit
        array.
    method
        Any of the five methods supported by ``run``: ``"saw"`` (closed-form
        path), or ``"topsis"``, ``"vikor"``, ``"promethee_ii"``, ``"comet"``
        (numeric path).
    bounds
        Optional declared bounds, forwarded to ``run``.
    normalization, baselines, targets
        Optional per-metric normalization context forwarded to ``run``.
        Default ``None`` keeps the ``run`` defaults. Pass the values from
        ``beam.mcda.registry_context`` so the perturbation search rests on
        the same normalized matrix as the headline ranking.
    fragility_threshold
        Absolute weight delta below which the top-rank flip is flagged as
        fragile in ``top_rank_is_fragile``. Default 0.05, i.e. five
        percentage points of a weight in [0, 1].
    search_range
        Numeric path only. Largest absolute single-weight change considered.
        Defaults to 1.0, the full span of a weight in [0, 1]. Ignored by the
        SAW path, which has no range cap.
    tolerance
        Numeric path only. Bisection tolerance on the weight change ``delta``.
        Defaults to 1e-9. Ignored by the SAW path.

    Returns
    -------
    WeightPerturbationReport
    """
    if method not in _KNOWN_METHODS:
        raise ValueError(f"unknown method {method!r}; supported: {_KNOWN_METHODS}")

    base = run(
        scores,
        polarity,
        weights=weights,
        method=method,
        bounds=bounds,
        normalization=normalization,
        baselines=baselines,
        targets=targets,
        missing=missing,
    )
    x = base.normalized
    w = base.weights
    n_tools, n_metrics = x.shape

    if method == "saw":
        pairs = _closed_form_pairs(base, x, w, n_tools, n_metrics)
    else:
        aggregate_fn = _resolve_method(method)
        pairs = _numeric_pairs(
            base, x, w, n_tools, n_metrics, aggregate_fn, search_range, tolerance
        )

    feasible_pairs = [p for p in pairs if p.criterion != -1]
    most_fragile = min(feasible_pairs, key=lambda p: p.absolute_delta) if feasible_pairs else None

    top_idx = int(np.argmin(base.ranks))
    top_perturbations = [p for p in feasible_pairs if p.higher == top_idx]
    top_rank_perturbation = (
        min(top_perturbations, key=lambda p: p.absolute_delta) if top_perturbations else None
    )
    top_rank_is_fragile = (
        top_rank_perturbation is not None
        and top_rank_perturbation.absolute_delta < fragility_threshold
    )

    return WeightPerturbationReport(
        base=base,
        per_pair=tuple(pairs),
        most_fragile_pair=most_fragile,
        top_rank_perturbation=top_rank_perturbation,
        top_rank_is_fragile=top_rank_is_fragile,
    )


def _ranked_above_pairs(base: Result, n_tools: int) -> list[tuple[int, int]]:
    """List ordered pairs ``(a, b)`` where tool ``a`` currently ranks above ``b``."""
    pairs: list[tuple[int, int]] = []
    for a in range(n_tools):
        for b in range(n_tools):
            if a == b:
                continue
            if base.ranks[a] < base.ranks[b]:
                pairs.append((a, b))
    return pairs


def _closed_form_pairs(
    base: Result,
    x: np.ndarray,
    w: np.ndarray,
    n_tools: int,
    n_metrics: int,
) -> list[PairPerturbation]:
    """Exact SAW path: solve the linear gap for each criterion in closed form."""
    pairs: list[PairPerturbation] = []
    for a, b in _ranked_above_pairs(base, n_tools):
        diff_composite = float(base.composite[a] - base.composite[b])
        best_criterion = -1
        best_delta = math.inf
        best_abs = math.inf
        best_new_weight = math.nan
        for k in range(n_metrics):
            denom = float(x[a, k] - x[b, k])
            if denom == 0.0 or not math.isfinite(denom):
                # A non-finite gap means one of the pair lacks this metric under
                # available-case SAW; that criterion cannot flip the pair.
                continue
            delta_k = -diff_composite / denom
            new_w = float(w[k]) + delta_k
            if new_w < 0.0:
                continue
            abs_delta = abs(delta_k)
            if abs_delta < best_abs:
                best_abs = abs_delta
                best_delta = delta_k
                best_criterion = k
                best_new_weight = new_w
        pairs.append(
            PairPerturbation(
                higher=a,
                lower=b,
                criterion=best_criterion,
                delta=best_delta if best_criterion != -1 else math.nan,
                absolute_delta=best_abs,
                new_weight=best_new_weight,
            )
        )
    return pairs


def _signed_gap(
    x: np.ndarray,
    w: np.ndarray,
    aggregate_fn: Callable[[np.ndarray, np.ndarray], np.ndarray],
    a: int,
    b: int,
    criterion: int,
    delta: float,
) -> float:
    """Signed rank gap of the pair after changing one weight by ``delta``.

    Returns the composite of tool ``a`` minus the composite of tool ``b`` under
    the aggregation, with ``weights[criterion]`` shifted by ``delta`` and the
    other weights unchanged. Positive means ``a`` still scores above ``b``.
    """
    perturbed = w.copy()
    perturbed[criterion] += delta
    composite = aggregate_fn(x, perturbed)
    return float(composite[a] - composite[b])


def _bisect_crossing(
    gap_at: Callable[[float], float],
    low: float,
    high: float,
    gap_low: float,
    gap_high: float,
    tolerance: float,
) -> float:
    """Bisect a bracket for the zero crossing of a signed gap.

    The two bracket points ``low`` and ``high`` carry gaps of opposite sign.
    The endpoints may arrive in either numeric order (the search runs outward
    in both directions from zero), so this orders them first, then narrows the
    bracket until its width is below ``tolerance`` and returns the endpoint that
    sits just past the crossing, the smaller absolute change that flips the pair.
    """
    if low > high:
        low, high = high, low
        gap_low, gap_high = gap_high, gap_low

    while high - low > tolerance:
        mid = 0.5 * (low + high)
        gap_mid = gap_at(mid)
        if gap_mid == 0.0:
            return mid
        if (gap_mid > 0.0) == (gap_low > 0.0):
            low, gap_low = mid, gap_mid
        else:
            high, gap_high = mid, gap_mid

    return 0.5 * (low + high)


def _smallest_flip_delta(
    x: np.ndarray,
    w: np.ndarray,
    aggregate_fn: Callable[[np.ndarray, np.ndarray], np.ndarray],
    a: int,
    b: int,
    criterion: int,
    search_range: float,
    tolerance: float,
) -> float | None:
    """Smallest single-weight change on ``criterion`` that flips pair ``(a, b)``.

    Scans ``delta`` outward from zero in both feasible directions on a grid,
    brackets the first sign change of the signed gap, then bisects to
    ``tolerance``. The negative direction is capped so the new weight stays
    non-negative. Returns the signed ``delta`` of the smallest flip found, or
    ``None`` when no flip occurs within ``search_range``.
    """

    def gap_at(delta: float) -> float:
        return _signed_gap(x, w, aggregate_fn, a, b, criterion, delta)

    gap_zero = gap_at(0.0)
    if gap_zero <= 0.0:
        return None

    feasible_low = max(-float(w[criterion]), -search_range)
    n_steps = 256
    candidates: list[float] = []

    for limit in (search_range, feasible_low):
        if limit == 0.0:
            continue
        step = limit / n_steps
        prev_delta = 0.0
        prev_gap = gap_zero
        for i in range(1, n_steps + 1):
            delta = step * i
            gap = gap_at(delta)
            if (gap > 0.0) != (prev_gap > 0.0) or gap == 0.0:
                crossing = _bisect_crossing(gap_at, prev_delta, delta, prev_gap, gap, tolerance)
                candidates.append(crossing)
                break
            prev_delta, prev_gap = delta, gap

    if not candidates:
        return None
    return min(candidates, key=abs)


def _numeric_pairs(
    base: Result,
    x: np.ndarray,
    w: np.ndarray,
    n_tools: int,
    n_metrics: int,
    aggregate_fn: Callable[[np.ndarray, np.ndarray], np.ndarray],
    search_range: float,
    tolerance: float,
) -> list[PairPerturbation]:
    """Numeric path: bracket-and-bisect the smallest flip per criterion per pair."""
    pairs: list[PairPerturbation] = []
    for a, b in _ranked_above_pairs(base, n_tools):
        best_criterion = -1
        best_delta = math.inf
        best_abs = math.inf
        best_new_weight = math.nan
        for k in range(n_metrics):
            delta_k = _smallest_flip_delta(x, w, aggregate_fn, a, b, k, search_range, tolerance)
            if delta_k is None:
                continue
            abs_delta = abs(delta_k)
            if abs_delta < best_abs:
                best_abs = abs_delta
                best_delta = delta_k
                best_criterion = k
                best_new_weight = float(w[k]) + delta_k
        pairs.append(
            PairPerturbation(
                higher=a,
                lower=b,
                criterion=best_criterion,
                delta=best_delta if best_criterion != -1 else math.nan,
                absolute_delta=best_abs,
                new_weight=best_new_weight,
            )
        )
    return pairs
