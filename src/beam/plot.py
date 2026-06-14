"""Public plotting API: saveable matplotlib figures from a beam run.

Every function here returns a ``matplotlib.figure.Figure`` you can show in a
notebook, drop into a Quarto vignette, or write to a file with :func:`save`.
The figure code is shared with the HTML report, so a plot you draw here is the
same one the report embeds. Nothing switches the global matplotlib backend, so
importing this module is safe inside another plotting session.

The functions fall into three groups.

Ranking and stability, each taking a ``RunResult`` from ``beam.rank``:

- :func:`ranking` the composite score per tool
- :func:`normalized_scores` the normalized score heatmap
- :func:`smaa` the share of random weightings that rank each tool first
- :func:`dataset_stability` the leave-one-dataset-out rank stability
- :func:`rank_sensitivity` the share of rank variance carried by each factor
- :func:`funky_heatmap` the glyph table with the rank-robustness panels

Effect dissection, each taking a ``RunResult`` and showing how the ranking
moves when one choice or the data changes, drawn as a bump chart so you can
follow each tool:

- :func:`weighting_effect` across the weighting schemes
- :func:`aggregation_effect` across the five aggregation rules
- :func:`normalization_effect` across the normalization strategies
- :func:`dataset_effect` across the leave-one-dataset-out runs

Agreement and consistency, each taking the matching analysis report:

- :func:`aggregation_agreement` the tau-b heatmap across aggregations
- :func:`normalization_agreement` the tau-b heatmap across normalizations
- :func:`dataset_concordance` the tau-b heatmap across datasets
- :func:`dataset_struggle` the per-dataset rank-deviation map of each method
- :func:`critical_difference` the canonical Friedman-Nemenyi clique-bar diagram
- :func:`critical_difference_band` the shaded-band alternative
- :func:`specification_curve` the rank of the top tool across every combination
- :func:`pairwise_majority` the pairwise majority relation and its cycles
- :func:`bayesian_comparison` the posterior probability one method is better

Grids, heterogeneity and building blocks:

- :func:`rank_heatmap` a labelled integer-rank grid (by configuration or dataset)
- :func:`score_heatmap` a raw tool-by-column score heatmap, NaN-aware
- :func:`rank_bump` a bump chart of method ranks across columns
- :func:`model_effects` per-method effects with error bars (mixed-effects, source-variance)
- :func:`variance_components` variance-component shares from those reports
- :func:`bradley_terry_leaves` datasets per Bradley-Terry leaf, labelled by the method ranking first

The effect plots re-rank the run's reduced matrix, so they hold every other
choice fixed and vary only the named one. A level that cannot run on the input
(for example ``merec`` weighting on a min-max column with a hard zero, or
``log_min_max`` on a column with a non-positive value) is dropped from the
plot, the same way the agreement diagnostics drop it.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from matplotlib.figure import Figure

from .mcda import aggregation_agreement as _aggregation_agreement
from .mcda import normalization_agreement as _normalization_agreement
from .mcda import run as _run
from .reporting import figures as _figures
from .reporting import funky_heatmap_from_run as _funky_heatmap_from_run

_WEIGHTINGS = ("equal", "entropy", "std", "critic", "merec")


def save(fig: Figure, path: str, **kwargs) -> str:
    """Write a figure to ``path``; the extension picks the format.

    A thin wrapper over ``Figure.savefig`` with a tight bounding box, so a
    ``.png``, ``.pdf`` or ``.svg`` path all work. Returns the path.
    """
    kwargs.setdefault("bbox_inches", "tight")
    fig.savefig(path, **kwargs)
    return path


def ranking(run, ground_truth_tool: str | None = None) -> Figure:
    """Bar chart of the composite score per tool, rank 1 at the top.

    ``ground_truth_tool`` outlines the bar of a tool documented to rank first,
    for comparing the computed order against a known answer.
    """
    return _figures.ranking_plot(
        run.tool_names, run.result.composite, run.result.ranks, ground_truth_tool
    )


def normalized_scores(run) -> Figure:
    """Heatmap of the normalized scores, tools by rank against metrics."""
    return _figures.normalized_heatmap_plot(
        run.tool_names, run.metric_ids, run.result.normalized, run.result.ranks
    )


def smaa(run) -> Figure:
    """Bar chart of the SMAA confidence factor, the share of sampled weightings
    that rank each tool first.

    Raises ``ValueError`` when the run carries no SMAA report (sensitivity was
    turned off).
    """
    if run.smaa is None:
        raise ValueError("this run has no SMAA report; run beam.rank with sensitivity=True")
    return _figures.smaa_confidence_plot(
        run.tool_names, run.smaa.confidence_factor, run.result.ranks
    )


def dataset_stability(run) -> Figure:
    """Bar chart of the per-tool leave-one-dataset-out rank stability.

    Raises ``ValueError`` when the run has no leave-one-dataset-out report,
    which happens for a single-dataset input or when sensitivity was off.
    """
    lodo = run.leave_one_dataset_out
    if lodo is None:
        raise ValueError(
            "this run has no leave-one-dataset-out report; it needs a tensor input "
            "with at least two datasets and sensitivity=True"
        )
    return _figures.dataset_stability_plot(
        run.tool_names, lodo.rank_stability, run.result.ranks, len(lodo.evaluated_datasets)
    )


def rank_sensitivity(report) -> Figure:
    """Bar chart of the share of rank variance carried by each factor.

    Takes a ``RankSensitivityReport`` from ``beam.mcda.rank_sensitivity``. The
    factor shares are the first-order variance indices over the factorial of the
    weighting, the aggregation and (for a tensor) the dataset; the interaction
    bar carries what the main effects do not explain. A tall dataset bar means
    the ranking depends mostly on which dataset you use; a tall weighting or
    aggregation bar means it depends on a choice the analyst makes.
    """
    labels = [*report.factors, "interaction"]
    shares = [report.factor_shares[f] for f in report.factors] + [report.interaction_share]
    colors = ["#4477aa"] * len(report.factors) + ["#bbbbbb"]
    fig = Figure(figsize=(max(4.0, 1.0 * len(labels) + 1.5), 3.5))
    ax = fig.subplots()
    ax.bar(range(len(labels)), shares, color=colors)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylabel("share of rank variance")
    ax.set_xlabel("factor")
    ax.set_ylim(0, 1)
    ax.set_title("what moves the ranking")
    return fig


def funky_heatmap(run, **kwargs) -> Figure:
    """The funky glyph table with beam's rank-robustness panels.

    A thin pass-through to ``beam.funky_heatmap_from_run``; see that function
    for the optional panels (model worth, leave-one-dataset-out span, SMAA
    acceptability, aggregation consensus and normalization consensus).
    """
    return _funky_heatmap_from_run(run, **kwargs)


def _context_args(run) -> dict:
    ctx = run.context
    return {
        "normalization": list(ctx.normalization),
        "bounds": list(ctx.bounds),
        "baselines": list(ctx.baselines),
        "targets": list(ctx.targets),
    }


def _bump(tool_names, columns: Sequence[str], rank_rows: list[np.ndarray], title: str) -> Figure:
    """Bump chart of each tool's rank across the given columns."""
    ranks = np.column_stack(rank_rows)
    return _figures.rank_bump(tuple(tool_names), tuple(columns), ranks, title=title)


