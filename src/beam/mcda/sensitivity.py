"""Sensitivity analysis on an MCDA run."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from .cross_dataset import reduce_tensor
from .facade import Result, run


def _subset_columns(context, cols: Sequence[int]):
    """Restrict a per-metric context to the kept columns for a leave-one-out run.

    ``None`` and a single strategy name apply to every column unchanged. A
    per-column sequence is indexed down to the kept columns.
    """
    if context is None or isinstance(context, str):
        return context
    return [context[j] for j in cols]


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
    normalization=None,
    bounds=None,
    baselines=None,
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
    normalization, bounds, baselines
        Optional per-metric normalization context forwarded to ``run`` and
        subset to the kept columns on each omission. Default ``None`` keeps
        the ``run`` defaults. Pass the values from
        ``beam.mcda.registry_context`` so the leave-one-out runs normalize
        the scores the same way as the headline ranking.

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

    base = run(
        scores,
        polarity,
        weights=weights,
        method=method,
        normalization=normalization,
        bounds=bounds,
        baselines=baselines,
    )

    loo: dict[int, Result] = {}
    for i in range(n_metrics):
        cols = [j for j in range(n_metrics) if j != i]
        sub_scores = scores[:, cols]
        sub_polarity = [polarity[j] for j in cols]
        loo[i] = run(
            sub_scores,
            sub_polarity,
            weights=weights,
            method=method,
            normalization=_subset_columns(normalization, cols),
            bounds=_subset_columns(bounds, cols),
            baselines=_subset_columns(baselines, cols),
        )

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


@dataclass(frozen=True)
class DatasetSensitivityReport:
    """Outcome of a leave-one-dataset-out sensitivity analysis.

    Holds the base run (all datasets pooled), every leave-one-dataset-out run
    keyed by the omitted dataset index, the optional dataset_names label list,
    and four summary fields. ``evaluated_datasets`` lists the dataset indices
    whose omission left a matrix the pipeline could still rank; a dataset whose
    removal would leave some tool with no observation for a metric is skipped
    and excluded from the stability denominator. ``rank_stability`` is the
    per-tool fraction of evaluated runs in which the tool kept its base rank.
    ``most_influential_dataset`` is the dataset whose removal causes the largest
    rank change, and ``max_rank_shift`` is the size of that change.
    """

    base: Result
    leave_one_out: dict[int, Result]
    dataset_names: tuple[str, ...] | None
    rank_stability: np.ndarray
    most_influential_dataset: int
    max_rank_shift: int
    evaluated_datasets: tuple[int, ...]


def leave_one_dataset_out(
    tensor,
    polarity: Sequence[str],
    reduction_rules: Sequence[str],
    dataset_names: Sequence[str] | None = None,
    metric_ids: Sequence[str] | None = None,
    weights="equal",
    method: str = "saw",
    normalization=None,
    bounds=None,
    baselines=None,
) -> DatasetSensitivityReport:
    """Pool all datasets and rank, then re-rank with each dataset left out.

    The headline ranking pools a tool by dataset by metric tensor across the
    dataset axis (one reduction rule per metric) into a tool by metric matrix
    and ranks it. This analysis asks how much that ranking depends on any single
    dataset: for each dataset d, drop d, pool the remaining datasets the same
    way, re-rank, and compare to the base ranking. The result is a per-tool rank
    stability (the fraction of leave-one-out runs in which the tool keeps its
    base rank) and the largest rank shift caused by removing any single dataset.

    The reduction is nan-aware. A dataset whose removal would leave some tool
    with no observation for a metric cannot be pooled, so that omission is
    skipped and excluded from the stability denominator; the evaluated dataset
    indices are reported in the result.

    The normalization context applies per metric and the metric axis is
    unchanged when a dataset is dropped, so ``normalization``, ``bounds`` and
    ``baselines`` are forwarded to every run unchanged.

    Parameters
    ----------
    tensor
        Array-like of shape ``(n_tools, n_datasets, n_metrics)``.
    polarity
        Length ``n_metrics`` sequence of polarity strings.
    reduction_rules
        Length ``n_metrics`` sequence of cross-dataset reduction rule names,
        one per metric. Source these from each card's
        ``recommended_aggregation_across_datasets``.
    dataset_names
        Optional length ``n_datasets`` labels, carried in the report.
    metric_ids
        Optional length ``n_metrics`` labels used in reduction error messages.
    weights, method
        Forwarded to ``run``.
    normalization, bounds, baselines
        Optional per-metric normalization context forwarded to every run.
        Pass the values from ``beam.mcda.registry_context`` so the leave-one-out
        runs normalize the same way as the headline ranking.

    Returns
    -------
    DatasetSensitivityReport
    """
    tensor = np.asarray(tensor, dtype=float)
    if tensor.ndim != 3:
        raise ValueError(f"tensor must be 3D; got shape {tensor.shape}")
    n_tools, n_datasets, n_metrics = tensor.shape
    if n_datasets < 2:
        raise ValueError(f"leave_one_dataset_out needs at least 2 datasets; got {n_datasets}")
    if len(polarity) != n_metrics:
        raise ValueError(f"polarity has {len(polarity)} entries but tensor has {n_metrics} metrics")
    if len(reduction_rules) != n_metrics:
        raise ValueError(
            f"reduction_rules has {len(reduction_rules)} entries but tensor has {n_metrics} metrics"
        )

    def _run(matrix):
        return run(
            matrix,
            list(polarity),
            weights=weights,
            method=method,
            normalization=normalization,
            bounds=bounds,
            baselines=baselines,
        )

    base = _run(reduce_tensor(tensor, reduction_rules, metric_ids=metric_ids))

    loo: dict[int, Result] = {}
    for d in range(n_datasets):
        kept = [k for k in range(n_datasets) if k != d]
        sub = tensor[:, kept, :]
        if not (~np.isnan(sub)).any(axis=1).all():
            # Dropping this dataset leaves a tool unobserved on some metric.
            continue
        loo[d] = _run(reduce_tensor(sub, reduction_rules, metric_ids=metric_ids))

    evaluated = tuple(sorted(loo))
    if evaluated:
        held = np.zeros(n_tools, dtype=int)
        for r in loo.values():
            held += (r.ranks == base.ranks).astype(int)
        rank_stability = held / len(evaluated)
    else:
        rank_stability = np.full(n_tools, np.nan)

    max_shift = 0
    most_influential = evaluated[0] if evaluated else 0
    for d, r in loo.items():
        shift = int(np.abs(r.ranks - base.ranks).max())
        if shift > max_shift:
            max_shift = shift
            most_influential = d

    return DatasetSensitivityReport(
        base=base,
        leave_one_out=loo,
        dataset_names=tuple(dataset_names) if dataset_names is not None else None,
        rank_stability=rank_stability,
        most_influential_dataset=most_influential,
        max_rank_shift=max_shift,
        evaluated_datasets=evaluated,
    )
