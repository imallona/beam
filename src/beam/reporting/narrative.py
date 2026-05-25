"""Generate the plain-English recommendation paragraph for a report.

The text follows the project writing rules: plain English, short sentences,
no em dash, no bold, no marketing vocabulary, and no winner or wins phrasing
for methods. It also avoids bare best and worst value judgements, preferring
rank-based language such as ranks first. Every claim is tied to the specific
metric set and weighting, in line with the project's own thesis that no single
method ranks first in the abstract.
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

    Describes which tool ranks first under the chosen weighting and
    aggregation on the given metric set, then qualifies that with the
    sensitivity outputs when they are present: the SMAA confidence factor, the
    leave-one-metric-out stability, and whether the top rank is fragile under a
    single-metric weight change.
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
            sentences.append(
                f"Its rank held in {held} of {n_metrics} leave-one-metric-out runs."
            )

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
                "The top rank is stable: the smallest single-metric weight change that would "
                f"overturn it is about {abs(pert.delta):.2f}."
            )

    return " ".join(sentences)


def _perturbation_metric(result: RunResult, criterion: int) -> str:
    if 0 <= criterion < len(result.metric_ids):
        return result.metric_ids[criterion]
    return "one metric"