def weighting_effect(
    run, weightings: Sequence[str] | None = None, missing: str = "error"
) -> Figure:
    """Bump chart of each tool's rank across the weighting schemes.

    Re-ranks the run's reduced matrix under each weighting scheme, holding the
    normalization and the aggregation fixed, so the lines show how much the
    weighting choice alone moves the order. The default schemes are equal,
    entropy, standard deviation, CRITIC and MEREC; a scheme that cannot run on
    the input is dropped.
    """
    names = list(_WEIGHTINGS if weightings is None else weightings)
    ctx = _context_args(run)
    ran, rows = [], []
    for scheme in names:
        try:
            result = _run(
                run.matrix,
                run.context.polarity,
                weights=scheme,
                method=run.result.method,
                missing=missing,
                **ctx,
            )
        except Exception:
            continue
        ran.append(scheme)
        rows.append(result.ranks)
    if len(rows) < 2:
        raise ValueError("fewer than two weighting schemes produced a ranking on this input")
    return _bump(run.tool_names, ran, rows, "weighting effect on the ranking")


def aggregation_effect(run, missing: str = "error") -> Figure:
    """Bump chart of each tool's rank across the five aggregation rules.

    Computes ``aggregation_agreement`` on the run's reduced matrix and draws the
    per-tool ranks, so the lines show how much the aggregation choice alone moves
    the order. An aggregation that cannot run on the input is dropped.
    """
    report = aggregation_agreement_report(run, missing=missing)
    rows = [report.ranks_by_method[m] for m in report.methods]
    return _bump(run.tool_names, report.methods, rows, "aggregation effect on the ranking")


