"""Triantaphyllou-Sanchez weight perturbation sensitivity.

For SAW, the composite score is linear in the weights, so the smallest
single-weight change that swaps a given pair of tools has a closed form.
This module implements that calculation and reports the most fragile
pair, the criterion responsible for it, and the new weight after the
perturbation. The TOPSIS case is non-linear in the weights and is not
covered here.

Reference: Triantaphyllou and Sanchez, A sensitivity analysis approach
for some deterministic multi-criteria decision-making methods. Decision
Sciences (1997).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from .facade import Result, run


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
) -> WeightPerturbationReport:
    """Compute the smallest single-weight change that swaps each pair of tools under SAW.

    For SAW, the composite difference between two tools ``a`` and ``b`` is
    a linear function of the weights:

        C_a - C_b = sum_k w_k * (x_ak - x_bk)

    where ``x`` is the normalized matrix. The smallest change to weight
    ``k`` alone that brings this difference to zero is

        delta_k = (C_b - C_a) / (x_ak - x_bk)

    when the denominator is non-zero. The function reports, for every
    ordered pair where ``a`` is currently above ``b``, the criterion that
    gives the smallest ``|delta_k|`` subject to the feasibility constraint
    that ``w_k + delta_k`` remains non-negative.

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
        Must be ``"saw"``; ``"topsis"`` is rejected because the composite
        is non-linear in the weights.
    bounds
        Optional declared bounds, forwarded to ``run``.
    fragility_threshold
        Absolute weight delta below which the top-rank flip is flagged as
        fragile in ``top_rank_is_fragile``. Default 0.05, i.e. five
        percentage points of a weight in [0, 1].

    Returns
    -------
    WeightPerturbationReport
    """
    if method != "saw":
        raise NotImplementedError(
            f"smallest_weight_perturbation is closed-form only for 'saw'; got {method!r}"
        )

    base = run(scores, polarity, weights=weights, method=method, bounds=bounds)
    x = base.normalized
    w = base.weights
    n_tools, n_metrics = x.shape

    pairs: list[PairPerturbation] = []
    for a in range(n_tools):
        for b in range(n_tools):
            if a == b:
                continue
            if base.ranks[a] >= base.ranks[b]:
                continue
            diff_composite = float(base.composite[a] - base.composite[b])
            best_criterion = -1
            best_delta = math.inf
            best_abs = math.inf
            best_new_weight = math.nan
            for k in range(n_metrics):
                denom = float(x[a, k] - x[b, k])
                if denom == 0.0:
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
