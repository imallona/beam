"""Matplotlib figures for the HTML report, returned as base64 PNG strings.

Every figure labels both axes. The figures are embedded directly in the HTML
as data URIs, so a report is a single self-contained file with no external
assets.

These functions build figures with ``matplotlib.figure.Figure`` directly,
without ``pyplot`` and without calling ``matplotlib.use``. That matters because
beam imports this module at package import time (``beam.report``), and switching
the global matplotlib backend on import would break inline plotting in any
notebook or Quarto vignette that imports beam. ``Figure.savefig`` writes a PNG
without a GUI backend, so this still works headless.
"""

from __future__ import annotations

import base64
import io

import matplotlib
import numpy as np
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
from matplotlib.figure import Figure
from matplotlib.lines import Line2D


def _fig_to_base64(fig: Figure) -> str:
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=110, bbox_inches="tight")
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
    fig = Figure(figsize=(7, max(2.0, 0.4 * len(names))))
    ax = fig.subplots()
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
    fig = Figure(figsize=(1.2 * len(metric_ids) + 2, max(2.0, 0.4 * len(names))))
    ax = fig.subplots()
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
    fig = Figure(figsize=(7, max(2.0, 0.4 * len(names))))
    ax = fig.subplots()
    ax.barh(range(len(names)), values, color="#4477aa")
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names)
    ax.invert_yaxis()
    ax.set_xlabel("share of random weightings ranked first (percent)")
    ax.set_ylabel("tool (ordered by headline rank)")
    ax.set_xlim(0, 100)
    return _fig_to_base64(fig)


def dataset_stability_figure(
    tool_names: tuple[str, ...],
    rank_stability: np.ndarray,
    ranks: np.ndarray,
    n_datasets: int,
) -> str:
    """Bar chart of the per-tool leave-one-dataset-out rank stability.

    Each bar is the share of leave-one-dataset-out runs in which the tool kept
    its base rank, so a bar near 100 percent means the tool's position does not
    depend on any single dataset. Tools are ordered by their headline rank.
    """
    order = np.argsort(ranks)
    names = [tool_names[i] for i in order]
    values = rank_stability[order] * 100.0
    fig = Figure(figsize=(7, max(2.0, 0.4 * len(names))))
    ax = fig.subplots()
    ax.barh(range(len(names)), values, color="#ee8866")
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names)
    ax.invert_yaxis()
    ax.set_xlabel(f"rank held across {n_datasets} leave-one-dataset-out runs (percent)")
    ax.set_ylabel("tool (ordered by headline rank)")
    ax.set_xlim(0, 100)
    return _fig_to_base64(fig)


_GROUP_COLORS = (
    "#4477aa",
    "#ee6677",
    "#228833",
    "#ccbb44",
    "#66ccee",
    "#aa3377",
    "#bbbbbb",
)


