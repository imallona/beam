"""Render a RunResult to a single self-contained HTML report.

The report has these sections: input summary, normalization diagnostics with the
guard warnings, the ranking table, a funky-heatmap glyph table that carries the
rank-robustness panels, the sensitivity outputs, a critical difference diagram
when the input carries more than one dataset, and a plain English recommendation
paragraph. Figures are embedded as base64 PNGs so the output is one file with no
external assets.
"""

from __future__ import annotations

from collections.abc import Sequence
from importlib import resources
from pathlib import Path
from typing import Any

import numpy as np
from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..api import RunResult
from ..cards import Registry
from ..mcda import critical_difference, pairwise_superiority, run_from_registry
from . import figures
from .narrative import recommendation

_TEMPLATE_DIR = Path(str(resources.files("beam").joinpath("reporting", "templates")))
_TEMPLATE_NAME = "report.html.j2"


def write_report(
    result: RunResult,
    path: str | Path,
    *,
    title: str | None = None,
    ground_truth_tool: str | None = None,
    registry: Registry | None = None,
    funky_heatmap: bool = True,
    metric_groups: Sequence[str] | None = None,
) -> None:
    """Write an HTML report for ``result`` to ``path``.

    Parameters
    ----------
    result
        The ``RunResult`` from ``beam.rank``.
    path
        Output file path.
    title
        Optional report title. Defaults to a generated one.
    ground_truth_tool
        Optional name of the tool documented to rank first, drawn on the
        ranking figure for comparison. Used by vignettes that carry a known
        truth; left ``None`` for a plain benchmark CSV.
    registry
        Optional ``Registry`` for the per-dataset critical-difference
        computation. Defaults to a fresh registry.
    funky_heatmap
        Include the funky-heatmap glyph table with its rank-robustness panels
        (leave-one-dataset-out span, SMAA acceptability, aggregation consensus).
        Default True. Set False for a leaner report or when the matplotlib glyph
        table is not wanted.
    metric_groups
        Optional group label per metric, in the order of ``result.metric_ids``,
        used to colour the funky-heatmap columns. Ignored when ``funky_heatmap``
        is False.
    """
    context = _build_context(
        result, title, ground_truth_tool, registry, funky_heatmap, metric_groups
    )
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    html = env.get_template(_TEMPLATE_NAME).render(**context)
    Path(path).write_text(html, encoding="utf-8")


def _build_context(
    result: RunResult,
    title: str | None,
    ground_truth_tool: str | None,
    registry: Registry | None,
    funky_heatmap: bool = True,
    metric_groups: Sequence[str] | None = None,
) -> dict[str, Any]:
    res = result.result
    order = np.argsort(res.ranks)
    ranking_rows = [
        {
            "rank": int(res.ranks[i]),
            "tool": result.tool_names[i],
            "composite": f"{float(res.composite[i]):.4f}",
        }
        for i in order
    ]

    normalization_rows = [
        {"metric": mid, "strategy": strat}
        for mid, strat in zip(result.metric_ids, res.normalization or (), strict=False)
    ]

    context: dict[str, Any] = {
        "title": title or f"beam recommendation: {result.top_tool} ranks first",
        "beam_version": result.manifest.get("beam_version", ""),
        "created_utc": result.manifest.get("created_utc", ""),
        "layout": result.scores.layout,
        "n_tools": len(result.tool_names),
        "metric_ids": list(result.metric_ids),
        "dataset_names": list(result.scores.dataset_names or []),
        "source_path": result.scores.source_path,
        "method": res.method,
        "weighting": res.weighting,
        "ranking_rows": ranking_rows,
        "normalization_rows": normalization_rows,
        "warnings": list(res.warnings),
        "recommendation": recommendation(result),
        "software": result.manifest.get("software", {}),
        "input_sha256": result.manifest.get("input", {}).get("sha256", ""),
        "ranking_figure": figures.ranking_figure(
            result.tool_names, res.composite, res.ranks, ground_truth_tool
        ),
        "heatmap_figure": figures.normalized_heatmap(
            result.tool_names, result.metric_ids, res.normalized, res.ranks
        ),
    }

    if result.smaa is not None:
        context["smaa_figure"] = figures.smaa_confidence_figure(
            result.tool_names, result.smaa.confidence_factor, res.ranks
        )
        context["smaa_rows"] = _smaa_rows(result)
    if result.leave_one_out is not None:
        context["loo"] = _loo_summary(result)
    if result.perturbation is not None:
        context["perturbation"] = _perturbation_summary(result)
    if result.leave_one_dataset_out is not None:
        context["lodo"] = _lodo_summary(result)
        context["lodo_figure"] = figures.dataset_stability_figure(
            result.tool_names,
            result.leave_one_dataset_out.rank_stability,
            res.ranks,
            len(result.leave_one_dataset_out.evaluated_datasets),
        )

    ref = _reference_levels_section(result)
    if ref is not None:
        context["reference_levels"] = ref

    cards = _card_consistency_section(result)
    if cards is not None:
        context["card_consistency"] = cards

    cd = _critical_difference_section(result, registry)
    if cd is not None:
        context["critical_difference"] = cd

    agg = _aggregation_agreement_summary(result)
    if agg is not None:
        context["aggregation_agreement"] = agg

    rs = _rank_sensitivity_section(result)
    if rs is not None:
        context["rank_sensitivity"] = rs

    if funky_heatmap:
        funky = _funky_heatmap_figure(result, metric_groups)
        if funky is not None:
            context["funky_figure"] = funky

    return context


