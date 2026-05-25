"""Render a RunResult to a single self-contained HTML report.

The report has six sections: input summary, normalization diagnostics with the
guard warnings, the ranking table, the sensitivity outputs, a critical
difference diagram when the input carries more than one dataset, and a plain
English recommendation paragraph. Figures are embedded as base64 PNGs so the
output is one file with no external assets.
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Any

import numpy as np
from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..api import RunResult
from ..cards import Registry
from ..mcda import critical_difference, run_from_registry
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
    """
    context = _build_context(result, title, ground_truth_tool, registry)
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

    cd = _critical_difference_section(result, registry)
    if cd is not None:
        context["critical_difference"] = cd

    return context


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


def _perturbation_summary(result: RunResult) -> dict[str, Any]:
    pert = result.perturbation
    top = pert.top_rank_perturbation
    summary: dict[str, Any] = {"top_rank_is_fragile": bool(pert.top_rank_is_fragile)}
    if top is not None:
        metric = (
            result.metric_ids[top.criterion]
            if 0 <= top.criterion < len(result.metric_ids)
            else ""
        )
        summary["delta"] = f"{abs(top.delta):.3f}"
        summary["metric"] = metric
    return summary


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
    return {
        "figure": figures.critical_difference_figure(
            result.tool_names, report.average_ranks, report.critical_difference
        ),
        "friedman_pvalue": f"{report.friedman_pvalue:.4g}",
        "critical_difference": f"{report.critical_difference:.3f}",
        "n_datasets": n_datasets,
        "cliques": cliques,
    }
