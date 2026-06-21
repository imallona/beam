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
from collections.abc import Sequence

import matplotlib
import numpy as np
from matplotlib.cm import ScalarMappable
from matplotlib.colors import ListedColormap, Normalize
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle


def _fig_to_base64(fig: Figure) -> str:
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=110, bbox_inches="tight")
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("ascii")


def ranking_plot(
    tool_names: tuple[str, ...],
    composite: np.ndarray,
    ranks: np.ndarray,
    ground_truth_tool: str | None = None,
) -> Figure:
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
    return fig


def ranking_figure(
    tool_names: tuple[str, ...],
    composite: np.ndarray,
    ranks: np.ndarray,
    ground_truth_tool: str | None = None,
) -> str:
    """Base64 PNG of :func:`ranking_plot` for the HTML report."""
    return _fig_to_base64(ranking_plot(tool_names, composite, ranks, ground_truth_tool))


def normalized_heatmap_plot(
    tool_names: tuple[str, ...],
    metric_ids: tuple[str, ...],
    normalized: np.ndarray,
    ranks: np.ndarray,
) -> Figure:
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
    return fig


def normalized_heatmap(
    tool_names: tuple[str, ...],
    metric_ids: tuple[str, ...],
    normalized: np.ndarray,
    ranks: np.ndarray,
) -> str:
    """Base64 PNG of :func:`normalized_heatmap_plot` for the HTML report."""
    return _fig_to_base64(normalized_heatmap_plot(tool_names, metric_ids, normalized, ranks))


def smaa_confidence_plot(
    tool_names: tuple[str, ...],
    confidence_factor: np.ndarray,
    ranks: np.ndarray,
) -> Figure:
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
    return fig


def smaa_confidence_figure(
    tool_names: tuple[str, ...],
    confidence_factor: np.ndarray,
    ranks: np.ndarray,
) -> str:
    """Base64 PNG of :func:`smaa_confidence_plot` for the HTML report."""
    return _fig_to_base64(smaa_confidence_plot(tool_names, confidence_factor, ranks))


def dataset_stability_plot(
    tool_names: tuple[str, ...],
    rank_stability: np.ndarray,
    ranks: np.ndarray,
    n_datasets: int,
) -> Figure:
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
    return fig


def dataset_stability_figure(
    tool_names: tuple[str, ...],
    rank_stability: np.ndarray,
    ranks: np.ndarray,
    n_datasets: int,
) -> str:
    """Base64 PNG of :func:`dataset_stability_plot` for the HTML report."""
    return _fig_to_base64(dataset_stability_plot(tool_names, rank_stability, ranks, n_datasets))


_GROUP_COLORS = (
    "#4477aa",
    "#ee6677",
    "#228833",
    "#ccbb44",
    "#66ccee",
    "#aa3377",
    "#bbbbbb",
)


