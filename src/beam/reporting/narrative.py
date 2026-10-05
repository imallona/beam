"""Recommendation paragraph for the HTML report.

The top tool under the chosen weighting, aggregation and metric set, followed
by the sensitivity results present in the run. The claim is always tied to the
metric set and weighting, since the top rank can change with either.
"""

from __future__ import annotations

import numpy as np

from ..api import RunResult

_METHOD_NAMES = {
    "saw": "weighted sum",
    "topsis": "TOPSIS",
    "vikor": "VIKOR",
    "promethee_ii": "PROMETHEE II",
    "comet": "COMET",
}

_WEIGHTING_NAMES = {
    "equal": "equal weights",
    "entropy": "Shannon entropy weights",
    "std": "standard deviation weights",
    "critic": "CRITIC weights",
    "merec": "MEREC weights",
    "user-supplied": "the supplied weights",
}


def _method_phrase(method: str) -> str:
    return _METHOD_NAMES.get(method, method)


def _weighting_phrase(weighting: str) -> str:
    return _WEIGHTING_NAMES.get(weighting, weighting)


def _metric_phrase(metric_ids: tuple[str, ...]) -> str:
    ids = list(metric_ids)
    if len(ids) == 1:
        return ids[0]
    if len(ids) == 2:
        return f"{ids[0]} and {ids[1]}"
    return ", ".join(ids[:-1]) + f" and {ids[-1]}"


def recommendation(result: RunResult) -> str:
    """Return a short recommendation paragraph for a ``RunResult``.

    The top tool, then the sensitivity results present in the run: SMAA
    confidence, leave-one-metric-out and leave-one-dataset-out stability, the
    smallest weight perturbation, the chance baseline, the noise floor and the
    card consistency audit.
    """
    ranks = result.result.ranks
    top_idx = int(np.argmin(ranks))
    top = result.tool_names[top_idx]
    n_tools = len(result.tool_names)
    method = _method_phrase(result.result.method)
    weighting = _weighting_phrase(result.result.weighting)
    metrics = _metric_phrase(result.metric_ids)

    sentences = [
        f"Under {method} aggregation with {weighting} over the metrics {metrics}, "
        f"{top} ranks first of {n_tools} tools."
    ]

    if result.smaa is not None:
        confidence = float(result.smaa.confidence_factor[top_idx])
        pct = round(confidence * 100)
        n = result.smaa.n_samples
        sentences.append(
            f"Across {n} weightings drawn at random from the metric simplex, "
            f"{top} ranked first in {pct} percent of draws."
        )

    if result.leave_one_out is not None:
        stability = float(result.leave_one_out.rank_stability[top_idx])
        n_metrics = len(result.metric_ids)
        held = round(stability * n_metrics)
        if n_metrics > 1:
            sentences.append(f"Its rank held in {held} of {n_metrics} leave-one-metric-out runs.")

    if result.leave_one_dataset_out is not None:
        lodo = result.leave_one_dataset_out
        n_eval = len(lodo.evaluated_datasets)
        if n_eval > 0:
            held = round(float(lodo.rank_stability[top_idx]) * n_eval)
            sentences.append(f"Its rank held in {held} of {n_eval} leave-one-dataset-out runs.")

    if result.perturbation is not None:
        pert = result.perturbation.top_rank_perturbation
        if result.perturbation.top_rank_is_fragile and pert is not None:
            metric = _perturbation_metric(result, pert.criterion)
            sentences.append(
                f"The top rank is fragile: a weight change of about {abs(pert.delta):.2f} "
                f"on {metric} is enough to overturn it."
            )
        elif pert is None:
            sentences.append(
                "No single-metric weight change within the searched range overturns the top rank."
            )
        else:
            sentences.append(
                "The top rank is stable: the smallest single-metric weight change overturning "
                f"it is about {abs(pert.delta):.2f}."
            )

    if result.random_baseline is not None and result.random_baseline.active:
        n_never = len(result.random_baseline.tools_never_beating)
        if n_never:
            sentences.append(
                f"{n_never} of {n_tools} tools do not score above chance on any metric that "
                "declares a baseline."
            )

    if result.noise_floor is not None and result.noise_floor.top_pair_indistinguishable:
        sentences.append(
            "The top two tools differ by less than the noise floor on every metric that "
            "declares one, so the order between them is within measurement noise."
        )

    if result.card_consistency is not None and result.card_consistency.violations:
        n_viol = len(result.card_consistency.violations)
        sentences.append(
            f"The raw scores contradict the metric cards in {n_viol} place(s); the ranking "
            "is based on at least one metric whose data falls outside its declared card values."
        )

    return " ".join(sentences)


def _perturbation_metric(result: RunResult, criterion: int) -> str:
    if 0 <= criterion < len(result.metric_ids):
        return result.metric_ids[criterion]
    return "one metric"
