"""How much the recommendation depends on the choice of normalization.

Before any weighting or aggregation, beam rescales each metric column to
[0, 1]. The strategy is chosen per metric from the card field
``comparability.recommended_normalization``, but it is a real analyst choice: a
rank normalization drops the size of the gaps between methods, ``log_min_max``
stops one slow method from compressing a runtime column, and ``zscore``
squashes outliers smoothly. A different strategy can change the order.

Like ``aggregation_agreement``, this module checks whether a different
normalization would order the tools the same way. It re-ranks the same
matrix under several normalizations, holding the weighting and the
aggregation fixed, and reports how closely the resulting orderings agree.

The agreement is measured with the Kendall tau-b rank-correlation coefficient,
which handles the tied ranks that competition ranking produces. A high mean
pairwise tau means the recommendation is stable under the normalization choice;
a low one means the choice is itself a degree of freedom the report should
disclose. The consensus ranking averages the per-method ranks, and a flag marks
whether every normalization puts the same tool first.

This sits alongside the other choice-sensitivity diagnostics: SMAA varies the
weights, ``aggregation_agreement`` varies the aggregation rule, and
``leave_one_dataset_out`` varies the data. ``normalization_agreement`` varies
the normalization, the one analyst choice the others leave untested.

Only the scale-agnostic strategies are compared by default (``min_max``,
``log_min_max``, ``rank``, ``zscore``). ``baseline_relative`` and
``target_relative`` are left out of the uniform sweep: they need a per-metric
reference or target from the card and are tied to the metric's meaning, so they
are not a free choice the analyst makes column by column. The card-recommended
per-metric normalization can still be passed in as one labelled candidate, so
the report compares the headline default against the uniform alternatives.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from .aggregate import rank
from .aggregation_agreement import _pairwise_tau
from .facade import run

_DEFAULT_STRATEGIES = ("min_max", "log_min_max", "rank", "zscore")


@dataclass(frozen=True)
class NormalizationAgreementReport:
    """Outcome of re-ranking one matrix under several normalizations.

    Fields:
        labels: the normalization labels that ran, in order. A normalization
            that raises on the input (for example ``log_min_max`` on a column
            with a non-positive value) is dropped.
        ranks_by_label: per-label 1-based ranks (1 is best), keyed by label,
            each of length ``n_tools``.
        tau_matrix: (n_labels, n_labels) Kendall tau-b between every pair of
            labels' rankings, indexed by the order in ``labels``. The diagonal
            is 1. An entry is ``nan`` when one ranking is constant, so tau-b is
            undefined.
        mean_pairwise_tau: mean of the off-diagonal tau values, ignoring any
            ``nan``. A scalar summary of how much the orderings agree; 1 is
            exact agreement across every pair.
        consensus_ranks: (n_tools,) ranks from the mean rank across labels, 1
            is best. Ties share the lowest rank.
        consensus_order: tool indices sorted from best to worst by the
            consensus.
        top_tool: the consensus rank-1 tool index.
        top_is_unanimous: True when every normalization ranks ``top_tool``
            first.
        rank_low, rank_high: (n_tools,) best and worst rank each tool takes
            across the labels.
        tool_names: optional labels carried for reporting.
    """

    labels: tuple[str, ...]
    ranks_by_label: dict[str, np.ndarray]
    tau_matrix: np.ndarray
    mean_pairwise_tau: float
    consensus_ranks: np.ndarray
    consensus_order: np.ndarray
    top_tool: int
    top_is_unanimous: bool
    rank_low: np.ndarray
    rank_high: np.ndarray
    tool_names: tuple[str, ...] | None = None


def normalization_agreement(
    scores,
    polarity: Sequence[str],
    weights="equal",
    method: str = "saw",
    strategies: Sequence[str] | None = None,
    recommended: Sequence[str] | None = None,
    bounds=None,
    baselines=None,
    targets=None,
    missing: str = "error",
    tool_names: Sequence[str] | None = None,
) -> NormalizationAgreementReport:
    """Re-rank one matrix under several normalizations and measure their agreement.

    Each candidate normalization is run through ``beam.mcda.run`` with the same
    weighting and aggregation, so the only thing that varies is how the raw
    scores are rescaled to [0, 1]. The function collects the per-tool ranks and
    compares every pair of rankings with the Kendall tau-b coefficient.

    Objective weights (entropy, std, critic, merec) are computed from the
    normalized matrix, so a change of normalization also changes those weights.
    That is intended: the normalization choice propagates through the whole
    pipeline, and the report shows its total effect on the order.

    A candidate that raises on the input is dropped from the report rather than
    failing the whole analysis, matching how ``aggregation_agreement`` treats an
    aggregation that cannot run. At least two candidates must succeed.

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
        across the candidates.
    method
        Aggregation rule, forwarded to ``run``. Held fixed across the
        candidates. Default ``"saw"``.
    strategies
        Normalization strategy names to compare, each applied to every metric
        column. Default the four scale-agnostic strategies (``min_max``,
        ``log_min_max``, ``rank``, ``zscore``).
    recommended
        Optional per-metric normalization, one strategy per column, added as a
        candidate labelled ``"recommended"``. Pass ``RegistryContext.normalization``
        so the report compares the card-recommended default against the uniform
        alternatives.
    bounds, baselines, targets
        Optional per-metric normalization context forwarded to every run. The
        bounds feed ``min_max``; ``baselines`` and ``targets`` are only used by
        a ``recommended`` config that names ``baseline_relative`` or
        ``target_relative``.
    missing
        Missing-data policy forwarded to every run. Default ``"error"``.
    tool_names
        Optional length ``n_tools`` labels carried in the report.

    Returns
    -------
    NormalizationAgreementReport

    Raises
    ------
    ValueError
        If fewer than two of the candidate normalizations produce a ranking.

    Examples
    --------
    >>> import numpy as np
    >>> from beam.mcda import normalization_agreement
    >>> scores = np.array([[0.9, 30.0], [0.7, 50.0], [0.5, 40.0]])
    >>> report = normalization_agreement(
    ...     scores, ["higher_is_better", "lower_is_better"]
    ... )
    >>> report.top_is_unanimous
    True
    """
    scores = np.asarray(scores, dtype=float)
    if scores.ndim != 2:
        raise ValueError(f"scores must be 2D; got shape {scores.shape}")
    polarity = list(polarity)
    n_metrics = scores.shape[1]
    if len(polarity) != n_metrics:
        raise ValueError(f"polarity has {len(polarity)} entries but scores has {n_metrics} columns")

    candidates: list[tuple[str, list[str]]] = []
    names = list(_DEFAULT_STRATEGIES if strategies is None else strategies)
    for name in names:
        candidates.append((name, [name] * n_metrics))
    if recommended is not None:
        recommended = list(recommended)
        if len(recommended) != n_metrics:
            raise ValueError(
                f"recommended has {len(recommended)} entries but scores has {n_metrics} columns"
            )
        candidates.insert(0, ("recommended", recommended))

    ran: list[str] = []
    rank_rows: list[np.ndarray] = []
    for label, strategy in candidates:
        try:
            result = run(
                scores,
                polarity,
                weights=weights,
                method=method,
                normalization=strategy,
                bounds=bounds,
                baselines=baselines,
                targets=targets,
                missing=missing,
            )
        except Exception:
            continue
        ran.append(label)
        rank_rows.append(result.ranks)

    if len(rank_rows) < 2:
        raise ValueError(
            "normalization_agreement needs at least two normalizations to compare; "
            f"only {len(rank_rows)} of {[label for label, _ in candidates]} produced "
            "a ranking on this input"
        )

    stacked = np.vstack(rank_rows)
    tau_matrix, mean_tau = _pairwise_tau(rank_rows)

    mean_rank = stacked.mean(axis=0)
    consensus_ranks = rank(-mean_rank)
    consensus_order = np.argsort(consensus_ranks, kind="stable")
    top_tool = int(consensus_order[0])
    top_is_unanimous = all(int(row[top_tool]) == 1 for row in rank_rows)

    return NormalizationAgreementReport(
        labels=tuple(ran),
        ranks_by_label={label: r for label, r in zip(ran, rank_rows, strict=True)},
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
