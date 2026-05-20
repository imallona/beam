"""Sensitivity analysis on an MCDA run."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from .facade import Result, run


@dataclass(frozen=True)
class SensitivityReport:
    """Outcome of a leave-one-metric-out sensitivity analysis.

    Holds the base run (all metrics), every leave-one-out run keyed by the
    omitted metric index, the optional metric_ids label list, and three
    summary fields: per-tool rank stability, the index of the metric whose
    removal causes the largest rank change, and the value of that change.
    """

    base: Result
    leave_one_out: dict[int, Result]
    metric_ids: tuple[str, ...] | None
    rank_stability: np.ndarray
    most_influential_metric: int
    max_rank_shift: int


def leave_one_metric_out(
    scores,
    polarity: Sequence[str],
    metric_ids: Sequence[str] | None = None,
    weights="equal",
    method: str = "saw",
) -> SensitivityReport:
    """Run the pipeline once with all metrics, then once per metric omission.

    For each metric column j, drop column j and re-run ``beam.mcda.run`` on
    the remaining ``n_metrics - 1`` columns with the same weighting and
    method. Compare every leave-one-out ranking to the base ranking to
    obtain per-tool rank stability (the fraction of leave-one-out runs in
    which the tool keeps its base rank) and the maximum rank shift caused
    by any single omission.

    Parameters
    ----------
    scores
        Array-like of shape ``(n_tools, n_metrics)``.
    polarity
        Length ``n_metrics`` sequence of ``"higher_is_better"`` or
        ``"lower_is_better"``. Use ``beam.cards.polarities_for`` to source
        this from the registry.
    metric_ids
        Optional length ``n_metrics`` sequence of metric ids. Carried in
        the report for labelling; not consulted by the pipeline.
    weights
        Forwarded to ``run``. ``"equal"``, ``"entropy"``, or an array.
    method
        Forwarded to ``run``. ``"saw"`` or ``"topsis"``.

    Returns
    -------
    SensitivityReport
    """
    scores = np.asarray(scores, dtype=float)
    polarity = list(polarity)

    if scores.ndim != 2:
        raise ValueError(f"scores must be 2D; got shape {scores.shape}")
    n_tools, n_metrics = scores.shape
    if n_metrics < 2:
        raise ValueError(f"leave_one_metric_out needs at least 2 metrics; got {n_metrics}")
    if len(polarity) != n_metrics:
        raise ValueError(f"polarity has {len(polarity)} entries but scores has {n_metrics} columns")
    if metric_ids is not None and len(metric_ids) != n_metrics:
        raise ValueError(
            f"metric_ids has {len(metric_ids)} entries but scores has {n_metrics} columns"
        )

    base = run(scores, polarity, weights=weights, method=method)

    loo: dict[int, Result] = {}
    for i in range(n_metrics):
        cols = [j for j in range(n_metrics) if j != i]
        sub_scores = scores[:, cols]
        sub_polarity = [polarity[j] for j in cols]
        loo[i] = run(sub_scores, sub_polarity, weights=weights, method=method)

    held = np.zeros(n_tools, dtype=int)
    for r in loo.values():
        held += (r.ranks == base.ranks).astype(int)
    rank_stability = held / n_metrics

    max_shift = 0
    most_influential = 0
    for i, r in loo.items():
        shift = int(np.abs(r.ranks - base.ranks).max())
        if shift > max_shift:
            max_shift = shift
            most_influential = i

    return SensitivityReport(
        base=base,
        leave_one_out=loo,
        metric_ids=tuple(metric_ids) if metric_ids is not None else None,
        rank_stability=rank_stability,
        most_influential_metric=most_influential,
        max_rank_shift=max_shift,
    )