def rank_bump(
    method_names: tuple[str, ...],
    columns: tuple[str, ...],
    ranks: np.ndarray,
    *,
    divider_after: int | None = None,
    title: str | None = None,
) -> Figure:
    """A subway (bump) chart of method ranks across columns.

    Each method is a line that connects its rank in each column, with rank 1 at
    the top. Columns are benchmarks or aggregation rules. Where the lines cross
    a lot the columns disagree on the order; where they run parallel the columns
    agree. An optional vertical divider separates two groups of columns (for
    example the benchmarks' published rankings on the left from beam's
    consistent re-ranking on the right), so the eye can compare how tangled each
    side is.

    Parameters
    ----------
    method_names
        The methods, one line each.
    columns
        Column labels along the x-axis.
    ranks
        ``(n_methods, n_columns)`` integer ranks, 1 best, aligned with
        ``method_names`` and ``columns``.
    divider_after
        Draw a dashed vertical line after this column index (0-based) to split
        the chart into two groups.
    title
        Optional figure title.

    Returns
    -------
    matplotlib.figure.Figure
    """
    ranks = np.asarray(ranks, dtype=float)
    n_methods, n_cols = ranks.shape
    fig = Figure(figsize=(1.7 * n_cols + 3.0, max(3.0, 0.5 * n_methods)))
    ax = fig.subplots()
    x = np.arange(n_cols)
    for i, name in enumerate(method_names):
        color = _GROUP_COLORS[i % len(_GROUP_COLORS)]
        ax.plot(x, ranks[i], "-o", color=color, linewidth=2, markersize=7, label=name)
        ax.annotate(
            name,
            (x[0], ranks[i, 0]),
            xytext=(-6, 0),
            textcoords="offset points",
            ha="right",
            va="center",
            fontsize=9,
            color=color,
        )
        ax.annotate(
            name,
            (x[-1], ranks[i, -1]),
            xytext=(6, 0),
            textcoords="offset points",
            ha="left",
            va="center",
            fontsize=9,
            color=color,
        )
    if divider_after is not None:
        ax.axvline(divider_after + 0.5, color="#555555", linestyle="--", linewidth=1)
    ax.set_xticks(x)
    ax.set_xticklabels(columns, fontsize=9)
    ax.set_yticks(range(1, n_methods + 1))
    ax.set_ylim(n_methods + 0.5, 0.5)  # rank 1 at the top
    ax.set_ylabel("rank (1 is best)")
    ax.margins(x=0.18)
    if title:
        ax.set_title(title)
    return fig


def _rank_span_panel(ax, order, ranks, low, high, n_methods, xlabel):
    """Draw a per-method rank-span panel: a coloured bar from best to worst rank."""
    y = np.arange(n_methods)
    low = np.asarray(low, dtype=float)[order]
    high = np.asarray(high, dtype=float)[order]
    pooled = np.asarray(ranks, dtype=float)[order]
    for k in range(n_methods):
        span = high[k] - low[k]
        shade = "#228833" if span < 0.5 else ("#ccbb44" if span <= 2.0 else "#ee6677")
        ax.plot([low[k], high[k]], [y[k], y[k]], color=shade, linewidth=3, solid_capstyle="round")
        ax.plot([pooled[k]], [y[k]], marker="o", color="#222222", markersize=4)
    ax.set_ylim(n_methods - 0.5, -0.5)
    ax.set_yticks([])
    ax.set_xlim(0.5, n_methods + 0.5)  # rank 1 (best) on the left
    ax.set_xlabel(xlabel)