def _aggregation_agreement_summary(result: RunResult) -> dict[str, Any] | None:
    """One-line summary of how much the ranking depends on the aggregation choice.

    Returns the mean pairwise Kendall tau-b across the five aggregations, whether
    they all rank the same tool first, and how many ran. ``None`` when fewer than
    two aggregations produce a ranking on this input.
    """
    from . import _aggregation_agreement_report

    report = _aggregation_agreement_report(result)
    if report is None:
        return None
    tau = report.mean_pairwise_tau
    return {
        "mean_tau": "n/a" if np.isnan(tau) else f"{tau:.2f}",
        "top_is_unanimous": bool(report.top_is_unanimous),
        "top_tool": result.tool_names[report.top_tool],
        "n_methods": len(report.methods),
    }


def _rank_sensitivity_section(result: RunResult) -> dict[str, Any] | None:
    """Split the rank variance between the weighting, aggregation and dataset.

    Runs only for a tensor input with at least two datasets, where the dataset is
    a third factor next to the two modeling choices. Non-run cells are treated as
    the worst score so every dataset is included. Returns the factor shares, the
    most influential factor, and the headline tool's mean rank per dataset, or
    ``None`` when the input is single-dataset or the decomposition cannot run.
    """
    from beam.mcda import rank_sensitivity, specification_curve

    from . import figures

    scores = result.scores
    if not scores.is_tensor or scores.dataset_names is None or scores.values.shape[1] < 2:
        return None

    ctx = result.context
    try:
        report = rank_sensitivity(
            scores.values,
            ctx.polarity,
            normalization=list(ctx.normalization),
            bounds=list(ctx.bounds),
            baselines=list(ctx.baselines),
            targets=list(ctx.targets),
            missing="worst",
            tool_names=result.tool_names,
            dataset_names=scores.dataset_names,
        )
    except ValueError:
        return None

    def _pct(value: float) -> str:
        return "n/a" if np.isnan(value) else f"{value * 100:.0f}"

    headline = result.tool_names[report.headline_tool]
    by_dataset = [
        {"dataset": name, "rank": f"{rank:.1f}"}
        for name, rank in zip(report.dataset_names, report.headline_rank_by_dataset, strict=True)
    ]

    curve = specification_curve(report)
    section = {
        "weighting_pct": _pct(report.weighting_share),
        "aggregation_pct": _pct(report.aggregation_share),
        "dataset_pct": _pct(report.dataset_share),
        "interaction_pct": _pct(report.interaction_share),
        "most_influential": report.most_influential_factor,
        "n_combinations": report.n_combinations,
        "headline_tool": headline,
        "headline_top_pct": _pct(report.headline_top_fraction),
        "headline_rank_span": report.headline_rank_span,
        "headline_by_dataset": by_dataset,
        "dropped_weightings": list(report.dropped_weightings),
        "spec_curve_figure": figures.specification_curve_figure(curve),
        "top_first_pct": _pct(curve.most_frequent_top_fraction),
        "modal_order_pct": _pct(curve.modal_order_fraction),
        "n_distinct_top": curve.n_distinct_top_tools,
    }
    return section


