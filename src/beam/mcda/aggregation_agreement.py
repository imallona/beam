"""How much the recommendation depends on the choice of aggregation method.

beam offers five aggregations (SAW, TOPSIS, VIKOR, PROMETHEE II, COMET), each
resting on different assumptions about how per-metric scores combine into one
composite. The headline ranking uses one of them. This module checks
whether another aggregation would order the tools the same way. It re-ranks
the same normalized matrix under each aggregation, holding the weighting
fixed, and reports how closely the resulting orderings agree.

The agreement is measured with the Kendall tau-b rank-correlation coefficient,
which handles the tied ranks that competition ranking produces. A high mean
pairwise tau means the recommendation is stable under the aggregation choice; a
low one means the choice of method is itself a degree of freedom the report
should disclose. The consensus ranking averages the per-method ranks, and a flag marks
whether every aggregation puts the same tool first.

This sits alongside the other choice-sensitivity diagnostics: leave-one-metric-out
and leave-one-dataset-out vary the inputs, SMAA varies the weights, and this
varies the aggregation rule.
"""

from __future__ import annotations

import warnings as _warnings
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from scipy.stats import ConstantInputWarning, kendalltau

from .aggregate import rank
from .facade import _KNOWN_METHODS, run


@dataclass(frozen=True)
class AggregationAgreementReport:
    """Outcome of re-ranking one matrix under several aggregations.

    Fields:
        methods: the aggregation names that ran, in order. An aggregation that
            raises on the input (for example a degenerate matrix) is dropped.
        ranks_by_method: per-method 1-based ranks (1 is best), keyed by method
            name, each of length ``n_tools``.
        tau_matrix: (n_methods, n_methods) Kendall tau-b between every pair of
            methods' rankings, indexed by the order in ``methods``. The diagonal
            is 1. An entry is ``nan`` when one ranking is constant, so tau-b is
            undefined.
        mean_pairwise_tau: mean of the off-diagonal tau values, ignoring any
            ``nan``. A scalar summary of how much the orderings agree; 1 is exact
            agreement across every pair.
        consensus_ranks: (n_tools,) ranks from the mean rank across methods, 1 is
            best. Ties share the lowest rank.
        consensus_order: tool indices sorted from best to worst by the consensus.
        top_tool: the consensus rank-1 tool index.
        top_is_unanimous: True when every method ranks ``top_tool`` first.
        rank_low, rank_high: (n_tools,) best and worst rank each tool takes across
            the methods, the rank span behind the funky-heatmap consensus panel.
        tool_names: optional labels carried for reporting.
    """

    methods: tuple[str, ...]
    ranks_by_method: dict[str, np.ndarray]
    tau_matrix: np.ndarray
    mean_pairwise_tau: float
    consensus_ranks: np.ndarray
    consensus_order: np.ndarray
    top_tool: int
    top_is_unanimous: bool
    rank_low: np.ndarray
    rank_high: np.ndarray
    tool_names: tuple[str, ...] | None = None


def _pairwise_tau(rank_rows: list[np.ndarray]) -> tuple[np.ndarray, float]:
    """Kendall tau-b between every pair of rank vectors.

    Returns the symmetric tau matrix (diagonal 1) and the mean of the
    off-diagonal entries, ignoring pairs where tau-b is undefined because one
    ranking is constant.
    """
    n = len(rank_rows)
    tau = np.eye(n)
    off_diagonal = []
    with _warnings.catch_warnings():
        _warnings.simplefilter("ignore", ConstantInputWarning)
        for a in range(n):
            for b in range(a + 1, n):
                value = float(kendalltau(rank_rows[a], rank_rows[b]).statistic)
                tau[a, b] = tau[b, a] = value
                off_diagonal.append(value)
    finite = [v for v in off_diagonal if not np.isnan(v)]
    mean_tau = float(np.mean(finite)) if finite else float("nan")
    return tau, mean_tau