def normalization_effect(run, missing: str = "error") -> Figure:
    """Bump chart of each tool's rank across the normalization strategies.

    Computes ``normalization_agreement`` on the run's reduced matrix, including
    the card-recommended per-metric normalization as one labelled column, and
    draws the per-tool ranks. The lines show how much the normalization choice
    alone moves the order. A strategy that cannot run on the input is dropped.
    """
    report = normalization_agreement_report(run, missing=missing)
    rows = [report.ranks_by_label[label] for label in report.labels]
    return _bump(run.tool_names, report.labels, rows, "normalization effect on the ranking")


def dataset_effect(run) -> Figure:
    """Bump chart of each tool's rank across the leave-one-dataset-out runs.

    The first column is the pooled ranking over all datasets; each later column
    drops one dataset. A line that stays flat means the tool's rank does not
    depend on any single dataset. Raises ``ValueError`` when the run has no
    leave-one-dataset-out report.
    """
    lodo = run.leave_one_dataset_out
    if lodo is None:
        raise ValueError(
            "this run has no leave-one-dataset-out report; it needs a tensor input "
            "with at least two datasets and sensitivity=True"
        )
    columns = ["all datasets"]
    rows = [lodo.base.ranks]
    for index in lodo.evaluated_datasets:
        name = lodo.dataset_names[index] if lodo.dataset_names is not None else f"dataset {index}"
        columns.append(f"drop {name}")
        rows.append(lodo.leave_one_out[index].ranks)
    return _bump(run.tool_names, columns, rows, "leave-one-dataset-out effect on the ranking")


def aggregation_agreement_report(run, missing: str = "error"):
    """Run ``aggregation_agreement`` on a run's reduced matrix and context."""
    return _aggregation_agreement(
        run.matrix,
        run.context.polarity,
        weights=run.result.weighting,
        missing=missing,
        tool_names=run.tool_names,
        **_context_args(run),
    )


def normalization_agreement_report(run, missing: str = "error"):
    """Run ``normalization_agreement`` on a run's reduced matrix and context.

    Passes the card-recommended per-metric normalization as the ``recommended``
    candidate so the headline default is compared against the uniform strategies.
    """
    ctx = _context_args(run)
    return _normalization_agreement(
        run.matrix,
        run.context.polarity,
        weights=run.result.weighting,
        method=run.result.method,
        recommended=ctx["normalization"],
        bounds=ctx["bounds"],
        baselines=ctx["baselines"],
        targets=ctx["targets"],
        missing=missing,
        tool_names=run.tool_names,
    )