def funky_heatmap(
    normalized: np.ndarray,
    method_names: tuple[str, ...],
    metric_names: tuple[str, ...],
    composite: np.ndarray,
    ranks: np.ndarray,
    *,
    metric_groups: tuple[str, ...] | None = None,
    rank_low: np.ndarray | None = None,
    rank_high: np.ndarray | None = None,
    cliques: tuple[tuple[str, ...], ...] | None = None,
    worth: np.ndarray | None = None,
    worth_ci: np.ndarray | None = None,
    worth_label: str = "model worth",
    consensus_low: np.ndarray | None = None,
    consensus_high: np.ndarray | None = None,
    consensus_label: str = "rank span across\naggregations (1 is best)",
    smaa_acceptability: np.ndarray | None = None,
    title: str | None = None,
) -> Figure:
    """A funky heatmap of normalized scores with optional rank-robustness panels.

    The funky heatmap (the glyph table used by dynbenchmark and OpenProblems)
    shows methods as rows, sorted best first, and metrics as columns, with each
    cell a circle whose radius grows with the normalized score and whose colour
    marks the metric group. An overall column carries the composite score as a
    bar. Read alone it looks like a settled ranking. beam adds panels that test
    that reading, each answering whether the row order survives a reasonable
    change. Both the circle sizes and the row order depend on the normalization,
    which beam resolves from the metric cards rather than defaulting to min-max.

    Parameters
    ----------
    normalized
        ``(n_methods, n_metrics)`` array in [0, 1], oriented so higher is better.
    method_names, metric_names
        Row and column labels.
    composite
        ``(n_methods,)`` overall score, drawn as the overall bar.
    ranks
        ``(n_methods,)`` pooled ranks, 1 is best, used to sort the rows.
    metric_groups
        Optional ``(n_metrics,)`` group label per metric for the circle colour.
    rank_low, rank_high
        Optional ``(n_methods,)`` smallest and largest rank per method across
        leave-one-dataset-out runs; draws the dataset rank-span panel.
    cliques
        Optional groups of method names the Friedman-Nemenyi test cannot
        separate; drawn as brackets to the left of the glyph grid.
    worth, worth_ci
        Optional ``(n_methods,)`` model worth (Plackett-Luce, Bradley-Terry or
        mixed-effects) and its half-interval; draws a worth panel with intervals
        so adjacent overlapping intervals read as not separable.
    worth_label
        x-axis label for the worth panel.
    consensus_low, consensus_high
        Optional ``(n_methods,)`` smallest and largest rank per method across
        the five aggregations; draws the aggregation rank-span panel.
    consensus_label
        x-axis label for the aggregation panel.
    smaa_acceptability
        Optional ``(n_methods, n_ranks)`` SMAA rank-acceptability index, entry
        ``[a, k - 1]`` the share of sampled weightings ranking method ``a`` at
        rank ``k``; drawn as a stacked bar per method.
    title
        Optional figure title.

    Returns
    -------
    matplotlib.figure.Figure
    """
    normalized = np.asarray(normalized, dtype=float)
    composite = np.asarray(composite, dtype=float)
    order = np.argsort(ranks)  # rank 1 first
    names = [method_names[i] for i in order]
    mat = normalized[order]
    comp = composite[order]
    n_methods = len(names)
    n_metrics = len(metric_names)
    y = np.arange(n_methods)

    groups = list(metric_groups) if metric_groups is not None else ["all"] * n_metrics
    unique_groups = list(dict.fromkeys(groups))
    group_color = {g: _GROUP_COLORS[i % len(_GROUP_COLORS)] for i, g in enumerate(unique_groups)}

    # Decide which panels are present and their relative widths, in order.
    has_lodo = rank_low is not None and rank_high is not None
    has_worth = worth is not None
    has_consensus = consensus_low is not None and consensus_high is not None
    has_smaa = smaa_acceptability is not None
    n_cliques = len([c for c in cliques if len(c) > 1]) if cliques else 0

    width_ratios = [max(3.0, 0.5 * n_metrics + 0.7 * n_cliques), 1.3]
    kinds = ["glyph", "composite"]
    for present, kind, w in (
        (has_worth, "worth", 2.0),
        (has_lodo, "lodo", 2.0),
        (has_consensus, "consensus", 2.0),
        (has_smaa, "smaa", 2.6),
    ):
        if present:
            kinds.append(kind)
            width_ratios.append(w)

    fig = Figure(figsize=(sum(width_ratios) + 2.5, max(2.5, 0.45 * n_methods)))
    axes = np.atleast_1d(
        fig.subplots(1, len(width_ratios), gridspec_kw={"width_ratios": width_ratios})
    )
    ax_by_kind = dict(zip(kinds, axes, strict=True))

    # Glyph grid: one circle per (method, metric), radius growing with the score.
    ax_heat = ax_by_kind["glyph"]
    for j in range(n_metrics):
        sizes = (0.15 + 0.85 * mat[:, j]) ** 2 * 320.0
        ax_heat.scatter(
            np.full(n_methods, j),
            y,
            s=sizes,
            c=group_color[groups[j]],
            edgecolors="#33333355",
            linewidths=0.5,
        )
    left = -0.5 - 0.9 * n_cliques
    ax_heat.set_xticks(range(n_metrics))
    ax_heat.set_xticklabels(metric_names, rotation=45, ha="right", fontsize=8)
    ax_heat.set_yticks(y)
    ax_heat.set_yticklabels(names)
    ax_heat.set_ylim(n_methods - 0.5, -0.5)
    ax_heat.set_xlim(left, n_metrics - 0.5)
    ax_heat.set_xlabel("metric (circle radius is the normalized score)")
    ax_heat.set_ylabel("method (ordered by pooled rank)")
    if len(unique_groups) > 1:
        handles = [
            Line2D([], [], marker="o", linestyle="", color=group_color[g], label=g)
            for g in unique_groups
        ]
        ax_heat.legend(
            handles=handles,
            loc="upper left",
            bbox_to_anchor=(0, 1.12),
            fontsize=8,
            ncol=len(unique_groups),
        )

    # Critical-difference clique brackets, to the left of the glyph grid. Rows in
    # the same clique are not separable by the Friedman-Nemenyi test.
    if n_cliques:
        row_of = {name: i for i, name in enumerate(names)}
        slot = 0
        for clique in cliques:
            members = [row_of[m] for m in clique if m in row_of]
            if len(members) < 2:
                continue
            x = -1.0 - 0.9 * slot
            top, bot = min(members), max(members)
            ax_heat.plot([x, x], [top, bot], color="#332288", linewidth=1.5)
            ax_heat.plot([x, x + 0.2], [top, top], color="#332288", linewidth=1.5)
            ax_heat.plot([x, x + 0.2], [bot, bot], color="#332288", linewidth=1.5)
            slot += 1

    # Overall composite bar.
    ax_bar = ax_by_kind["composite"]
    ax_bar.barh(y, comp, color="#888888")
    ax_bar.set_ylim(n_methods - 0.5, -0.5)
    ax_bar.set_yticks([])
    ax_bar.set_xlabel("overall\ncomposite")

    # Model worth with confidence intervals: overlapping intervals between
    # adjacent rows mean the two methods are not separable.
    if has_worth:
        ax_w = ax_by_kind["worth"]
        w = np.asarray(worth, dtype=float)[order]
        err = np.asarray(worth_ci, dtype=float)[order] if worth_ci is not None else None
        ax_w.errorbar(
            w,
            y,
            xerr=err,
            fmt="o",
            color="#4477aa",
            ecolor="#88aacc",
            capsize=3,
            markersize=4,
        )
        ax_w.set_ylim(n_methods - 0.5, -0.5)
        ax_w.set_yticks([])
        ax_w.set_xlabel(worth_label)

    # Leave-one-dataset-out rank span.
    if has_lodo:
        _rank_span_panel(
            ax_by_kind["lodo"],
            order,
            ranks,
            rank_low,
            rank_high,
            n_methods,
            "rank span across\nleave-one-dataset-out (1 is best)",
        )

    # Aggregation-consensus rank span.
    if has_consensus:
        _rank_span_panel(
            ax_by_kind["consensus"],
            order,
            ranks,
            consensus_low,
            consensus_high,
            n_methods,
            consensus_label,
        )

    # SMAA rank-acceptability stacked bar: the share of sampled weightings that
    # place each method at each rank, coloured by rank.
    if has_smaa:
        ax_s = ax_by_kind["smaa"]
        acc = np.asarray(smaa_acceptability, dtype=float)[order]
        n_ranks = acc.shape[1]
        cmap = matplotlib.colormaps["viridis"]
        norm = Normalize(vmin=1, vmax=n_ranks)
        for r in range(n_ranks):
            ax_s.barh(
                y,
                acc[:, r],
                left=acc[:, :r].sum(axis=1),
                color=cmap(norm(n_ranks - r)),
                height=0.8,
            )
        ax_s.set_ylim(n_methods - 0.5, -0.5)
        ax_s.set_yticks([])
        ax_s.set_xlim(0, 1)
        ax_s.set_xlabel("SMAA rank acceptability\n(share of weightings)")
        # The bars put rank 1 (best) at the bright end of the colormap. Reverse the
        # colormap on the legend so the colour reads the same way, then flip the axis
        # so rank 1 sits at the top. Without these the legend would put rank 1 at the
        # dark end and start the scale at the worst rank.
        bar = fig.colorbar(ScalarMappable(norm=norm, cmap=cmap.reversed()), ax=ax_s, fraction=0.08)
        bar.set_label("rank (1 best)")
        bar.ax.invert_yaxis()

    if title:
        fig.suptitle(title)
    fig.tight_layout()
    return fig


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
    fig = Figure(figsize=(7, max(2.0, 0.4 * len(names))))
    ax = fig.subplots()
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
