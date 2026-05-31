"""HTML report generation for a beam RunResult.

The package is named ``reporting`` so the public convenience ``beam.report``
can be a callable (a module and a function cannot share the name
``beam.report``). ``write_report`` is the full entry point; ``beam.report`` is
an alias for it. ``funky_heatmap`` and ``funky_heatmap_from_run`` draw the
glyph-table benchmarking plot with a rank-robustness panel.
"""

from __future__ import annotations

import numpy as np

from .figures import funky_heatmap, rank_bump
from .render import write_report

__all__ = ["funky_heatmap", "funky_heatmap_from_run", "rank_bump", "write_report"]


def _aggregation_agreement_report(run):
    """Re-rank the run's reduced matrix under the five aggregations.

    Holds the run's card-derived normalization context and weighting fixed and
    varies the aggregation rule, returning an ``AggregationAgreementReport`` or
    ``None`` when fewer than two aggregations produce a ranking on this input.
    """
    from beam.mcda import aggregation_agreement

    ctx = run.context
    try:
        return aggregation_agreement(
            run.matrix,
            ctx.polarity,
            weights=run.result.weighting,
            normalization=list(ctx.normalization),
            bounds=list(ctx.bounds),
            baselines=list(ctx.baselines),
            targets=list(ctx.targets),
            tool_names=run.tool_names,
        )
    except ValueError:
        return None


def _aggregation_consensus(run):
    """Rank span per tool across the five aggregations, holding the weighting fixed.

    Returns the smallest and largest rank each tool takes, the span behind the
    funky-heatmap consensus panel. ``(None, None)`` when fewer than two
    aggregations run on the input.
    """
    report = _aggregation_agreement_report(run)
    if report is None:
        return None, None
    return report.rank_low, report.rank_high


def funky_heatmap_from_run(
    run,
    metric_groups=None,
    title=None,
    *,
    worth=None,
    worth_ci=None,
    worth_label="model worth",
    cliques=None,
    show_smaa=True,
    show_aggregation_consensus=True,
):
    """Build a funky heatmap from a ``beam.rank`` RunResult.

    Derives the robustness panels from the run: the leave-one-dataset-out rank
    span from the leave-one-dataset-out report, the SMAA rank-acceptability bar
    from the SMAA report, and the aggregation-consensus rank span by re-ranking
    the run's matrix under the five aggregations. The model worth with intervals
    and the Friedman-Nemenyi cliques are passed in by the caller, since the
    worth comes from the R-backed heterogeneity models.

    Parameters
    ----------
    run
        A ``beam.api.RunResult``.
    metric_groups
        Optional group label per metric, in the order of ``run.metric_ids``.
    title
        Optional figure title.
    worth, worth_ci, worth_label
        Optional model worth, its half-interval, and the panel label.
    cliques
        Optional groups of method names not separable by Friedman-Nemenyi.
    show_smaa
        Draw the SMAA rank-acceptability panel when the run carries SMAA.
    show_aggregation_consensus
        Draw the aggregation rank-span panel.

    Returns
    -------
    matplotlib.figure.Figure
    """
    result = run.result
    rank_low = rank_high = None
    lodo = run.leave_one_dataset_out
    if lodo is not None:
        stacked = np.vstack([lodo.base.ranks] + [r.ranks for r in lodo.leave_one_out.values()])
        rank_low = stacked.min(axis=0)
        rank_high = stacked.max(axis=0)

    consensus_low = consensus_high = None
    if show_aggregation_consensus:
        consensus_low, consensus_high = _aggregation_consensus(run)

    smaa_acceptability = (
        run.smaa.rank_acceptability_index if (show_smaa and run.smaa is not None) else None
    )

    return funky_heatmap(
        result.normalized,
        run.tool_names,
        run.metric_ids,
        result.composite,
        result.ranks,
        metric_groups=tuple(metric_groups) if metric_groups is not None else None,
        rank_low=rank_low,
        rank_high=rank_high,
        cliques=cliques,
        worth=worth,
        worth_ci=worth_ci,
        worth_label=worth_label,
        consensus_low=consensus_low,
        consensus_high=consensus_high,
        smaa_acceptability=smaa_acceptability,
        title=title,
    )