def aggregation_agreement(report) -> Figure:
    """Tau-b agreement heatmap across the aggregation rules.

    Takes an ``AggregationAgreementReport``. Accepts a ``RunResult`` too, in
    which case the report is computed first.
    """
    if not hasattr(report, "tau_matrix"):
        report = aggregation_agreement_report(report)
    return _figures.agreement_heatmap(
        report.methods,
        report.tau_matrix,
        mean_tau=report.mean_pairwise_tau,
        choice_label="aggregation",
    )


def normalization_agreement(report) -> Figure:
    """Tau-b agreement heatmap across the normalization strategies.

    Takes a ``NormalizationAgreementReport``. Accepts a ``RunResult`` too, in
    which case the report is computed first.
    """
    if not hasattr(report, "tau_matrix"):
        report = normalization_agreement_report(report)
    return _figures.agreement_heatmap(
        report.labels,
        report.tau_matrix,
        mean_tau=report.mean_pairwise_tau,
        choice_label="normalization",
    )


def _concordance_report(report):
    """Return the DatasetConcordanceReport, unwrapping a RunResult if given one."""
    if hasattr(report, "dataset_concordance"):
        report = report.dataset_concordance
    if report is None:
        raise ValueError(
            "no dataset_concordance report; the run needs a tensor with at least two datasets"
        )
    return report


def _concordance_labels(report) -> list[str]:
    if report.dataset_names is not None:
        return [report.dataset_names[d] for d in report.evaluated_datasets]
    return [f"dataset_{d}" for d in report.evaluated_datasets]


def dataset_concordance(report) -> Figure:
    """Tau-b agreement heatmap across datasets.

    Takes a ``DatasetConcordanceReport``. Accepts a ``RunResult`` too, in which
    case its attached report is used. Each cell is the Kendall tau-b between two
    datasets' method orderings; a low cell marks a pair of datasets that order
    the methods differently.
    """
    report = _concordance_report(report)
    return _figures.agreement_heatmap(
        _concordance_labels(report),
        report.tau_matrix,
        mean_tau=report.mean_pairwise_tau,
        choice_label="dataset",
        title=f"dataset agreement on method ordering (mean tau-b {report.mean_pairwise_tau:.2f})",
    )


def dataset_struggle(report) -> Figure:
    """Map of which methods place better or worse than usual on each dataset.

    Takes a ``DatasetConcordanceReport`` (or a ``RunResult``) and draws its
    ``rank_deviation`` table: rows are methods, columns are datasets, and each
    cell is the method's rank on that dataset minus its mean rank across the
    datasets. A method that struggles on a dataset relative to its own baseline
    shows as a strong positive cell. The figure locates where the dataset
    disagreement comes from without ranking the methods against each other.
    """
    report = _concordance_report(report)
    tools = report.tool_names or tuple(f"tool_{i}" for i in range(report.rank_deviation.shape[0]))
    return _figures.rank_deviation_heatmap(
        tools,
        _concordance_labels(report),
        report.rank_deviation,
    )


def critical_difference(report) -> Figure:
    """Canonical Friedman-Nemenyi critical-difference diagram (Demsar 2006).

    Each tool sits at its average rank, with a blue bar joining each clique the
    Nemenyi test cannot separate. Takes a ``CriticalDifferenceReport`` from
    ``beam.mcda.critical_difference``. See :func:`critical_difference_band` for
    the shaded-band alternative.
    """
    names = report.tool_names or tuple(f"tool_{i + 1}" for i in range(len(report.average_ranks)))
    return _figures.critical_difference_plot(
        names, report.average_ranks, report.critical_difference, report.cliques
    )


def critical_difference_band(report) -> Figure:
    """Average-rank dot plot with the critical difference as a shaded band.

    The alternative to :func:`critical_difference`: a band one critical
    difference wide from the top-ranked tool, so a tool inside it is within the
    critical difference of it. Takes a ``CriticalDifferenceReport``.
    """
    names = report.tool_names or tuple(f"tool_{i + 1}" for i in range(len(report.average_ranks)))
    return _figures.critical_difference_band_plot(
        names, report.average_ranks, report.critical_difference
    )