def rank_heatmap(
    ranks: np.ndarray,
    row_names: Sequence[str],
    col_names: Sequence[str],
    *,
    row_label: str = "tool",
    col_label: str = "column",
    title: str | None = None,
) -> Figure:
    """Heatmap of integer ranks, one rank printed in each cell.

    A general labelled rank grid: rows are tools, columns are whatever the rank
    is taken over, a weighting-by-aggregation configuration or a dataset. Each
    cell holds the tool's rank in that column (1 first), coloured so the better
    ranks are green. The same plot reads as "rank by configuration" or "rank by
    dataset" depending on what the columns are.

    Parameters
    ----------
    ranks
        ``(n_rows, n_cols)`` integer ranks, 1 best.
    row_names, col_names
        Row and column labels.
    row_label, col_label
        Axis labels.
    title
        Optional figure title.
    """
    ranks = np.asarray(ranks, dtype=float)
    n_rows, n_cols = ranks.shape
    fig = Figure(figsize=(max(4.0, 0.6 * n_cols + 2.0), max(2.5, 0.4 * n_rows + 1.0)))
    ax = fig.subplots()
    ax.imshow(ranks, aspect="auto", cmap="RdYlGn_r", vmin=1, vmax=max(2, n_rows))
    ax.set_xticks(range(n_cols))
    ax.set_xticklabels(list(col_names), rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels(list(row_names), fontsize=8)
    ax.set_xlabel(col_label)
    ax.set_ylabel(row_label)
    for i in range(n_rows):
        for j in range(n_cols):
            if not np.isnan(ranks[i, j]):
                ax.text(j, i, f"{int(ranks[i, j])}", ha="center", va="center", fontsize=7)
    if title:
        ax.set_title(title, fontsize=10)
    return fig


def score_heatmap(
    values: np.ndarray,
    row_names: Sequence[str],
    col_names: Sequence[str],
    *,
    row_label: str = "tool",
    col_label: str = "dataset",
    value_label: str = "score",
    log: bool = False,
    highlight_best_per_col: bool = False,
    higher_is_better: bool = True,
    title: str | None = None,
) -> Figure:
    """Heatmap of raw scores, tools by columns, NaN-aware.

    Draws the raw tool-by-dataset (or tool-by-group) scores. Missing cells are
    left grey rather than imputed. With ``highlight_best_per_col`` the best score
    in each column is outlined, the ground-truth box the transportation and M4
    vignettes draw. ``log`` colours on a log scale for a metric that spans orders
    of magnitude.

    Parameters
    ----------
    values
        ``(n_rows, n_cols)`` raw scores, may contain NaN.
    row_names, col_names
        Row and column labels.
    row_label, col_label, value_label
        Axis and colourbar labels.
    log
        Colour on a log scale (values must be positive where present).
    highlight_best_per_col
        Outline the best cell per column, by ``higher_is_better``.
    higher_is_better
        Direction used to pick the best cell when highlighting.
    title
        Optional figure title.
    """
    from matplotlib.colors import LogNorm

    values = np.asarray(values, dtype=float)
    n_rows, n_cols = values.shape
    masked = np.ma.masked_invalid(values)
    cmap = matplotlib.colormaps["viridis"].copy()
    cmap.set_bad("#dddddd")
    fig = Figure(figsize=(max(4.0, 0.7 * n_cols + 2.0), max(2.5, 0.4 * n_rows + 1.0)))
    ax = fig.subplots()
    norm = None
    if log:
        positive = masked.compressed()
        positive = positive[positive > 0]
        if positive.size:
            norm = LogNorm(vmin=float(positive.min()), vmax=float(positive.max()))
    image = ax.imshow(masked, aspect="auto", cmap=cmap, norm=norm)
    ax.set_xticks(range(n_cols))
    ax.set_xticklabels(list(col_names), rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels(list(row_names), fontsize=8)
    ax.set_xlabel(col_label)
    ax.set_ylabel(row_label)
    bar = fig.colorbar(image, ax=ax, fraction=0.046)
    bar.set_label(value_label)
    if highlight_best_per_col:
        for j in range(n_cols):
            col = masked[:, j]
            if col.count() == 0:
                continue
            best = int(np.ma.argmax(col) if higher_is_better else np.ma.argmin(col))
            ax.add_patch(
                Rectangle((j - 0.5, best - 0.5), 1, 1, fill=False, edgecolor="#cc3311", linewidth=2)
            )
    if title:
        ax.set_title(title, fontsize=10)
    return fig


def effects_plot(
    labels: Sequence[str],
    estimates: np.ndarray,
    errors: np.ndarray | None = None,
    *,
    xlabel: str = "estimate",
    title: str | None = None,
) -> Figure:
    """Horizontal point estimates with optional error bars, best at the top.

    The shared drawing for a model's per-method estimate: the mixed-effects
    marginal means, the Plackett-Luce or Bradley-Terry worths. Methods are
    ordered by the estimate, largest first. Overlapping error bars between
    neighbours read as not separable.
    """
    labels = list(labels)
    estimates = np.asarray(estimates, dtype=float)
    order = np.argsort(-estimates)
    names = [labels[i] for i in order]
    est = estimates[order]
    err = None if errors is None else np.asarray(errors, dtype=float)[order]
    fig = Figure(figsize=(7, max(2.0, 0.4 * len(names) + 0.5)))
    ax = fig.subplots()
    ax.errorbar(
        est, range(len(names)), xerr=err, fmt="o", color="#4477aa", ecolor="#88aacc", capsize=3
    )
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names)
    ax.invert_yaxis()
    ax.set_xlabel(xlabel)
    ax.set_ylabel("method")
    if title:
        ax.set_title(title, fontsize=10)
    return fig


def variance_shares_plot(
    components: dict[str, float],
    *,
    title: str | None = None,
) -> Figure:
    """Bar chart of variance components as shares of the total.

    Takes the ``variance_components`` map from a mixed-effects or source-variance
    report (factor name to variance) and draws each as a share of the total, so
    the bars sum to one. The residual or dispersion bar is greyed.
    """
    names = list(components)
    values = np.array([components[k] for k in names], dtype=float)
    total = float(values.sum())
    shares = values / total if total > 0 else values
    colors = ["#bbbbbb" if k.lower() in {"residual", "dispersion"} else "#4477aa" for k in names]
    fig = Figure(figsize=(max(4.0, 1.1 * len(names) + 1.5), 3.5))
    ax = fig.subplots()
    ax.bar(range(len(names)), shares, color=colors)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=20, ha="right", fontsize=9)
    ax.set_ylabel("share of variance")
    ax.set_xlabel("component")
    ax.set_ylim(0, 1)
    if title:
        ax.set_title(title, fontsize=10)
    return fig