def _funky_heatmap_figure(
    result: RunResult,
    metric_groups: Sequence[str] | None,
) -> str | None:
    """Render the funky-heatmap glyph table as a base64 PNG, or ``None`` if it fails.

    Uses the public ``funky_heatmap_from_run`` path so the report draws the same
    figure the vignettes do. A degenerate input that the figure cannot draw is
    skipped rather than failing the whole report.
    """
    from . import funky_heatmap_from_run

    try:
        fig = funky_heatmap_from_run(result, metric_groups=metric_groups)
    except Exception:
        return None
    return figures._fig_to_base64(fig)


def _smaa_rows(result: RunResult) -> list[dict[str, Any]]:
    res = result.result
    order = np.argsort(res.ranks)
    cf = result.smaa.confidence_factor
    return [
        {"tool": result.tool_names[i], "confidence": f"{float(cf[i]) * 100:.1f}"} for i in order
    ]


def _loo_summary(result: RunResult) -> dict[str, Any]:
    loo = result.leave_one_out
    top_idx = int(np.argmin(result.result.ranks))
    n_metrics = len(result.metric_ids)
    influential = (
        result.metric_ids[loo.most_influential_metric]
        if 0 <= loo.most_influential_metric < n_metrics
        else ""
    )
    return {
        "top_stability_pct": f"{float(loo.rank_stability[top_idx]) * 100:.0f}",
        "most_influential_metric": influential,
        "max_rank_shift": int(loo.max_rank_shift),
        "n_metrics": n_metrics,
    }


def _lodo_summary(result: RunResult) -> dict[str, Any]:
    lodo = result.leave_one_dataset_out
    top_idx = int(np.argmin(result.result.ranks))
    names = lodo.dataset_names
    influential = (
        names[lodo.most_influential_dataset]
        if names is not None and 0 <= lodo.most_influential_dataset < len(names)
        else str(lodo.most_influential_dataset)
    )
    return {
        "top_stability_pct": f"{float(lodo.rank_stability[top_idx]) * 100:.0f}",
        "most_influential_dataset": influential,
        "max_rank_shift": int(lodo.max_rank_shift),
        "n_datasets": len(lodo.evaluated_datasets),
    }


def _perturbation_summary(result: RunResult) -> dict[str, Any]:
    pert = result.perturbation
    top = pert.top_rank_perturbation
    summary: dict[str, Any] = {"top_rank_is_fragile": bool(pert.top_rank_is_fragile)}
    if top is not None:
        metric = (
            result.metric_ids[top.criterion] if 0 <= top.criterion < len(result.metric_ids) else ""
        )
        summary["delta"] = f"{abs(top.delta):.3f}"
        summary["metric"] = metric
    return summary