def specification_curve(report, compact: bool = True) -> Figure:
    """Rank of the top tool across every combination of analyst choices.

    Takes a ``SpecificationCurveReport`` from ``beam.mcda.specification_curve``.
    With ``compact`` (the default) the dataset axis is one colour strip; pass
    ``compact=False`` for the full per-dataset dashboard.
    """
    return _figures.specification_curve_plot(report, compact=compact)


def pairwise_majority(report) -> Figure:
    """Pairwise majority matrix with its cycles marked.

    A filled cell means the row method outperforms the column method on the
    majority of the datasets they share; cells that close a cycle are marked.
    Takes a ``PairwiseTransitivityReport`` from ``beam.mcda.pairwise_transitivity``.
    """
    return _figures.pairwise_majority_plot(report)


def bayesian_comparison(report) -> Figure:
    """Posterior probability that the row method is practically better.

    A heatmap whose cell shows the posterior probability that the row method is
    practically better than the column method across the datasets they share,
    from the Bayesian sign test. Takes a ``BayesianSignReport`` from
    ``beam.mcda.bayesian_sign_comparison``.
    """
    return _figures.bayesian_comparison_plot(report)


def rank_heatmap(
    ranks,
    row_names,
    col_names,
    *,
    row_label: str = "tool",
    col_label: str = "column",
    title: str | None = None,
) -> Figure:
    """Labelled integer-rank heatmap, one rank per cell.

    A general rank grid: rows are tools, columns are whatever the rank is taken
    over (a weighting-by-aggregation configuration, or a dataset). See
    ``beam.reporting.figures.rank_heatmap`` for the arguments.
    """
    return _figures.rank_heatmap(
        ranks, row_names, col_names, row_label=row_label, col_label=col_label, title=title
    )


def score_heatmap(values, row_names, col_names, **kwargs) -> Figure:
    """Raw tool-by-column score heatmap, NaN-aware.

    Leaves missing cells grey, can colour on a log scale, and can outline the
    best cell per column (the ground-truth box). See
    ``beam.reporting.figures.score_heatmap`` for the arguments.
    """
    return _figures.score_heatmap(values, row_names, col_names, **kwargs)


def rank_bump(method_names, columns, ranks, **kwargs) -> Figure:
    """Bump (subway) chart of method ranks across columns.

    Each method is a line connecting its rank in each column, rank 1 at the top.
    See ``beam.reporting.figures.rank_bump`` for the arguments.
    """
    return _figures.rank_bump(method_names, columns, ranks, **kwargs)


def model_effects(report, *, xlabel: str | None = None, title: str | None = None) -> Figure:
    """Per-method effect estimates with error bars, largest first.

    Takes a mixed-effects or source-variance report and draws its
    ``method_effects`` with ``method_effect_se`` as error bars. The estimates are
    the marginal means over datasets (or benchmarks), so overlapping bars between
    neighbours read as methods the model cannot separate.
    """
    return _figures.effects_plot(
        report.method_names,
        report.method_effects,
        report.method_effect_se,
        xlabel=xlabel or "marginal mean over datasets",
        title=title,
    )


def variance_components(report, *, title: str | None = None) -> Figure:
    """Variance-component shares from a mixed-effects or source-variance report.

    Draws each entry of the report's ``variance_components`` as a share of the
    total, the residual or dispersion bar greyed.
    """
    return _figures.variance_shares_plot(report.variance_components, title=title)


def bradley_terry_leaves(report, *, title: str | None = None) -> Figure:
    """Datasets per Bradley-Terry tree leaf, each labelled by the method ranking
    first in that leaf.

    Takes a ``BradleyTerryTreeReport`` from ``beam.heterogeneity.bradley_terry_tree``.
    """
    return _figures.bradley_terry_leaves_plot(report, title=title)