def bradley_terry_leaves_plot(report, *, title: str | None = None) -> Figure:
    """Bar chart of the datasets per Bradley-Terry tree leaf, labelled by the
    method ranking first in each leaf.

    Each leaf of the tree is one bar, its length the number of datasets in the
    leaf, annotated with the method that ranks first there. A tree that did not
    split has one bar holding every dataset. Takes a ``BradleyTerryTreeReport``.
    """
    leaves = list(report.terminal_nodes)
    assignment = list(report.leaf_assignment)
    sizes, names = [], []
    for node in leaves:
        size = node.n if node.n is not None else assignment.count(node.id)
        sizes.append(int(size))
        first = report.node_ranking(node.id)[0]
        names.append(f"leaf {node.id}: {first}")
    fig = Figure(figsize=(7, max(2.0, 0.5 * len(leaves) + 0.8)))
    ax = fig.subplots()
    ax.barh(range(len(leaves)), sizes, color="#228833")
    ax.set_yticks(range(len(leaves)))
    ax.set_yticklabels(names, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("datasets in the leaf")
    ax.set_ylabel("Bradley-Terry leaf (method ranking first)")
    if title:
        ax.set_title(title, fontsize=10)
    return fig


def rank_bump(
    method_names: tuple[str, ...],
    columns: tuple[str, ...],
    ranks: np.ndarray,
    *,
    divider_after: int | None = None,
    title: str | None = None,
    host: Figure | None = None,
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
    fig = (
        host
        if host is not None
        else Figure(figsize=(1.7 * n_cols + 3.0, max(3.0, 0.5 * n_methods)))
    )
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
    norm_consensus_low: np.ndarray | None = None,
    norm_consensus_high: np.ndarray | None = None,
    norm_consensus_label: str = "rank span across\nnormalizations (1 is best)",
    smaa_acceptability: np.ndarray | None = None,
    title: str | None = None,
    host: Figure | None = None,
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
    norm_consensus_low, norm_consensus_high
        Optional ``(n_methods,)`` smallest and largest rank per method across
        the normalization strategies; draws the normalization rank-span panel.
    norm_consensus_label
        x-axis label for the normalization panel.
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
    has_norm_consensus = norm_consensus_low is not None and norm_consensus_high is not None
    has_smaa = smaa_acceptability is not None
    n_cliques = len([c for c in cliques if len(c) > 1]) if cliques else 0

    width_ratios = [max(3.0, 0.5 * n_metrics + 0.7 * n_cliques), 1.3]
    kinds = ["glyph", "composite"]
    for present, kind, w in (
        (has_worth, "worth", 2.0),
        (has_lodo, "lodo", 2.0),
        (has_consensus, "consensus", 2.0),
        (has_norm_consensus, "norm_consensus", 2.0),
        (has_smaa, "smaa", 2.6),
    ):
        if present:
            kinds.append(kind)
            width_ratios.append(w)

    fig = (
        host
        if host is not None
        else Figure(figsize=(sum(width_ratios) + 2.5, max(2.5, 0.45 * n_methods)))
    )
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

    # Normalization-consensus rank span.
    if has_norm_consensus:
        _rank_span_panel(
            ax_by_kind["norm_consensus"],
            order,
            ranks,
            norm_consensus_low,
            norm_consensus_high,
            n_methods,
            norm_consensus_label,
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
    if host is None:
        fig.tight_layout()
    return fig


def critical_difference_plot(
    tool_names: tuple[str, ...],
    average_ranks: np.ndarray,
    critical_difference: float,
    cliques: tuple[tuple[int, ...], ...] = (),
    host: Figure | None = None,
) -> Figure:
    """Canonical Friedman-Nemenyi critical-difference diagram (Demsar 2006).

    Each tool sits at its average rank across datasets, rank 1 first. The red
    reference bar at the top is one critical difference wide. A blue bar joins
    each group of tools whose average ranks differ by less than the critical
    difference, the cliques the Nemenyi test cannot separate, so tools under one
    bar are statistically tied. This is the diagram people recognise in machine
    learning benchmarking, drawn here one tool per row so it stays readable for
    the dozen-plus methods a bioinformatics benchmark carries.

    ``cliques`` is the tuple of tool-index groups from a
    ``CriticalDifferenceReport``; pass it to draw the connecting bars. With no
    cliques only the points and the reference bar are drawn.
    """
    order = list(np.argsort(average_ranks))
    row_of = {tool: y for y, tool in enumerate(order)}
    names = [tool_names[i] for i in order]
    values = np.asarray(average_ranks, dtype=float)
    multi = [c for c in cliques if len(c) > 1]
    fig = (
        host
        if host is not None
        else Figure(figsize=(8.0, max(2.5, 0.42 * len(names) + 0.5 * max(1, len(multi)))))
    )
    ax = fig.subplots()
    ax.scatter(values[order], range(len(order)), color="#222222", zorder=3)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names)
    ax.invert_yaxis()
    ax.set_xlabel("average rank across datasets (rank 1 ranks first)")
    ax.set_ylabel("tool")
    lo = float(values.min())
    ax.plot([lo, lo + critical_difference], [-1.0, -1.0], color="#cc3311", lw=3, zorder=4)
    ax.annotate(
        f"critical difference = {critical_difference:.2f}",
        xy=(lo, -1.0),
        xytext=(0, 6),
        textcoords="offset points",
        fontsize=9,
        color="#cc3311",
    )
    for k, clique in enumerate(multi):
        rows = [row_of[i] for i in clique]
        ranks = [values[i] for i in clique]
        y = max(rows) + 0.5 + 0.16 * k
        ax.plot([min(ranks), max(ranks)], [y, y], color="#3a7ca5", lw=4, solid_capstyle="round")
    ax.set_ylim(len(names) - 0.5 + 0.16 * max(1, len(multi)), -1.6)
    return fig


def critical_difference_band_plot(
    tool_names: tuple[str, ...],
    average_ranks: np.ndarray,
    critical_difference: float,
) -> Figure:
    """Average-rank dot plot with the critical difference as a shaded band.

    The alternative to :func:`critical_difference_plot`: tools are placed on a
    rank axis, and a band one critical difference wide is shaded from the
    top-ranked tool, so any tool inside the band is within the critical
    difference of it. It shows the size of the critical difference but only ties
    with the top tool, not every clique.
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
    return fig


def critical_difference_figure(
    tool_names: tuple[str, ...],
    average_ranks: np.ndarray,
    critical_difference: float,
    cliques: tuple[tuple[int, ...], ...] = (),
) -> str:
    """Base64 PNG of :func:`critical_difference_plot` for the HTML report."""
    return _fig_to_base64(
        critical_difference_plot(tool_names, average_ranks, critical_difference, cliques)
    )


def agreement_heatmap(
    labels: Sequence[str],
    tau_matrix: np.ndarray,
    *,
    mean_tau: float | None = None,
    title: str | None = None,
    choice_label: str = "choice",
) -> Figure:
    """Heatmap of the pairwise Kendall tau-b agreement between rankings.

    Generalizable plot for any choice-agreement report whose rankings are
    compared with Kendall tau-b: ``aggregation_agreement`` over the aggregation
    rules and ``normalization_agreement`` over the normalizations both produce a
    square tau matrix indexed by the configuration that ran. A cell near 1 means
    the two configurations order the tools almost identically; a low or negative
    cell means the choice between them changes the order. The value is written in
    each cell so the figure reads without a separate table.

    Parameters
    ----------
    labels
        The configuration labels, in the row and column order of ``tau_matrix``.
    tau_matrix
        ``(n, n)`` Kendall tau-b matrix, diagonal 1, ``nan`` where one ranking
        is constant.
    mean_tau
        Optional mean off-diagonal tau, written into the title when given.
    title
        Optional figure title. A default naming ``choice_label`` is used when
        omitted.
    choice_label
        What the rows and columns are, used in the axis labels and the default
        title (for example ``"aggregation"`` or ``"normalization"``).

    Returns
    -------
    matplotlib.figure.Figure
    """
    labels = list(labels)
    tau = np.asarray(tau_matrix, dtype=float)
    n = len(labels)
    fig = Figure(figsize=(max(3.5, 0.7 * n + 2.0), max(3.0, 0.7 * n + 1.5)))
    ax = fig.subplots()
    image = ax.imshow(tau, cmap="RdYlGn", vmin=-1.0, vmax=1.0)
    ax.set_xticks(range(n))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=9)
    ax.set_yticks(range(n))
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel(choice_label)
    ax.set_ylabel(choice_label)
    for i in range(n):
        for j in range(n):
            value = tau[i, j]
            text = "n/a" if np.isnan(value) else f"{value:.2f}"
            shade = "#222222" if np.isnan(value) or abs(value) < 0.6 else "#ffffff"
            ax.text(j, i, text, ha="center", va="center", fontsize=8, color=shade)
    bar = fig.colorbar(image, ax=ax, fraction=0.046)
    bar.set_label("Kendall tau-b (1 is identical order)")
    if title is None:
        title = f"ranking agreement across {choice_label}s"
        if mean_tau is not None and not np.isnan(mean_tau):
            title += f" (mean tau {mean_tau:.2f})"
    ax.set_title(title, fontsize=10)
    return fig


def rank_deviation_heatmap(
    tool_names: Sequence[str],
    dataset_names: Sequence[str],
    deviation: np.ndarray,
    *,
    title: str | None = None,
) -> Figure:
    """Heatmap of each method's per-dataset rank relative to its own typical rank.

    Reads the ``rank_deviation`` table from a ``DatasetConcordanceReport``: rows
    are methods, columns are datasets, and each cell is the method's rank on that
    dataset minus its mean rank across the datasets. A negative cell (one colour)
    means the method places higher than its average on that dataset; a positive
    cell (the other colour) means it places lower. A method that struggles on a
    dataset relative to its own baseline shows as a strong positive cell, so the
    figure reads as a map of where each method does better or worse than usual,
    without ranking the methods against each other.

    Parameters
    ----------
    tool_names
        Length ``n_tools`` row labels.
    dataset_names
        Length ``n_datasets`` column labels, in the column order of
        ``deviation`` (the evaluated datasets).
    deviation
        ``(n_tools, n_datasets)`` signed rank-deviation table.
    title
        Optional figure title.

    Returns
    -------
    matplotlib.figure.Figure
    """
    tools = list(tool_names)
    datasets = list(dataset_names)
    values = np.asarray(deviation, dtype=float)
    n_tools, n_datasets = values.shape
    limit = float(np.nanmax(np.abs(values))) if values.size else 1.0
    limit = limit if limit > 0 else 1.0
    fig = Figure(figsize=(max(4.0, 0.7 * n_datasets + 2.0), max(3.0, 0.45 * n_tools + 1.5)))
    ax = fig.subplots()
    image = ax.imshow(values, cmap="RdBu_r", vmin=-limit, vmax=limit, aspect="auto")
    ax.set_xticks(range(n_datasets))
    ax.set_xticklabels(datasets, rotation=45, ha="right", fontsize=9)
    ax.set_yticks(range(n_tools))
    ax.set_yticklabels(tools, fontsize=9)
    ax.set_xlabel("dataset")
    ax.set_ylabel("method")
    for i in range(n_tools):
        for j in range(n_datasets):
            value = values[i, j]
            if np.isnan(value):
                continue
            shade = "#ffffff" if abs(value) > 0.6 * limit else "#222222"
            ax.text(j, i, f"{value:+.1f}", ha="center", va="center", fontsize=7, color=shade)
    bar = fig.colorbar(image, ax=ax, fraction=0.046)
    bar.set_label("rank minus the method's mean rank (negative is higher than usual)")
    ax.set_title(title or "method rank by dataset, relative to each method's mean", fontsize=10)
    return fig


def specification_curve_plot(report, *, compact: bool = True, host: Figure | None = None) -> Figure:
    """Specification curve over every combination of analyst choices.

    The top panel plots the rank of the method that ranks first most often, with
    combinations sorted from its best rank to its worst, so a flat line near rank
    1 means that method keeps the top across the choices. The other tools are
    drawn in light gray for context. The lower panels mark which choice each
    combination used, in the same column order.

    The figure width is capped rather than growing with the number of
    combinations, since a specification curve is dense by design and a width that
    scales with the count produces an unreadable canvas. With ``compact`` (the
    default), the weighting and the aggregation are drawn as labelled dot rows
    and the dataset axis is collapsed into one colour strip below them, so a
    benchmark with many datasets stays readable. With ``compact=False`` every
    dataset gets its own labelled row, the fuller dashboard for interactive use.

    Takes a ``SpecificationCurveReport`` from ``beam.mcda.specification_curve``.
    """
    specs = report.specifications
    order = list(report.curve_order)
    n = len(order)
    names = report.tool_names or tuple(f"tool_{i + 1}" for i in range(len(specs[0].ranks)))
    n_tools = len(names)
    top_idx = report.most_frequent_top_tool

    rows = [("weighting", level) for level in report.weightings]
    rows += [("aggregation", level) for level in report.methods]
    datasets = list(report.dataset_names) if report.dataset_names is not None else []
    dataset_as_strip = compact and len(datasets) > 0
    if datasets and not dataset_as_strip:
        rows += [("dataset", d) for d in datasets]

    width = max(7.0, min(13.0, 0.03 * n + 6.0))
    n_strip_rows = len(rows) + (1 if dataset_as_strip else 0)
    height = max(3.5, 0.16 * (n_tools + n_strip_rows) + 1.8)
    fig = host if host is not None else Figure(figsize=(width, height))
    if dataset_as_strip:
        ratios = [2.4, max(1.0, 0.16 * len(rows) + 0.4), 0.5]
        top, mid, strip = fig.subplots(3, 1, sharex=True, gridspec_kw={"height_ratios": ratios})
    else:
        ratios = [2.4, max(1.0, 0.16 * len(rows) + 0.4)]
        top, mid = fig.subplots(2, 1, sharex=True, gridspec_kw={"height_ratios": ratios})
        strip = None

    x = list(range(n))
    for t in range(n_tools):
        series = [specs[order[p]].ranks[t] for p in range(n)]
        top.plot(x, series, color="#e3e3e3", linewidth=0.6, zorder=1)
    top_series = [specs[order[p]].ranks[top_idx] for p in range(n)]
    top.plot(x, top_series, color="#cc3311", linewidth=2, zorder=3, label=names[top_idx])
    top.invert_yaxis()
    top.set_ylabel("rank (1 ranks first)")
    top.set_title(f"specification curve: rank of {names[top_idx]} across {n} specifications")
    top.legend(loc="lower right", fontsize=8)

    for row, (_factor, level) in enumerate(rows):
        active = [
            p
            for p in range(n)
            if level
            in (
                specs[order[p]].weighting,
                specs[order[p]].aggregation,
                specs[order[p]].dataset,
            )
        ]
        mid.scatter(active, [row] * len(active), s=8, color="#222222")
    mid.set_yticks(range(len(rows)))
    mid.set_yticklabels([f"{factor}: {level}" for factor, level in rows], fontsize=8)
    mid.invert_yaxis()
    mid.set_ylabel("choice")
    if strip is None:
        mid.set_xlabel("specification (sorted by the top tool's rank)")

    if dataset_as_strip:
        n_datasets = len(datasets)
        index_of = {d: i for i, d in enumerate(datasets)}
        strip_row = np.array([[index_of[specs[order[p]].dataset] for p in range(n)]], dtype=float)
        cmap = matplotlib.colormaps["tab20"].resampled(max(2, n_datasets))
        image = strip.imshow(
            strip_row,
            aspect="auto",
            cmap=cmap,
            vmin=-0.5,
            vmax=n_datasets - 0.5,
            extent=(-0.5, n - 0.5, 0.5, -0.5),
            interpolation="nearest",
        )
        strip.set_yticks([0])
        strip.set_yticklabels(["dataset"], fontsize=8)
        strip.set_xlabel("specification (sorted by the top tool's rank)")
        # A discrete colour key naming each dataset. It spans the full figure
        # height so the names have room; skipped past 20 datasets, where a strip
        # legend cannot stay readable.
        if n_datasets <= 20:
            bar = fig.colorbar(image, ax=[top, mid, strip], fraction=0.06, pad=0.02)
            bar.set_ticks(range(n_datasets))
            bar.set_ticklabels(datasets, fontsize=6)
            bar.set_label("dataset", fontsize=7)
    return fig


def specification_curve_figure(report) -> str:
    """Base64 PNG of :func:`specification_curve_plot` for the HTML report."""
    return _fig_to_base64(specification_curve_plot(report))


def pairwise_majority_plot(report) -> Figure:
    """Pairwise majority matrix, methods ordered by how many they outperform.

    A filled cell at row i, column j means method i outperforms method j on the
    majority of the datasets they share. Methods are ordered by how many others
    they outperform, so a transitive relation fills the upper triangle and leaves
    the lower one empty. A filled cell below the diagonal means a method
    outperforms one ranked above it, which can only happen inside a cycle, so the
    red cells mark the intransitivity directly.

    Takes a ``PairwiseTransitivityReport`` from ``beam.mcda.pairwise_transitivity``.
    """
    dom = np.asarray(report.dominance)
    n = report.n_methods
    names = report.method_names or tuple(f"method_{i + 1}" for i in range(n))

    if report.consistent_order is not None:
        order = list(report.consistent_order)
    else:
        order = list(np.argsort(-dom.sum(axis=1), kind="stable"))
    ordered_names = [names[i] for i in order]

    tied = set()
    for a, b in report.tied_pairs:
        tied.add((a, b))
        tied.add((b, a))

    # 0 empty, 1 consistent edge (upper triangle), 2 back-edge (cycle), 3 tie, 4 diagonal
    grid = np.zeros((n, n))
    for r, i in enumerate(order):
        for c, j in enumerate(order):
            if i == j:
                grid[r, c] = 4
            elif (i, j) in tied:
                grid[r, c] = 3
            elif dom[i, j] == 1:
                grid[r, c] = 1 if r < c else 2

    cmap = ListedColormap(["#f4f4f4", "#3b6ea5", "#cc3311", "#cfcfcf", "#777777"])
    side = max(3.0, 0.45 * n + 1.5)
    fig = Figure(figsize=(side, side))
    ax = fig.subplots()
    ax.imshow(grid, cmap=cmap, vmin=-0.5, vmax=4.5)
    ax.set_xticks(range(n))
    ax.set_xticklabels(ordered_names, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(n))
    ax.set_yticklabels(ordered_names, fontsize=8)
    ax.set_xlabel("method outperformed (column)")
    ax.set_ylabel("method (row), ordered by methods outperformed")

    triads = report.n_circular_triads
    if report.is_transitive:
        title = "pairwise majorities: transitive, one order is consistent"
    else:
        title = f"pairwise majorities: {triads} circular triad{'' if triads == 1 else 's'}"
    ax.set_title(title, fontsize=10)

    legend = [
        Patch(facecolor="#3b6ea5", label="outperforms (consistent with the order)"),
        Patch(facecolor="#cc3311", label="outperforms a higher-ranked method (cycle)"),
        Patch(facecolor="#cfcfcf", label="tied"),
    ]
    ax.legend(handles=legend, loc="lower left", fontsize=7, framealpha=0.9)
    return fig


def pairwise_majority_figure(report) -> str:
    """Base64 PNG of :func:`pairwise_majority_plot` for the HTML report."""
    return _fig_to_base64(pairwise_majority_plot(report))


def bayesian_comparison_plot(report) -> Figure:
    """Heatmap of the posterior probability that the row method is better.

    Cell ``[i, j]`` is the posterior probability that method ``i`` is practically
    better than method ``j`` across the datasets they share, from the Bayesian
    sign test. Methods are ordered by standing, so the strong cells gather in the
    upper triangle. The value is written in each cell. Takes a
    ``BayesianSignReport`` from ``beam.mcda.bayesian_sign_comparison``.
    """
    prob = np.asarray(report.probability_better, dtype=float)
    n = prob.shape[0]
    names = report.method_names or tuple(f"method_{i + 1}" for i in range(n))
    order = list(report.order)
    ordered_names = [names[i] for i in order]
    ordered = prob[np.ix_(order, order)]

    fig = Figure(figsize=(max(3.5, 0.7 * n + 2.0), max(3.0, 0.7 * n + 1.5)))
    ax = fig.subplots()
    ax.imshow(ordered, cmap="Blues", vmin=0.0, vmax=1.0)
    ax.set_xticks(range(n))
    ax.set_xticklabels(ordered_names, rotation=45, ha="right", fontsize=9)
    ax.set_yticks(range(n))
    ax.set_yticklabels(ordered_names, fontsize=9)
    ax.set_xlabel("method compared against (column)")
    ax.set_ylabel("method (row), ordered by standing")
    for i in range(n):
        for j in range(n):
            value = ordered[i, j]
            text = "" if np.isnan(value) else f"{value:.2f}"
            shade = "#ffffff" if not np.isnan(value) and value > 0.6 else "#222222"
            ax.text(j, i, text, ha="center", va="center", color=shade, fontsize=8)
    ax.set_title(
        f"posterior P(row practically better than column), ROPE {report.rope:g}",
        fontsize=10,
    )
    return fig


def bayesian_comparison_figure(report) -> str:
    """Base64 PNG of :func:`bayesian_comparison_plot` for the HTML report."""
    return _fig_to_base64(bayesian_comparison_plot(report))


def _group_order(metric_ids, groups):
    """Indices that sort metrics by group, keeping the within-group input order."""
    seen: list[str] = []
    for g in groups:
        if g not in seen:
            seen.append(g)
    order: list[int] = []
    for g in seen:
        order += [i for i, gi in enumerate(groups) if gi == g]
    return order, seen


def metric_correlation_heatmap(
    report, *, host: Figure | None = None, title: str | None = None
) -> Figure:
    """Oriented metric correlation heatmap, metrics grouped by construct.

    Draws the polarity-oriented Spearman correlation between metrics from a
    ``MetricValidityReport`` on a diverging scale centred at zero, with the
    metrics ordered and bracketed by their construct group. The block structure
    on the diagonal is the convergent evidence (within-group agreement); the
    off-block cells are the discriminant evidence (between-group agreement).

    Takes a ``MetricValidityReport`` from ``beam.mcda.metric_validity``.
    """
    corr = np.asarray(report.correlation, dtype=float)
    n = corr.shape[0]
    labels = (
        list(report.metric_ids) if report.metric_ids is not None else [str(i) for i in range(n)]
    )
    groups = list(report.groups)
    order, group_names = _group_order(labels, groups)
    ordered = corr[np.ix_(order, order)]
    names = [labels[i] for i in order]
    ordered_groups = [groups[i] for i in order]

    fig = host if host is not None else Figure(figsize=(6.5, 5.6))
    ax = fig.subplots()
    cmap = matplotlib.colormaps["RdBu_r"].copy()
    cmap.set_bad("#dddddd")
    im = ax.imshow(np.ma.masked_invalid(ordered), cmap=cmap, vmin=-1.0, vmax=1.0)
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(names, rotation=90, fontsize=7)
    ax.set_yticklabels(names, fontsize=7)

    # Group separators between the blocks.
    boundaries = []
    pos = 0
    for g in group_names:
        size = ordered_groups.count(g)
        pos += size
        if pos < n:
            boundaries.append(pos - 0.5)
    for b in boundaries:
        ax.axhline(b, color="#222222", linewidth=1.0)
        ax.axvline(b, color="#222222", linewidth=1.0)

    # Group brackets and labels down the left margin.
    start = 0
    for g in group_names:
        size = ordered_groups.count(g)
        mid = start + (size - 1) / 2.0
        ax.annotate(
            g,
            xy=(-0.06, mid),
            xycoords=("axes fraction", "data"),
            rotation=90,
            ha="center",
            va="center",
            fontsize=9,
            fontweight="bold",
        )
        start += size
    bar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    bar.set_label("oriented Spearman correlation")
    if title:
        ax.set_title(title, fontsize=10)
    return fig


def reliability_if_dropped_plot(
    report,
    *,
    alpha_threshold: float = 0.7,
    host: Figure | None = None,
    title: str | None = None,
) -> Figure:
    """Cronbach's alpha if each metric is dropped, faceted by construct group.

    One facet per group with at least three metrics. Each bar is the group's
    standardized alpha recomputed without that metric; a bar above the group's
    own alpha (the dashed reference line) marks a metric whose removal makes the
    group more reliable. A second dotted line marks the ``alpha_threshold``
    adequacy cutoff.

    Takes a ``MetricReliabilityReport`` from ``beam.mcda.metric_reliability``.
    """
    by_group: dict[str, list[tuple[str, float]]] = {}
    for metric, group, alpha_without in report.alpha_if_dropped:
        by_group.setdefault(group, []).append((metric, alpha_without))
    group_names = list(by_group)
    if not group_names:
        group_names = ["(no group with 3+ metrics)"]
        by_group[group_names[0]] = []

    fig = host if host is not None else Figure(figsize=(2.8 * len(group_names) + 1.0, 3.4))
    axes = np.atleast_1d(fig.subplots(1, len(group_names), sharey=True))

    # A focused y-range so the small differences between the dropped-metric
    # alphas are visible; the reference lines (group alpha, adequacy cutoff) are
    # what the panel is read against, so a zoomed baseline is the right view.
    all_values = [a for entries in by_group.values() for _, a in entries]
    refs = [v for v in report.alpha_by_group.values() if np.isfinite(v)] + [alpha_threshold]
    finite = [v for v in all_values if np.isfinite(v)] + refs
    low = min(finite) - 0.05 if finite else 0.0
    high = min(1.0, max(finite) + 0.05) if finite else 1.0

    for i, (ax, group) in enumerate(zip(axes, group_names, strict=True)):
        entries = by_group[group]
        metrics = [m for m, _ in entries]
        values = np.array([a for _, a in entries], dtype=float)
        group_alpha = report.alpha_by_group.get(group)
        ax.bar(range(len(metrics)), values, color="#4477aa")
        ax.set_xticks(range(len(metrics)))
        ax.set_xticklabels(metrics, rotation=90, fontsize=6)
        if group_alpha is not None and np.isfinite(group_alpha):
            ax.axhline(
                group_alpha,
                color="#ee6677",
                linestyle="--",
                linewidth=1.2,
                label=f"group alpha {group_alpha:.2f}",
            )
        ax.axhline(
            alpha_threshold,
            color="#888888",
            linestyle=":",
            linewidth=1.0,
            label=f"adequacy {alpha_threshold:g}",
        )
        ax.set_ylim(low, high)
        ax.set_title(group, fontsize=8)
        if i == 0:
            ax.legend(fontsize=5.5, loc="lower left")
    axes[0].set_ylabel("alpha if dropped")
    if title:
        fig.suptitle(title, fontsize=10)
    return fig


def dimensionality_scree_plot(
    report, *, host: Figure | None = None, title: str | None = None
) -> Figure:
    """Eigenvalue scree per construct group, with the Kaiser cutoff at one.

    One line per assessed group joining the descending eigenvalues of its
    oriented metric-correlation matrix against the component index. The
    horizontal line at one is the Kaiser rule; the number of components parallel
    analysis retains (the recommended reading) is annotated per group. A group
    whose curve clears the line at more than one component carries more than one
    factor.

    Takes a ``MetricDimensionalityReport`` from ``beam.mcda.metric_dimensionality``.
    """
    fig = host if host is not None else Figure(figsize=(5.6, 3.6))
    ax = fig.subplots()
    colors = ["#4477aa", "#ee6677", "#228833", "#aa3377"]
    max_k = 1
    for i, (group, eigenvalues) in enumerate(report.eigenvalues_by_group.items()):
        values = np.asarray(eigenvalues, dtype=float)
        x = np.arange(1, len(values) + 1)
        max_k = max(max_k, len(values))
        n_parallel = report.parallel_components_by_group.get(group)
        color = colors[i % len(colors)]
        ax.plot(
            x,
            values,
            "-o",
            color=color,
            markersize=5,
            label=f"{group} (parallel analysis: {n_parallel})",
        )
    ax.axhline(1.0, color="#888888", linestyle="--", linewidth=1.0, label="Kaiser cutoff = 1")
    ax.set_xticks(range(1, max_k + 1))
    ax.set_xlabel("component")
    ax.set_ylabel("eigenvalue")
    ax.legend(fontsize=8, loc="upper right")
    if title:
        ax.set_title(title, fontsize=10)
    return fig


def network_forest_plot(report, *, host: Figure | None = None, title: str | None = None) -> Figure:
    """Forest plot of network-meta effects against the reference treatment.

    Each method's pooled mean-rank difference from the reference, with its 95
    percent confidence interval as a horizontal whisker and a vertical line at
    zero. Smaller is better when the effect measure is a mean-rank difference, so
    a method whose interval sits left of zero outranks the reference. The P-score
    (the probability a method outranks a random competitor) is annotated per row.

    Takes a ``NetworkMetaReport`` from ``beam.heterogeneity.network_meta_analysis``.
    """
    treatments = list(report.treatments)
    effect = np.asarray(report.effect, dtype=float)
    lower = np.asarray(report.effect_lower, dtype=float)
    upper = np.asarray(report.effect_upper, dtype=float)
    pscore = np.asarray(report.pscore, dtype=float)
    order = list(np.argsort(effect))
    names = [treatments[i] for i in order]

    fig = host if host is not None else Figure(figsize=(6.5, max(2.5, 0.5 * len(names) + 1.0)))
    ax = fig.subplots()
    y = np.arange(len(order))
    for k, i in enumerate(order):
        ax.plot(
            [lower[i], upper[i]],
            [y[k], y[k]],
            color="#4477aa",
            linewidth=2.5,
            solid_capstyle="round",
        )
        ax.plot([effect[i]], [y[k]], marker="o", color="#222222", markersize=5, zorder=3)
        ax.annotate(
            f"P={pscore[i]:.2f}",
            xy=(upper[i], y[k]),
            xytext=(6, 0),
            textcoords="offset points",
            va="center",
            fontsize=7,
            color="#555555",
        )
    ax.axvline(0.0, color="#cc3311", linestyle="--", linewidth=1.0)
    ax.set_yticks(y)
    ax.set_yticklabels(names)
    ax.invert_yaxis()
    ax.set_xlabel(f"mean-rank difference vs {report.reference} (smaller is better)")
    ax.set_ylabel("method")
    if title:
        ax.set_title(title, fontsize=10)
    return fig


def attribution_progression_plot(
    report, *, host: Figure | None = None, title: str | None = None
) -> Figure:
    """Stacked share of a common rank-variance budget across settings.

    One stacked bar per setting, split into the analyst-choice, dataset, and
    benchmarker shares of a common rank-variance budget. The settings run in the
    order given, from one benchmark to a same-data contrast, so the rising
    analyst-choice share shows the dataset contribution being removed by design.

    Takes an ``AttributionReport`` from ``beam.mcda.attribution_synthesis``.
    """
    settings = list(report.settings)
    labels = [s.label for s in settings]
    analyst = np.array([s.analyst_choice_share for s in settings], dtype=float)
    dataset = np.array([s.dataset_share for s in settings], dtype=float)
    benchmarker = np.array([s.benchmarker_share for s in settings], dtype=float)

    fig = host if host is not None else Figure(figsize=(1.6 * len(settings) + 2.0, 4.0))
    ax = fig.subplots()
    x = np.arange(len(settings))
    ax.bar(x, analyst, label="analyst choice", color="#ee6677")
    ax.bar(x, dataset, bottom=analyst, label="dataset", color="#4477aa")
    ax.bar(x, benchmarker, bottom=analyst + dataset, label="benchmarker", color="#228833")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylim(0, 1)
    ax.set_ylabel("share of rank-variance budget")
    ax.set_xlabel("setting")
    ax.legend(fontsize=8, loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.12))
    if title:
        ax.set_title(title, fontsize=10, pad=20)
    return fig
