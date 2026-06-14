"""Agreement between datasets on how they order the methods.

A pooled ranking summarizes the methods over every dataset at once. It cannot
show whether the datasets agree on that order or pull in different directions.
This module measures the agreement directly. It ranks the methods within each
dataset under the same MCDA pipeline as the headline run, then compares every
pair of per-dataset orderings with the Kendall tau-b rank correlation.

The output is a dataset by dataset agreement matrix, a single mean-agreement
summary, the dataset whose ordering matches the others least, and a grouping of
datasets whose orderings are mutually consistent above a threshold. A high mean
says the pooled recommendation stands in for the individual datasets. A low one
says it does not, and a single pooled number then hides heterogeneity the reader
should see.

The companion view is the rank-deviation table. For each method it records the
datasets where the method places higher or lower than its own typical rank.
These cells are where the dataset disagreement comes from. They name the
method-by-dataset combinations that move the ordering, with no claim about which
method is preferable overall.

The diagnostic needs no replicates and assumes no exchangeability among the
datasets. It treats each observed dataset as fixed and reports the structure of
agreement among them. It is the data-driven companion to the Bradley-Terry
tree, which splits the datasets by declared features rather than by their
rankings.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from .aggregation_agreement import _pairwise_tau
from .facade import run


@dataclass(frozen=True)
class RankDeviation:
    """One method-by-dataset cell where a method departs from its typical rank.

    Fields:
        tool: index into the tool axis.
        dataset: original index into the dataset axis (not the evaluated-only
            position).
        rank: the method's 1-based rank on that dataset, 1 is the highest place.
        mean_rank: the method's mean rank across the evaluated datasets.
        deviation: ``rank`` minus ``mean_rank``. A negative value means the
            method places higher than its average on that dataset; a positive
            value means it places lower.
    """

    tool: int
    dataset: int
    rank: int
    mean_rank: float
    deviation: float


@dataclass(frozen=True)
class DatasetConcordanceReport:
    """Outcome of comparing the per-dataset method orderings.

    Rows and columns of ``tau_matrix`` and ``ranks_by_dataset``, and the entries
    of ``per_dataset_mean_tau``, follow ``evaluated_datasets``. The dataset
    indices in ``most_idiosyncratic_dataset``, ``concordant_groups`` and the
    ``RankDeviation`` records are original dataset indices.

    Fields:
        evaluated_datasets: original indices of the datasets that produced a
            ranking, in order. A dataset whose single-dataset matrix the pipeline
            cannot rank (for example a missing cell under the ``"error"`` policy)
            is dropped and absent here.
        ranks_by_dataset: (n_evaluated, n_tools) per-dataset 1-based ranks.
        tau_matrix: (n_evaluated, n_evaluated) Kendall tau-b between every pair
            of per-dataset orderings. The diagonal is 1. An entry is ``nan`` when
            one ordering is constant, so tau-b is undefined.
        mean_pairwise_tau: mean of the off-diagonal tau values, ignoring ``nan``.
            A scalar summary of how much the datasets agree; 1 is exact agreement.
        per_dataset_mean_tau: (n_evaluated,) each dataset's mean agreement with
            the others, ignoring ``nan``.
        most_idiosyncratic_dataset: original index of the dataset with the lowest
            mean agreement with the rest.
        concordant_groups: groups of datasets whose pairwise agreement is at or
            above ``threshold``, as connected components of that relation. Each
            group is a tuple of original dataset indices; a dataset agreeing with
            no other forms its own singleton group.
        mean_rank_by_tool: (n_tools,) each method's mean rank across the
            evaluated datasets.
        rank_deviation: (n_tools, n_evaluated) each method's per-dataset rank
            minus its mean rank, the signed table behind ``notable_cells``.
        notable_cells: the method-by-dataset cells at least one full rank from the
            method's mean rank, sorted by the size of the deviation, capped at a
            small number for reporting.
        threshold: the agreement cutoff used to form ``concordant_groups``.
        dataset_names: optional length n_datasets labels, indexed by original
            dataset index.
        tool_names: optional length n_tools labels.
    """

    evaluated_datasets: tuple[int, ...]
    ranks_by_dataset: np.ndarray
    tau_matrix: np.ndarray
    mean_pairwise_tau: float
    per_dataset_mean_tau: np.ndarray
    most_idiosyncratic_dataset: int
    concordant_groups: tuple[tuple[int, ...], ...]
    mean_rank_by_tool: np.ndarray
    rank_deviation: np.ndarray
    notable_cells: tuple[RankDeviation, ...]
    threshold: float
    dataset_names: tuple[str, ...] | None = None
    tool_names: tuple[str, ...] | None = None


def _connected_groups(tau_matrix: np.ndarray, threshold: float) -> list[tuple[int, ...]]:
    """Connected components of the at-or-above-threshold agreement relation.

    Two datasets are joined when their tau-b is finite and at least
    ``threshold``. Returns the components as sorted index tuples, ordered by
    their first member.
    """
    n = tau_matrix.shape[0]
    adjacency: list[list[int]] = [[] for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            value = tau_matrix[i, j]
            if not np.isnan(value) and value >= threshold:
                adjacency[i].append(j)
                adjacency[j].append(i)
    seen = [False] * n
    groups: list[tuple[int, ...]] = []
    for start in range(n):
        if seen[start]:
            continue
        stack = [start]
        seen[start] = True
        component: list[int] = []
        while stack:
            node = stack.pop()
            component.append(node)
            for neighbour in adjacency[node]:
                if not seen[neighbour]:
                    seen[neighbour] = True
                    stack.append(neighbour)
        groups.append(tuple(sorted(component)))
    groups.sort(key=lambda g: g[0])
    return groups


def dataset_concordance(
    tensor,
    polarity: Sequence[str],
    weights="equal",
    method: str = "saw",
    dataset_names: Sequence[str] | None = None,
    tool_names: Sequence[str] | None = None,
    metric_ids: Sequence[str] | None = None,
    normalization=None,
    bounds=None,
    baselines=None,
    targets=None,
    missing: str = "error",
    threshold: float = 0.5,
) -> DatasetConcordanceReport:
    """Rank the methods within each dataset and measure how the orderings agree.

    For each dataset the function ranks the methods on that dataset's tool by
    metric matrix through ``beam.mcda.run``, holding the weighting, aggregation
    and normalization context fixed. It then compares every pair of per-dataset
    orderings with the Kendall tau-b coefficient, which handles the ties that
    competition ranking produces.

    A dataset whose single-dataset matrix the pipeline cannot rank is dropped
    rather than failing the whole analysis, matching how the aggregation and
    normalization agreement reports drop a configuration that cannot run. At
    least two datasets must produce a ranking.

    Parameters
    ----------
    tensor
        Array-like of shape ``(n_tools, n_datasets, n_metrics)``.
    polarity
        Length ``n_metrics`` sequence of ``"higher_is_better"`` or
        ``"lower_is_better"``. Use ``beam.cards.polarities_for`` to source this
        from the registry.
    weights
        Forwarded to ``run``. A named scheme or an explicit array. Objective
        schemes are recomputed within each dataset.
    method
        Aggregation name forwarded to ``run``. Default ``"saw"``.
    dataset_names, tool_names
        Optional labels carried in the report.
    metric_ids
        Optional length ``n_metrics`` labels used in error messages.
    normalization, bounds, baselines, targets
        Optional per-metric normalization context forwarded to every run. Pass
        the values from ``beam.mcda.registry_context`` so the per-dataset
        rankings normalize the same way as the headline ranking.
    missing
        Missing-data policy forwarded to every run. Default ``"error"``, which
        drops any dataset with a missing cell.
    threshold
        Agreement cutoff for ``concordant_groups``. Default 0.5, a moderate
        tau-b. Two datasets join the same group when their tau-b is at least
        this value.

    Returns
    -------
    DatasetConcordanceReport

    Raises
    ------
    ValueError
        If the input is not 3D, has fewer than two datasets, or fewer than two
        datasets produce a ranking.

    Examples
    --------
    >>> import numpy as np
    >>> from beam.mcda import dataset_concordance
    >>> tensor = np.array(
    ...     [
    ...         [[0.9], [0.8], [0.1]],
    ...         [[0.5], [0.4], [0.5]],
    ...         [[0.1], [0.2], [0.9]],
    ...     ]
    ... )
    >>> report = dataset_concordance(tensor, ["higher_is_better"])
    >>> report.most_idiosyncratic_dataset
    2
    """
    tensor = np.asarray(tensor, dtype=float)
    if tensor.ndim != 3:
        raise ValueError(f"tensor must be 3D; got shape {tensor.shape}")
    n_tools, n_datasets, n_metrics = tensor.shape
    if n_datasets < 2:
        raise ValueError(f"dataset_concordance needs at least 2 datasets; got {n_datasets}")
    if len(polarity) != n_metrics:
        raise ValueError(f"polarity has {len(polarity)} entries but tensor has {n_metrics} metrics")

    evaluated: list[int] = []
    rank_rows: list[np.ndarray] = []
    for d in range(n_datasets):
        try:
            result = run(
                tensor[:, d, :],
                list(polarity),
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
        evaluated.append(d)
        rank_rows.append(result.ranks)

    if len(rank_rows) < 2:
        raise ValueError(
            f"dataset_concordance needs at least two datasets that produce a ranking; "
            f"only {len(rank_rows)} of {n_datasets} did under method {method!r}"
        )

    stacked = np.vstack(rank_rows)
    n_eval = len(rank_rows)
    tau_matrix, mean_tau = _pairwise_tau(rank_rows)

    per_dataset = np.full(n_eval, np.nan)
    for i in range(n_eval):
        off = [tau_matrix[i, j] for j in range(n_eval) if j != i and not np.isnan(tau_matrix[i, j])]
        if off:
            per_dataset[i] = float(np.mean(off))
    idiosyncratic_pos = 0 if np.all(np.isnan(per_dataset)) else int(np.nanargmin(per_dataset))
    most_idiosyncratic = evaluated[idiosyncratic_pos]

    groups = _connected_groups(tau_matrix, threshold)
    concordant_groups = tuple(tuple(evaluated[pos] for pos in group) for group in groups)

    mean_rank_by_tool = stacked.mean(axis=0)
    rank_deviation = stacked.T - mean_rank_by_tool[:, None]

    notable: list[RankDeviation] = []
    for tool in range(n_tools):
        for pos in range(n_eval):
            deviation = float(rank_deviation[tool, pos])
            if abs(deviation) >= 1.0:
                notable.append(
                    RankDeviation(
                        tool=tool,
                        dataset=evaluated[pos],
                        rank=int(stacked[pos, tool]),
                        mean_rank=float(mean_rank_by_tool[tool]),
                        deviation=deviation,
                    )
                )
    notable.sort(key=lambda cell: abs(cell.deviation), reverse=True)

    return DatasetConcordanceReport(
        evaluated_datasets=tuple(evaluated),
        ranks_by_dataset=stacked,
        tau_matrix=tau_matrix,
        mean_pairwise_tau=mean_tau,
        per_dataset_mean_tau=per_dataset,
        most_idiosyncratic_dataset=most_idiosyncratic,
        concordant_groups=concordant_groups,
        mean_rank_by_tool=mean_rank_by_tool,
        rank_deviation=rank_deviation,
        notable_cells=tuple(notable[:12]),
        threshold=float(threshold),
        dataset_names=tuple(dataset_names) if dataset_names is not None else None,
        tool_names=tuple(tool_names) if tool_names is not None else None,
    )
