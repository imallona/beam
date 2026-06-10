"""List every ranking the analyst's choices produce, and report how stable it is.

``rank_sensitivity`` runs the full factorial of the weighting scheme, the
aggregation rule and (for a tensor) the dataset, and splits the rank variance
into a share per factor. That answers which choice moves the ranking. It does
not list the rankings themselves.

``specification_curve`` does. It reads the per-combination ranks that
``rank_sensitivity`` already computed and turns them into one record per
combination: the factor levels that define it, the full tool ordering it
produces, and the tool it ranks first. From those records it reports how stable
the top method is: the fraction of combinations that rank the same tool first,
the fraction that produce the single most common ordering, and how many distinct
tools rank first in at least one combination.

This is the specification-curve form used in meta-research (Simonsohn, Simmons
and Nelson 2020; Steegen, Tuerlinckx, Gelman and Vanpaemel 2016): report the
ranking under every combination of choices rather than one, so the reader can
see how much it varies.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from .rank_sensitivity import RankSensitivityReport


@dataclass(frozen=True)
class Specification:
    """One combination of analyst choices and the ranking it produces.

    Attributes
    ----------
    index
        Position of this combination in the factorial, in row-major order over
        the weighting, aggregation and (for a tensor) dataset axes.
    weighting
        The weighting scheme of this combination.
    aggregation
        The aggregation rule of this combination.
    dataset
        The dataset of this combination for a tensor input, or ``None`` for a
        matrix.
    ranks
        The competition rank of every tool under this combination, indexed by
        tool. Rank 1 is best. Ties share the lower rank.
    ordering
        Tool indices sorted from best to worst rank, ties broken by tool index.
    top_tool
        The tool index ranked first. On a tie the lowest tool index is taken.
    """

    index: int
    weighting: str
    aggregation: str
    dataset: str | None
    ranks: tuple[int, ...]
    ordering: tuple[int, ...]
    top_tool: int


@dataclass(frozen=True)
class SpecificationCurveReport:
    """Every ranking the factorial produces, with stability summaries.

    Attributes
    ----------
    factors
        The factor names that vary, in axis order: ``("weighting",
        "aggregation")`` for a matrix, with ``"dataset"`` appended for a tensor.
    weightings, methods
        The weighting schemes and aggregations that formed the factorial.
    dataset_names
        The datasets that formed the third factor, or ``None`` for a matrix.
    tool_names
        Tool labels in index order, or ``None`` when the input carried none.
    n_specifications
        The number of combinations in the factorial.
    specifications
        One ``Specification`` per combination, in factorial order.
    curve_order
        Indices into ``specifications`` sorted for plotting: by the rank that the
        method ranking first most often takes, then by combination index. A
        specification curve reads left to right along this order.
    most_frequent_top_tool
        The tool index that ranks first in the most combinations.
    most_frequent_top_fraction
        The fraction of combinations that rank ``most_frequent_top_tool`` first.
    distinct_top_tools
        The tool indices that rank first in at least one combination, sorted.
    n_distinct_top_tools
        The length of ``distinct_top_tools``: how many tools rank first in at
        least one combination.
    modal_order
        The single most common full tool ordering across the combinations.
    modal_order_fraction
        The fraction of combinations that produce ``modal_order``.
    """

    factors: tuple[str, ...]
    weightings: tuple[str, ...]
    methods: tuple[str, ...]
    dataset_names: tuple[str, ...] | None
    tool_names: tuple[str, ...] | None
    n_specifications: int
    specifications: tuple[Specification, ...]
    curve_order: tuple[int, ...]
    most_frequent_top_tool: int
    most_frequent_top_fraction: float
    distinct_top_tools: tuple[int, ...]
    n_distinct_top_tools: int
    modal_order: tuple[int, ...]
    modal_order_fraction: float


def specification_curve(report: RankSensitivityReport) -> SpecificationCurveReport:
    """Build the specification curve from a ``rank_sensitivity`` report.

    Reads the per-combination ranks in ``report.ranks`` and produces one
    ``Specification`` per combination, then the stability summaries. Does no new
    ranking: it post-processes the factorial ``rank_sensitivity`` already ran, so
    it works the same for a matrix and a tensor input.

    Parameters
    ----------
    report
        A ``RankSensitivityReport`` from ``beam.mcda.rank_sensitivity``.

    Returns
    -------
    SpecificationCurveReport

    Examples
    --------
    >>> import numpy as np
    >>> from beam.mcda import rank_sensitivity, specification_curve
    >>> scores = np.array([[0.9, 30.0], [0.7, 50.0], [0.5, 40.0], [0.3, 70.0]])
    >>> rs = rank_sensitivity(scores, ["higher_is_better", "lower_is_better"])
    >>> sc = specification_curve(rs)
    >>> sc.n_specifications == len(rs.weightings) * len(rs.methods)
    True
    >>> 0.0 <= sc.most_frequent_top_fraction <= 1.0
    True
    """
    ranks = report.ranks
    factor_shape = ranks.shape[1:]
    is_tensor = len(report.factors) == 3

    specs: list[Specification] = []
    for index, idx in enumerate(np.ndindex(*factor_shape)):
        rank_vec = ranks[(slice(None), *idx)].astype(int)
        ordering = tuple(int(t) for t in np.argsort(rank_vec, kind="stable"))
        top_tool = int(np.flatnonzero(rank_vec == rank_vec.min())[0])
        specs.append(
            Specification(
                index=index,
                weighting=report.weightings[idx[0]],
                aggregation=report.methods[idx[1]],
                dataset=report.dataset_names[idx[2]] if is_tensor else None,
                ranks=tuple(int(r) for r in rank_vec),
                ordering=ordering,
                top_tool=top_tool,
            )
        )

    n = len(specs)
    most_frequent_top_tool, most_frequent_top_fraction = _modal_value(
        [s.top_tool for s in specs], n
    )
    distinct_top_tools = tuple(sorted({s.top_tool for s in specs}))
    modal_order, modal_order_fraction = _modal_value([s.ordering for s in specs], n)

    curve_order = tuple(sorted(range(n), key=lambda i: (specs[i].ranks[most_frequent_top_tool], i)))

    return SpecificationCurveReport(
        factors=report.factors,
        weightings=report.weightings,
        methods=report.methods,
        dataset_names=report.dataset_names,
        tool_names=report.tool_names,
        n_specifications=n,
        specifications=tuple(specs),
        curve_order=curve_order,
        most_frequent_top_tool=most_frequent_top_tool,
        most_frequent_top_fraction=most_frequent_top_fraction,
        distinct_top_tools=distinct_top_tools,
        n_distinct_top_tools=len(distinct_top_tools),
        modal_order=modal_order,
        modal_order_fraction=modal_order_fraction,
    )


def _modal_value(values: Sequence, n: int):
    """Return the most common value and its fraction of ``n``.

    Ties are broken by first appearance, so the result is deterministic.
    """
    counts: dict = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    best = max(counts, key=lambda k: counts[k])
    return best, counts[best] / n
