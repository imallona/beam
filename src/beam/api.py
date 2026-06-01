"""The five-line procedural API: load scores, rank, report.

``rank`` is the one call most users need. It resolves polarity, normalization,
bounds, baselines and targets from the metric registry, runs the MCDA pipeline, runs the
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
    DatasetSensitivityReport,
    NoiseFloorReport,
    RandomBaselineReport,
    RegistryContext,
    Result,
    SensitivityReport,
    SMAAReport,
    WeightPerturbationReport,
    beats_random_baseline,
    leave_one_dataset_out,
    leave_one_metric_out,
    noise_floor_separation,
    reduce_tensor,
    registry_context,
    run_from_registry,
    smaa,
    smallest_weight_perturbation,
)

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
    leave_one_dataset_out
        The leave-one-dataset-out sensitivity report, present only when the
        input was a tensor with at least two datasets and sensitivity was on.
    random_baseline
        Per-metric chance comparison from the cards' declared baselines, and the
        tools that beat chance on no metric. Always computed.
    noise_floor
        Pairwise separation against the cards' declared noise floors, flagging
        the tool pairs the metric set cannot tell apart. Always computed.
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
    leave_one_dataset_out: DatasetSensitivityReport | None = None
    random_baseline: RandomBaselineReport | None = None
    noise_floor: NoiseFloorReport | None = None

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
    missing: str = "error",
    metric_ids: Sequence[str] | None = None,
    tool_names: Sequence[str] | None = None,
    smaa_samples: int = _DEFAULT_SMAA_SAMPLES,
    seed: int = _DEFAULT_SEED,
    registry: Registry | None = None,
    versions: Sequence[str | None] | None = None,
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
    missing
        Missing-data policy for the tool by metric matrix. ``"error"``
        (default) refuses any missing cell; ``"available"`` is available-case
        SAW; ``"worst"`` treats a non-run as the worst score; ``"impute"`` is
        mean imputation (discouraged). See ``beam.mcda.run``. A tool by dataset
        by metric tensor is first summarized over the datasets where each tool
        ran (available-case, never imputed); a tool with no run at all for a
        metric leaves a missing cell that this policy then resolves.
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
    versions
        Optional per-metric card version pin, aligned with the score table's
        metric columns. ``None`` in a slot (or ``versions=None``) takes the
        latest version. A pinned version the registry does not carry raises
        KeyError. The resolved versions are recorded in the manifest.

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
    on_zero_coverage = "error" if missing == "error" else "nan"
    matrix = _matrix_for_ranking(score_obj, reg, on_zero_coverage)
    ids = score_obj.metric_ids

    context = registry_context(ids, method, registry=reg, versions=versions)
    result = run_from_registry(
        matrix,
        ids,
        weights=weights,
        method=method,
        registry=reg,
        missing=missing,
        versions=versions,
    )

    smaa_report: SMAAReport | None = None
    loo_report: SensitivityReport | None = None
    pert_report: WeightPerturbationReport | None = None
    lodo_report: DatasetSensitivityReport | None = None
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
            targets=list(context.targets),
            missing=missing,
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
            targets=list(context.targets),
            missing=missing,
        )
        pert_report = smallest_weight_perturbation(
            matrix,
            context.polarity,
            weights=weights,
            method=method,
            bounds=list(context.bounds),
            normalization=list(context.normalization),
            baselines=list(context.baselines),
            targets=list(context.targets),
            missing=missing,
        )
        if score_obj.is_tensor and score_obj.values.shape[1] >= 2:
            lodo_report = leave_one_dataset_out(
                score_obj.values,
                context.polarity,
                _reduction_rules(ids, reg),
                dataset_names=score_obj.dataset_names,
                metric_ids=ids,
                weights=weights,
                method=method,
                normalization=list(context.normalization),
                bounds=list(context.bounds),
                baselines=list(context.baselines),
                targets=list(context.targets),
                missing=missing,
                on_zero_coverage=on_zero_coverage,
            )

    random_baseline = beats_random_baseline(
        matrix, context.polarity, context.baselines, metric_ids=ids
    )
    noise_floor = noise_floor_separation(matrix, context.noise_floors, ranks=result.ranks)

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
        versions=context.versions,
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
        leave_one_dataset_out=lodo_report,
        random_baseline=random_baseline,
        noise_floor=noise_floor,
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


def _matrix_for_ranking(
    scores: Scores, registry: Registry, on_zero_coverage: str = "error"
) -> np.ndarray:
    """Fold a tool by dataset by metric tensor to a tool by metric matrix.

    Each metric column is reduced over the dataset axis with the rule on its
    card (``comparability.recommended_aggregation_across_datasets``), nan-aware
    so a tool missing on some datasets is summarized over the datasets where it
    was observed. A tool with no observation at all for a metric leaves a
    missing cell; under the default ``on_zero_coverage="error"`` that raises,
    and under ``"nan"`` it is left for the ranking call's missing-data policy.
    """
    if not scores.is_tensor:
        return scores.values
    rules = _reduction_rules(scores.metric_ids, registry)
    return reduce_tensor(
        scores.values, rules, metric_ids=scores.metric_ids, on_zero_coverage=on_zero_coverage
    )


def _reduction_rules(metric_ids: Sequence[str], registry: Registry) -> list[str]:
    """Per-metric cross-dataset reduction rules from the cards, defaulting to mean."""
    return [
        registry.get(mid).recommended_aggregation_across_datasets or "arithmetic_mean"
        for mid in metric_ids
    ]
