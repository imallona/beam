"""The five-line procedural API: load scores, rank, report.

``rank`` is the one call most users need. It resolves polarity, normalization,
bounds and baselines from the metric registry, runs the MCDA pipeline, runs the
default sensitivity primitives so the recommendation comes with a robustness
account, builds the run manifest, and returns a ``RunResult`` that bundles all
of it. ``beam.report`` (in ``beam.report``) turns a ``RunResult`` into a
self-contained HTML file.

The headline ranking and its sensitivity analysis share one normalization
context, resolved once from the cards, so the SMAA, leave-one-metric-out and
weight-perturbation outputs rest on the same normalized matrix as the ranking.

A single-dataset wide input flows straight through. A long tool by dataset by
metric tensor is first reduced across datasets per each card's recommended
cross-dataset rule, then ranked. The reduction is nan-aware (a tool missing on
some datasets is summarized over the datasets where it was observed), but a
tool that is never observed for a metric leaves a gap that the reduction cannot
fill, so ``rank`` refuses such an input and points to per-dataset analysis.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .cards import Registry
from .io import Scores, load_scores
from .manifest import build_manifest
from .mcda import (
    RegistryContext,
    Result,
    SensitivityReport,
    SMAAReport,
    WeightPerturbationReport,
    leave_one_metric_out,
    registry_context,
    run_from_registry,
    smaa,
    smallest_weight_perturbation,
)
from .mcda.cross_dataset import aggregate_across_datasets

_DEFAULT_SMAA_SAMPLES = 1000
_DEFAULT_SEED = 42


@dataclass(frozen=True)
class RunResult:
    """Everything one beam run produced, ready to report or inspect.

    Attributes
    ----------
    scores
        The input container, including the tensor and dataset names when the
        input was a long layout.
    matrix
        The tool by metric matrix actually ranked, after any cross-dataset
        reduction. Equal to ``scores.values`` for a wide input.
    result
        The headline MCDA ``Result``.
    context
        The card-derived normalization context shared by the ranking and the
        sensitivity analysis.
    smaa, leave_one_out, perturbation
        The default sensitivity outputs, or ``None`` when sensitivity was off.
    manifest
        The run manifest dictionary (see ``beam.manifest``).
    """

    scores: Scores
    matrix: np.ndarray
    result: Result
    context: RegistryContext
    manifest: dict
    smaa: SMAAReport | None = None
    leave_one_out: SensitivityReport | None = None
    perturbation: WeightPerturbationReport | None = None

    @property
    def tool_names(self) -> tuple[str, ...]:
        return self.scores.tool_names

    @property
    def metric_ids(self) -> tuple[str, ...]:
        return self.scores.metric_ids

    @property
    def top_tool(self) -> str:
        """Name of the tool ranked first by the headline aggregation."""
        return self.tool_names[int(np.argmin(self.result.ranks))]


def rank(
    scores: Scores | str | Path | np.ndarray,
    weights="equal",
    method: str = "saw",
    sensitivity: bool = True,
    *,
    metric_ids: Sequence[str] | None = None,
    tool_names: Sequence[str] | None = None,
    smaa_samples: int = _DEFAULT_SMAA_SAMPLES,
    seed: int = _DEFAULT_SEED,
    registry: Registry | None = None,
) -> RunResult:
    """Rank tools from a benchmark score table, with sensitivity and a manifest.

    Parameters
    ----------
    scores
        A ``Scores`` from ``beam.load_scores``, a path to a CSV (loaded with
        layout auto-detection), or a 2D array of shape ``(n_tools, n_metrics)``
        together with ``metric_ids``.
    weights
        ``"equal"`` (default), ``"entropy"``, ``"std"``, ``"critic"``,
        ``"merec"``, or an explicit array of length ``n_metrics``.
    method
        ``"saw"`` (default), ``"topsis"``, ``"vikor"``, ``"promethee_ii"`` or
        ``"comet"``.
    sensitivity
        When true (default), also run leave-one-metric-out, SMAA, and the
        smallest-weight-perturbation analysis, all on the same normalization
        context as the ranking.
    metric_ids
        Required only when ``scores`` is a bare array.
    tool_names
        Optional names when ``scores`` is a bare array; defaults to
        ``tool_1 .. tool_n``.
    smaa_samples
        SMAA sample count. Defaults to 1000.
    seed
        SMAA seed. Defaults to 42 so two default runs reproduce.
    registry
        Optional ``Registry``. Defaults to a fresh registry over the bundled
        metrics.

    Returns
    -------
    RunResult

    Raises
    ------
    ValueError
        If a bare array is passed without ``metric_ids``, or a long input
        leaves a tool with no observations for some metric.
    IncompatibleScaleError
        If a metric's declared scale type forbids the requested aggregation.
    """
    reg = registry if registry is not None else Registry()
    score_obj = _coerce_scores(scores, metric_ids, tool_names, reg)
    matrix = _matrix_for_ranking(score_obj, reg)
    ids = score_obj.metric_ids

    context = registry_context(ids, method, registry=reg)
    result = run_from_registry(matrix, ids, weights=weights, method=method, registry=reg)

    smaa_report: SMAAReport | None = None
    loo_report: SensitivityReport | None = None
    pert_report: WeightPerturbationReport | None = None
    if sensitivity:
        smaa_report = smaa(
            matrix,
            context.polarity,
            n_samples=smaa_samples,
            method=method,
            seed=seed,
            normalization=list(context.normalization),
            bounds=list(context.bounds),
            baselines=list(context.baselines),
        )
        loo_report = leave_one_metric_out(
            matrix,
            context.polarity,
            metric_ids=ids,
            weights=weights,
            method=method,
            normalization=list(context.normalization),
            bounds=list(context.bounds),
            baselines=list(context.baselines),
        )
        pert_report = smallest_weight_perturbation(
            matrix,
            context.polarity,
            weights=weights,
            method=method,
            bounds=list(context.bounds),
            normalization=list(context.normalization),
            baselines=list(context.baselines),
        )

    manifest = build_manifest(
        scores=score_obj,
        metric_ids=ids,
        weighting=result.weighting,
        method=method,
        normalization=context.normalization,
        sensitivity=sensitivity,
        smaa_samples=smaa_samples if sensitivity else None,
        smaa_seed=seed if sensitivity else None,
        registry=reg,
    )

    return RunResult(
        scores=score_obj,
        matrix=matrix,
        result=result,
        context=context,
        manifest=manifest,
        smaa=smaa_report,
        leave_one_out=loo_report,
        perturbation=pert_report,
    )


def _coerce_scores(
    scores: Scores | str | Path | np.ndarray,
    metric_ids: Sequence[str] | None,
    tool_names: Sequence[str] | None,
    registry: Registry,
) -> Scores:
    if isinstance(scores, Scores):
        return scores
    if isinstance(scores, (str, Path)):
        return load_scores(scores, registry=registry)
    matrix = np.asarray(scores, dtype=float)
    if matrix.ndim != 2:
        raise ValueError(f"array input must be 2D; got shape {matrix.shape}")
    if metric_ids is None:
        raise ValueError("metric_ids is required when scores is a bare array")
    names = (
        tuple(tool_names)
        if tool_names is not None
        else tuple(f"tool_{i + 1}" for i in range(matrix.shape[0]))
    )
    return Scores(
        values=matrix,
        tool_names=names,
        metric_ids=tuple(metric_ids),
        dataset_names=None,
        layout="wide",
    )


def _matrix_for_ranking(scores: Scores, registry: Registry) -> np.ndarray:
    if not scores.is_tensor:
        return scores.values
    return _reduce_across_datasets(scores, registry)


def _reduce_across_datasets(scores: Scores, registry: Registry) -> np.ndarray:
    """Fold a tool by dataset by metric tensor to a tool by metric matrix.

    Each metric column is reduced over the dataset axis with the rule on its
    card (``comparability.recommended_aggregation_across_datasets``), nan-aware
    so a tool missing on some datasets is summarized over the datasets where it
    was observed. A tool with no observations at all for a metric cannot be
    summarized; that raises, since the single-matrix pipeline has no value to
    rank there. Per-dataset and coverage-aware handling is the heterogeneity
    module (Phase 4).
    """
    n_tools, _, n_metrics = scores.values.shape
    out = np.empty((n_tools, n_metrics), dtype=float)
    for j, metric_id in enumerate(scores.metric_ids):
        rule = registry.get(metric_id).recommended_aggregation_across_datasets or "arithmetic_mean"
        out[:, j] = _reduce_metric(scores.values[:, :, j], rule, metric_id)
    return out


def _reduce_metric(per_dataset: np.ndarray, rule: str, metric_id: str) -> np.ndarray:
    observed = ~np.isnan(per_dataset)
    if not observed.any(axis=1).all():
        missing = np.where(~observed.any(axis=1))[0].tolist()
        raise ValueError(
            f"metric {metric_id!r} has tool rows with no observed dataset (indices {missing}); "
            "reduce or analyze per dataset, or use the heterogeneity module"
        )
    if rule == "arithmetic_mean":
        return np.nanmean(per_dataset, axis=1)
    if rule == "median":
        return np.nanmedian(per_dataset, axis=1)
    if rule == "geometric_mean":
        if np.nanmin(per_dataset) <= 0:
            raise ValueError(
                f"geometric_mean reduction for metric {metric_id!r} needs positive scores"
            )
        return np.exp(np.nanmean(np.log(per_dataset), axis=1))
    if rule == "rank_mean":
        raise NotImplementedError(
            f"rank_mean cross-dataset reduction for metric {metric_id!r} with missing cells is "
            "Phase 4 (coverage-aware) work; reduce per dataset first"
        )
    # Fall back to the validated rule set in beam.mcda for a clean error.
    return aggregate_across_datasets(per_dataset, rule)