def _reference_levels_section(result: RunResult) -> dict[str, Any] | None:
    """Build the chance-baseline and noise-floor section, or ``None`` when inactive.

    Returns a dict only when at least one metric declares a chance baseline or a
    noise floor. The chance part lists per-metric beat counts and names the tools
    that beat chance on no metric; the noise-floor part names the indistinguishable
    tool pairs and flags the top two tools when they fall within the floor.
    """
    rb = result.random_baseline
    nf = result.noise_floor
    if (rb is None or not rb.active) and (nf is None or not nf.active):
        return None

    section: dict[str, Any] = {}
    if rb is not None and rb.active:
        section["baseline_rows"] = [
            {
                "metric": mb.metric or "",
                "baseline": f"{mb.baseline:g}",
                "n_beating": mb.n_beating,
                "n_observed": mb.n_observed,
                "pct": "n/a"
                if np.isnan(mb.fraction_beating)
                else f"{mb.fraction_beating * 100:.0f}",
            }
            for mb in rb.per_metric
        ]
        section["tools_never_beating"] = [result.tool_names[i] for i in rb.tools_never_beating]
        section["n_floored_metrics"] = len(rb.per_metric)

    if nf is not None and nf.active:
        section["indistinguishable_pairs"] = [
            f"{result.tool_names[a]} and {result.tool_names[b]}"
            for a, b in nf.indistinguishable_pairs
        ]
        section["top_pair_indistinguishable"] = bool(nf.top_pair_indistinguishable)
        if nf.top_pair is not None:
            a, b = nf.top_pair
            section["top_pair"] = f"{result.tool_names[a]} and {result.tool_names[b]}"
    return section


def _card_consistency_section(result: RunResult) -> dict[str, Any] | None:
    """Build the card-versus-data audit section, or ``None`` when nothing to say.

    Returns a dict only when the audit raised at least one finding. ``violations``
    are hard card-or-data contradictions and ``notes`` are data-dependent
    observations, each a plain-language message.
    """
    audit = result.card_consistency
    if audit is None or not audit.findings:
        return None
    return {
        "ok": bool(audit.ok),
        "violations": [f.message for f in audit.violations],
        "notes": [f.message for f in audit.notes],
    }


def _critical_difference_section(
    result: RunResult,
    registry: Registry | None,
) -> dict[str, Any] | None:
    """Compute a critical-difference section when the input has many datasets.

    Builds a tool by dataset composite matrix by running the same aggregation
    on each dataset slice, then runs the Friedman and Nemenyi analysis. Returns
    ``None`` when the input is single-dataset, has too few tools or datasets for
    the test, or carries missing cells that would make the per-dataset
    composites undefined.
    """
    scores = result.scores
    if not scores.is_tensor or scores.dataset_names is None:
        return None
    tensor = scores.values
    n_tools, n_datasets, _ = tensor.shape
    if n_tools < 3 or n_datasets < 2 or np.isnan(tensor).any():
        return None

    reg = registry if registry is not None else Registry()
    composite = np.empty((n_tools, n_datasets), dtype=float)
    for d in range(n_datasets):
        per_dataset = run_from_registry(
            tensor[:, d, :],
            result.metric_ids,
            weights=result.result.weights,
            method=result.result.method,
            registry=reg,
        )
        composite[:, d] = per_dataset.composite

    report = critical_difference(composite, higher_is_better=True, tool_names=result.tool_names)
    cliques = [[result.tool_names[i] for i in clique] for clique in report.cliques]
    section = {
        "figure": figures.critical_difference_figure(
            result.tool_names, report.average_ranks, report.critical_difference
        ),
        "friedman_pvalue": f"{report.friedman_pvalue:.4g}",
        "critical_difference": f"{report.critical_difference:.3f}",
        "n_datasets": n_datasets,
        "cliques": cliques,
    }

    # Effect-size companion: how often the top method outranks the runner-up
    # across the datasets, not just whether the rank gap is significant.
    sup = pairwise_superiority(composite, "higher_is_better", method_names=result.tool_names)
    top, runner = int(sup.order[0]), int(sup.order[1])
    pair = next(p for p in sup.per_pair if {p.a, p.b} == {top, runner})
    p_top = pair.p_superior_a if pair.a == top else pair.p_superior_b
    section["superiority"] = {
        "top": result.tool_names[top],
        "runner": result.tool_names[runner],
        "n_datasets": pair.n_compared,
        "n_outperformed": pair.a_outperforms if pair.a == top else pair.b_outperforms,
        "pct": "n/a" if np.isnan(p_top) else f"{p_top * 100:.0f}",
    }
    return section
