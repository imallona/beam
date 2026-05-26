"""HTML report generation for a beam RunResult.

The package is named ``reporting`` so the public convenience ``beam.report``
can be a callable (a module and a function cannot share the name
``beam.report``). ``write_report`` is the full entry point; ``beam.report`` is
an alias for it. ``funky_heatmap`` and ``funky_heatmap_from_run`` draw the
glyph-table benchmarking plot with a rank-robustness panel.
"""

from __future__ import annotations

import numpy as np

from .figures import funky_heatmap
from .render import write_report

__all__ = ["funky_heatmap", "funky_heatmap_from_run", "write_report"]


_AGGREGATIONS = ("saw", "topsis", "vikor", "promethee_ii", "comet")


def _aggregation_consensus(run):
    """Rank span per tool across the five aggregations, holding the weighting fixed.

    Re-ranks the run's reduced matrix under each aggregation on the same
    card-derived normalization context, and returns the smallest and largest
    rank each tool takes. An aggregation that fails on the input is skipped.
    """
    from beam.mcda import run as mcda_run

    ctx = run.context
    rank_rows = []
    for method in _AGGREGATIONS:
        try:
            res = mcda_run(
                run.matrix,
                ctx.polarity,
                weights=run.result.weighting,
                method=method,
                normalization=list(ctx.normalization),
                bounds=list(ctx.bounds),
                baselines=list(ctx.baselines),
            )
        except Exception:
            continue
        rank_rows.append(res.ranks)
    if len(rank_rows) < 2:
        return None, None
    stacked = np.vstack(rank_rows)
    return stacked.min(axis=0), stacked.max(axis=0)


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