def aggregation_agreement(
    scores,
    polarity: Sequence[str],
    weights="equal",
    methods: Sequence[str] | None = None,
    normalization=None,
    bounds=None,
    baselines=None,
    targets=None,
    missing: str = "error",
    tool_names: Sequence[str] | None = None,
) -> AggregationAgreementReport:
    """Re-rank one matrix under several aggregations and measure their agreement.

    Normalization and weighting happen before aggregation and do not depend on
    the aggregation rule, so the weight vector is identical across the methods
    and the only thing that varies is how the normalized scores combine into a
    composite. For each method in ``methods`` the function runs the full
    pipeline through ``beam.mcda.run``, collects the per-tool ranks, and compares
    every pair of rankings with the Kendall tau-b coefficient.

    A method that raises on the input is dropped from the report rather than
    failing the whole analysis, matching how the funky-heatmap consensus panel
    already treats a method that cannot run. At least two methods must succeed.

    Parameters
    ----------
    scores
        Array-like of shape ``(n_tools, n_metrics)``.
    polarity
        Length ``n_metrics`` sequence of ``"higher_is_better"`` or
        ``"lower_is_better"``. Use ``beam.cards.polarities_for`` to source this
        from the registry.
    weights
        Forwarded to ``run``. A named scheme or an explicit array. Held fixed
        across the methods.
    methods
        Aggregation names to compare. Default is the five beam aggregations
        (SAW, TOPSIS, VIKOR, PROMETHEE II, COMET).
    normalization, bounds, baselines, targets
        Optional per-metric normalization context forwarded to every run. Pass
        the values from ``beam.mcda.registry_context`` so the comparison rests
        on the same normalized matrix as the headline ranking.
    missing
        Missing-data policy forwarded to every run. Default ``"error"``.
    tool_names
        Optional length ``n_tools`` labels carried in the report.

    Returns
    -------
    AggregationAgreementReport

    Raises
    ------
    ValueError
        If fewer than two of the requested methods produce a ranking.

    Examples
    --------
    >>> import numpy as np
    >>> from beam.mcda import aggregation_agreement
    >>> scores = np.array([[0.9, 30.0], [0.7, 50.0], [0.5, 40.0]])
    >>> report = aggregation_agreement(
    ...     scores, ["higher_is_better", "lower_is_better"]
    ... )
    >>> report.top_is_unanimous
    True
    """
    scores = np.asarray(scores, dtype=float)
    if scores.ndim != 2:
        raise ValueError(f"scores must be 2D; got shape {scores.shape}")
    polarity = list(polarity)
    if len(polarity) != scores.shape[1]:
        raise ValueError(
            f"polarity has {len(polarity)} entries but scores has {scores.shape[1]} columns"
        )
    method_names = list(_KNOWN_METHODS) if methods is None else list(methods)

    ran: list[str] = []
    rank_rows: list[np.ndarray] = []
    for method in method_names:
        try:
            result = run(
                scores,
                polarity,
                weights=weights,
                method=method,
                normalization=normalization,
                bounds=bounds,
                baselines=baselines,
                targets=targets,
                missing=missing,
            )
        except Exception:
            continue
        ran.append(method)
        rank_rows.append(result.ranks)

    if len(rank_rows) < 2:
        raise ValueError(
            f"aggregation_agreement needs at least two aggregations to compare; "
            f"only {len(rank_rows)} of {method_names} produced a ranking on this input"
        )

    stacked = np.vstack(rank_rows)
    tau_matrix, mean_tau = _pairwise_tau(rank_rows)

    mean_rank = stacked.mean(axis=0)
    consensus_ranks = rank(-mean_rank)
    consensus_order = np.argsort(consensus_ranks, kind="stable")
    top_tool = int(consensus_order[0])
    top_is_unanimous = all(int(row[top_tool]) == 1 for row in rank_rows)

    return AggregationAgreementReport(
        methods=tuple(ran),
        ranks_by_method={m: r for m, r in zip(ran, rank_rows, strict=True)},
        tau_matrix=tau_matrix,
        mean_pairwise_tau=mean_tau,
        consensus_ranks=consensus_ranks,
        consensus_order=consensus_order,
        top_tool=top_tool,
        top_is_unanimous=top_is_unanimous,
        rank_low=stacked.min(axis=0),
        rank_high=stacked.max(axis=0),
        tool_names=tuple(tool_names) if tool_names is not None else None,
    )
