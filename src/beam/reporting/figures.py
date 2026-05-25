"""Matplotlib figures for the HTML report, returned as base64 PNG strings.

Every figure labels both axes. The figures are embedded directly in the HTML
as data URIs, so a report is a single self-contained file with no external
assets. The backend is forced to Agg so figures render on a headless host.
"""

from __future__ import annotations

import base64
import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def _fig_to_base64(fig) -> str:
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("ascii")


def ranking_figure(
    tool_names: tuple[str, ...],
    composite: np.ndarray,
    ranks: np.ndarray,
    ground_truth_tool: str | None = None,
) -> str:
    """Horizontal bar chart of the composite score per tool, rank 1 at the top.

    When ``ground_truth_tool`` names a tool documented to rank first, its bar
    is outlined so the reader can compare the computed order against the truth.
    """
    order = np.argsort(ranks)
    names = [tool_names[i] for i in order]
    values = composite[order]
    fig, ax = plt.subplots(figsize=(7, max(2.0, 0.4 * len(names))))
    colors = ["#bbbbbb"] * len(names)
    edgecolors = ["none"] * len(names)
    for pos, name in enumerate(names):
        if ground_truth_tool is not None and name == ground_truth_tool:
            edgecolors[pos] = "#cc3311"
    bars = ax.barh(range(len(names)), values, color=colors, edgecolor=edgecolors, linewidth=2)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names)
    ax.invert_yaxis()
    ax.set_xlabel("composite score (higher ranks first)")
    ax.set_ylabel("tool")
    if ground_truth_tool is not None:
        ax.legend([bars[0]], [f"documented first: {ground_truth_tool}"], loc="lower right")
    return _fig_to_base64(fig)


def normalized_heatmap(
    tool_names: tuple[str, ...],
    metric_ids: tuple[str, ...],
    normalized: np.ndarray,
    ranks: np.ndarray,
) -> str:
    """Heatmap of the normalized scores (rows tools by rank, columns metrics)."""
    order = np.argsort(ranks)
    names = [tool_names[i] for i in order]
    data = normalized[order]
    fig, ax = plt.subplots(figsize=(1.2 * len(metric_ids) + 2, max(2.0, 0.4 * len(names))))
    image = ax.imshow(data, aspect="auto", cmap="viridis", vmin=0.0, vmax=1.0)
    ax.set_xticks(range(len(metric_ids)))
    ax.set_xticklabels(metric_ids, rotation=30, ha="right")
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names)
    ax.set_xlabel("metric")
    ax.set_ylabel("tool (ordered by rank)")
    bar = fig.colorbar(image, ax=ax)
    bar.set_label("normalized score in [0, 1] (higher is preferred per metric)")
    return _fig_to_base64(fig)


def smaa_confidence_figure(
    tool_names: tuple[str, ...],
    confidence_factor: np.ndarray,
    ranks: np.ndarray,
) -> str:
    """Bar chart of the SMAA confidence factor (share of draws ranked first)."""
    order = np.argsort(ranks)
    names = [tool_names[i] for i in order]
    values = confidence_factor[order] * 100.0
    fig, ax = plt.subplots(figsize=(7, max(2.0, 0.4 * len(names))))
    ax.barh(range(len(names)), values, color="#4477aa")
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names)
    ax.invert_yaxis()
    ax.set_xlabel("share of random weightings ranked first (percent)")
    ax.set_ylabel("tool (ordered by headline rank)")
    ax.set_xlim(0, 100)
    return _fig_to_base64(fig)


def critical_difference_figure(
    tool_names: tuple[str, ...],
    average_ranks: np.ndarray,
    critical_difference: float,
) -> str:
    """Average-rank plot with the critical difference shown as a reference bar.

    Tools are placed on a rank axis where rank 1 ranks first. A horizontal bar
    of length equal to the critical difference is drawn so the reader can see
    which tools are closer together than the test can separate.
    """
    order = np.argsort(average_ranks)
    names = [tool_names[i] for i in order]
    values = average_ranks[order]
    fig, ax = plt.subplots(figsize=(7, max(2.0, 0.4 * len(names))))
    ax.plot(values, range(len(names)), "o", color="#222222")
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names)
    ax.invert_yaxis()
    ax.set_xlabel("average rank across datasets (rank 1 ranks first)")
    ax.set_ylabel("tool")
    top_rank = values[0]
    ax.axvspan(top_rank, top_rank + critical_difference, color="#cccccc", alpha=0.5)
    ax.annotate(
        f"critical difference = {critical_difference:.2f}",
        xy=(top_rank + critical_difference, 0),
        xytext=(5, 5),
        textcoords="offset points",
        fontsize=9,
    )
    return _fig_to_base64(fig)
