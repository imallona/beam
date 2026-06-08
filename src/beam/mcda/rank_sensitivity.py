"""Split a ranking's variance between the analyst's choices and the data.

A ranking can move for two reasons. One is the analyst's choices: which weighting
scheme sets the weights, and which aggregation rule combines the scores. The other
is the data: a method that ranks first on one dataset can trail on another. A
benchmarker should know which reason is at work. The other tools each vary one
thing. ``aggregation_agreement`` varies the aggregation. ``smaa`` varies the
weights. ``leave_one_dataset_out`` drops a dataset. None of them measure the
choices and the data on the same scale.

``rank_sensitivity`` does. The weighting, the aggregation, and the dataset are
each a small set of options, so beam computes every combination rather than
sampling. For each tool this gives a table of its rank over the full factorial. An
analysis of variance then splits the rank variance into a share for each factor
plus a share for their interactions. The shares sum to one. For a deterministic
function of categorical factors over a balanced factorial, these main-effect
shares are the first-order variance indices (the categorical form of the Sobol
indices), and they are exact here because nothing is sampled.

The headline is the share each factor carries, pooled over the tools. A large
dataset share means the ranking depends on which dataset you use. A large
weighting or aggregation share means it depends on a choice the analyst could make
differently. Either way, the report says so instead of hiding it.

A 2D tool-by-metric matrix has two factors: the weighting and the aggregation. A
3D tool-by-dataset-by-metric tensor adds the dataset as a third factor, so the
data question and the choice questions are answered in one decomposition.
"""

from __future__ import annotations

import warnings as _warnings
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from .facade import _KNOWN_METHODS, run

# MEREC is left out of the default weightings: it takes the logarithm of the
# normalized scores and refuses a zero, but the default min_max normalization maps
# each column minimum to exactly zero, so MEREC cannot run on a standard pipeline.
# Pass it explicitly with a normalization that keeps the scores strictly positive.
_DEFAULT_WEIGHTINGS = ("equal", "entropy", "std", "critic")


@dataclass(frozen=True)
class ToolRankSensitivity:
    """The rank-sensitivity profile of one tool.

    Attributes
    ----------
    tool
        Tool index into the score matrix.
    name
        Tool label, or ``None`` when the matrix carried none.
    factor_shares
        The fraction of this tool's rank variance over the factorial explained by
        each factor's main effect, keyed by factor name. With the
        ``interaction_share`` the values sum to one. All ``nan`` when the tool
        holds the same rank in every combination.
    interaction_share
        The fraction of this tool's rank variance carried by every factor
        interaction together, ``nan`` when the tool has no rank variance.
    rank_min, rank_max, rank_span
        The best, worst, and spread of this tool's rank across the factorial.
    modal_rank
        The rank this tool takes most often across the factorial.
    """

    tool: int
    name: str | None
    factor_shares: dict[str, float]
    interaction_share: float
    rank_min: int
    rank_max: int
    rank_span: int
    modal_rank: int


@dataclass(frozen=True)
class RankSensitivityReport:
    """Variance attribution of a ranking to the choices and the data.

    Attributes
    ----------
    factors
        The factor names in the order of the ``ranks`` axes after the tool axis:
        ``("weighting", "aggregation")`` for a matrix, with ``"dataset"`` appended
        for a tensor.
    weightings, methods
        The weighting schemes and aggregations that formed the factorial, after
        any pruning, in axis order.
    dataset_names
        The datasets that formed the third factor, or ``None`` for a 2D input.
    dropped_weightings, dropped_methods, dropped_datasets
        Factor levels dropped because they failed on this input, so the surviving
        grid stays balanced. Empty in the common case.
    n_combinations
        The size of the surviving factorial.
    ranks
        Integer competition ranks (1 is best). Shape ``(n_tools, n_weightings,
        n_methods)`` for a matrix, ``(n_tools, n_weightings, n_methods,
        n_datasets)`` for a tensor.
    tool_names
        Tool labels in index order, or ``None``.
    factor_shares
        The pooled main-effect variance share per factor over all tools. With
        ``interaction_share`` the values sum to one.
    interaction_share
        The pooled variance share carried by all factor interactions together.
    most_influential_factor
        The factor or ``"interaction"`` whose pooled share is largest.
    per_tool
        The per-tool profiles, in tool-index order.
    headline_tool
        The tool ranked first in the most combinations.
    headline_top_fraction
        The fraction of combinations in which ``headline_tool`` ranks first.
    headline_rank_span
        The rank span of ``headline_tool`` across the factorial.
    headline_rank_by_dataset
        For a tensor input, the mean rank of ``headline_tool`` on each dataset,
        averaged over the choices, in ``dataset_names`` order. ``None`` for a
        matrix. A row that climbs from 1 shows where the headline tool slips.
    """

    factors: tuple[str, ...]
    weightings: tuple[str, ...]
    methods: tuple[str, ...]
    dataset_names: tuple[str, ...] | None
    dropped_weightings: tuple[str, ...]
    dropped_methods: tuple[str, ...]
    dropped_datasets: tuple[str, ...]
    n_combinations: int
    ranks: np.ndarray
    tool_names: tuple[str, ...] | None
    factor_shares: dict[str, float]
    interaction_share: float
    most_influential_factor: str
    per_tool: tuple[ToolRankSensitivity, ...]
    headline_tool: int
    headline_top_fraction: float
    headline_rank_span: int
    headline_rank_by_dataset: np.ndarray | None

    @property
    def weighting_share(self) -> float:
        """Pooled main-effect share of the weighting choice."""
        return self.factor_shares["weighting"]

    @property
    def aggregation_share(self) -> float:
        """Pooled main-effect share of the aggregation choice."""
        return self.factor_shares["aggregation"]

    @property
    def dataset_share(self) -> float | None:
        """Pooled main-effect share of the dataset, or ``None`` for a matrix."""
        return self.factor_shares.get("dataset")


def _variance_shares(table: np.ndarray) -> tuple[float, list[float], float]:
    """Decompose a balanced full-factorial table into main-effect sums of squares.

    ``table`` has one value per factor combination, one axis per factor. Returns
    the total sum of squares, the main-effect sum of squares per axis, and the
    interaction sum of squares (everything the main effects do not explain). The
    design is deterministic and balanced, so the decomposition is exact and the
    interaction term needs no replication.
    """
    grand = float(table.mean())
    ss_total = float(((table - grand) ** 2).sum())
    n_cells = table.size
    ss_main: list[float] = []
    for axis in range(table.ndim):
        other = tuple(i for i in range(table.ndim) if i != axis)
        level_means = table.mean(axis=other)
        ss = (n_cells / table.shape[axis]) * float(((level_means - grand) ** 2).sum())
        ss_main.append(ss)
    ss_interaction = ss_total - sum(ss_main)
    return ss_total, ss_main, ss_interaction


def _prune_to_complete_grid(success: np.ndarray) -> list[list[int]]:
    """Drop whole factor levels until every surviving combination succeeded.

    ``success`` is a boolean grid with one axis per factor. A balanced
    decomposition needs a complete box, so a level that failed on any combination
    is removed. Each step drops the single level (on any axis) with the most
    failures in the current box, which clears the most failures per level removed,
    until the kept box is all success or an axis empties.
    """
    kept = [list(range(n)) for n in success.shape]
    while all(kept):
        sub = success[np.ix_(*kept)]
        if sub.all():
            break
        best_axis = best_pos = -1
        best_fail = -1
        for axis in range(sub.ndim):
            other = tuple(i for i in range(sub.ndim) if i != axis)
            fails = (~sub).sum(axis=other)
            pos = int(np.argmax(fails))
            if int(fails[pos]) > best_fail:
                best_fail = int(fails[pos])
                best_axis, best_pos = axis, pos
        kept[best_axis].pop(best_pos)
    return kept


def rank_sensitivity(
    scores,
    polarity: Sequence[str],
    weightings: Sequence[str] | None = None,
    methods: Sequence[str] | None = None,
    normalization=None,
    bounds=None,
    baselines=None,
    targets=None,
    missing: str = "error",
    tool_names: Sequence[str] | None = None,
    dataset_names: Sequence[str] | None = None,
) -> RankSensitivityReport:
    """Decompose a ranking's variance over the weighting, aggregation and dataset.

    Runs the full factorial of the factors, collecting the rank of every tool
    under each combination, and decomposes each tool's rank variance into a
    main-effect share per factor plus the interaction share by an analysis of
    variance. Pooling the variance over the tools gives the overall share each
    factor carries.

    With a 2D ``(n_tools, n_metrics)`` matrix the factors are the weighting and the
    aggregation. With a 3D ``(n_tools, n_datasets, n_metrics)`` tensor the dataset
    joins them: each combination ranks the tools on one dataset's slice, so the
    dataset share reads how much the ranking depends on which dataset you evaluate
    on. Each combination must rank: the distance and outranking aggregations
    refuse a slice with missing cells, so for partial coverage pass
    ``missing="worst"`` to complete the matrix or restrict to the feasible subset.

    Parameters
    ----------
    scores
        Array-like of shape ``(n_tools, n_metrics)`` or ``(n_tools, n_datasets,
        n_metrics)``.
    polarity
        Length ``n_metrics`` sequence of ``"higher_is_better"`` or
        ``"lower_is_better"``. Use ``beam.cards.polarities_for`` to source it from
        the registry.
    weightings
        Weighting schemes to vary. Default is ``("equal", "entropy", "std",
        "critic")``. MEREC is left out of the default because it takes the
        logarithm of the scores and refuses the zeros the default min_max
        normalization produces; pass it explicitly with a positivity-preserving
        normalization. AHP is excluded because it needs an analyst-supplied
        pairwise matrix, not a data-driven rule.
    methods
        Aggregations to vary, from the five beam aggregations. Default is all five.
        COMET builds characteristic objects whose count grows fast with the number
        of metrics, so drop it on a metric-rich benchmark (pass the other four) to
        keep the factorial quick.
    normalization, bounds, baselines, targets
        Optional per-metric normalization context forwarded to every run. Pass the
        values from ``beam.mcda.registry_context`` so the decomposition rests on
        the same normalized matrix as the headline ranking.
    missing
        Missing-data policy forwarded to every run. Default ``"error"``.
    tool_names
        Optional length ``n_tools`` labels carried in the report.
    dataset_names
        Optional length ``n_datasets`` labels for a tensor input, carried in the
        report and used to name the dataset levels.

    Returns
    -------
    RankSensitivityReport

    Raises
    ------
    ValueError
        If the shapes do not line up, or fewer than two weightings or two
        aggregations (or, for a tensor, two datasets) survive on this input, so a
        factorial decomposition is undefined.

    Examples
    --------
    >>> import numpy as np
    >>> from beam.mcda import rank_sensitivity
    >>> scores = np.array([[0.9, 30.0], [0.7, 50.0], [0.5, 40.0], [0.3, 70.0]])
    >>> report = rank_sensitivity(scores, ["higher_is_better", "lower_is_better"])
    >>> report.dataset_share is None
    True
    >>> round(sum(report.factor_shares.values()) + report.interaction_share, 6)
    1.0
    """
    scores = np.asarray(scores, dtype=float)
    if scores.ndim not in (2, 3):
        raise ValueError(
            f"scores must be 2D (tools, metrics) or 3D (tools, datasets, metrics); "
            f"got shape {scores.shape}"
        )
    is_tensor = scores.ndim == 3
    n_tools = scores.shape[0]
    n_metrics = scores.shape[-1]
    polarity = list(polarity)
    if len(polarity) != n_metrics:
        raise ValueError(f"polarity has {len(polarity)} entries but scores has {n_metrics} metrics")

    weighting_names = list(_DEFAULT_WEIGHTINGS) if weightings is None else list(weightings)
    method_names = list(_KNOWN_METHODS) if methods is None else list(methods)
    n_datasets = scores.shape[1] if is_tensor else 1
    if dataset_names is not None:
        dataset_names = list(dataset_names)
        if is_tensor and len(dataset_names) != n_datasets:
            raise ValueError(
                f"dataset_names has {len(dataset_names)} entries but scores has "
                f"{n_datasets} datasets"
            )
    ds_labels = (
        (
            dataset_names
            if dataset_names is not None
            else [f"dataset_{d}" for d in range(n_datasets)]
        )
        if is_tensor
        else None
    )

    n_w, n_m = len(weighting_names), len(method_names)
    grid_shape = (n_w, n_m, n_datasets) if is_tensor else (n_w, n_m)
    rank_grid: dict[tuple[int, ...], np.ndarray] = {}
    success = np.zeros(grid_shape, dtype=bool)

    def _slice(d: int) -> np.ndarray:
        return scores[:, d, :] if is_tensor else scores

    for i, weighting in enumerate(weighting_names):
        for j, method in enumerate(method_names):
            for d in range(n_datasets):
                try:
                    result = run(
                        _slice(d),
                        polarity,
                        weights=weighting,
                        method=method,
                        normalization=normalization,
                        bounds=bounds,
                        baselines=baselines,
                        targets=targets,
                        missing=missing,
                    )
                except Exception:
                    continue
                cell = (i, j, d) if is_tensor else (i, j)
                rank_grid[cell] = result.ranks
                success[cell] = True

    kept = _prune_to_complete_grid(success)
    keep_w, keep_m = kept[0], kept[1]
    keep_d = kept[2] if is_tensor else [0]
    min_datasets = 2 if is_tensor else 1
    if len(keep_w) < 2 or len(keep_m) < 2 or len(keep_d) < min_datasets:
        raise ValueError(
            "rank_sensitivity needs at least two weightings, two aggregations and "
            f"(for a tensor) two datasets that all run on this input; after "
            f"dropping the ones that failed, {len(keep_w)} weighting(s), "
            f"{len(keep_m)} aggregation(s) and {len(keep_d)} dataset(s) remain. "
            "Check the matrix is complete (try missing='worst') and not degenerate."
        )

    kept_weightings = [weighting_names[i] for i in keep_w]
    kept_methods = [method_names[j] for j in keep_m]
    kept_datasets = [ds_labels[d] for d in keep_d] if is_tensor else None
    dropped_weightings = [w for w in weighting_names if w not in kept_weightings]
    dropped_methods = [m for m in method_names if m not in kept_methods]
    dropped_datasets = (
        [ds_labels[d] for d in range(n_datasets) if d not in keep_d] if is_tensor else []
    )
    if dropped_weightings or dropped_methods or dropped_datasets:
        _warnings.warn(
            f"rank_sensitivity dropped weighting(s) {dropped_weightings}, "
            f"aggregation(s) {dropped_methods} and dataset(s) {dropped_datasets} "
            "that failed on this input; the decomposition rests on the surviving grid",
            stacklevel=2,
        )

    factor_names = (
        ("weighting", "aggregation", "dataset") if is_tensor else ("weighting", "aggregation")
    )
    if is_tensor:
        ranks = np.empty((n_tools, len(keep_w), len(keep_m), len(keep_d)), dtype=int)
        for ii, i in enumerate(keep_w):
            for jj, j in enumerate(keep_m):
                for dd, d in enumerate(keep_d):
                    ranks[:, ii, jj, dd] = rank_grid[(i, j, d)]
    else:
        ranks = np.empty((n_tools, len(keep_w), len(keep_m)), dtype=int)
        for ii, i in enumerate(keep_w):
            for jj, j in enumerate(keep_m):
                ranks[:, ii, jj] = rank_grid[(i, j)]

    names = list(tool_names) if tool_names is not None else None
    if names is not None and len(names) != n_tools:
        raise ValueError(f"tool_names has {len(names)} entries but scores has {n_tools} rows")

    per_tool: list[ToolRankSensitivity] = []
    pooled_total = 0.0
    pooled_main = [0.0] * len(factor_names)
    pooled_interaction = 0.0
    for t in range(n_tools):
        table = ranks[t].astype(float)
        ss_total, ss_main, ss_interaction = _variance_shares(table)
        pooled_total += ss_total
        pooled_main = [p + s for p, s in zip(pooled_main, ss_main, strict=True)]
        pooled_interaction += ss_interaction
        if ss_total > 0:
            shares = {name: ss / ss_total for name, ss in zip(factor_names, ss_main, strict=True)}
            i_share = ss_interaction / ss_total
        else:
            shares = {name: float("nan") for name in factor_names}
            i_share = float("nan")
        flat = ranks[t].ravel()
        values, counts = np.unique(flat, return_counts=True)
        per_tool.append(
            ToolRankSensitivity(
                tool=t,
                name=names[t] if names is not None else None,
                factor_shares=shares,
                interaction_share=i_share,
                rank_min=int(flat.min()),
                rank_max=int(flat.max()),
                rank_span=int(flat.max() - flat.min()),
                modal_rank=int(values[int(np.argmax(counts))]),
            )
        )

    if pooled_total > 0:
        factor_shares = {
            name: s / pooled_total for name, s in zip(factor_names, pooled_main, strict=True)
        }
        interaction_share = pooled_interaction / pooled_total
    else:
        factor_shares = {name: float("nan") for name in factor_names}
        interaction_share = float("nan")

    all_shares = {**factor_shares, "interaction": interaction_share}
    most_influential = max(all_shares, key=lambda k: all_shares[k]) if pooled_total > 0 else "none"

    wins = (ranks == 1).reshape(n_tools, -1).sum(axis=1)
    headline_tool = int(np.argmax(wins))
    n_combinations = int(np.prod([len(k) for k in (keep_w, keep_m, keep_d)]))
    headline_top_fraction = float(wins[headline_tool] / n_combinations)

    headline_rank_by_dataset = None
    if is_tensor:
        headline_rank_by_dataset = ranks[headline_tool].mean(axis=(0, 1))

    return RankSensitivityReport(
        factors=factor_names,
        weightings=tuple(kept_weightings),
        methods=tuple(kept_methods),
        dataset_names=tuple(kept_datasets) if kept_datasets is not None else None,
        dropped_weightings=tuple(dropped_weightings),
        dropped_methods=tuple(dropped_methods),
        dropped_datasets=tuple(dropped_datasets),
        n_combinations=n_combinations,
        ranks=ranks,
        tool_names=tuple(names) if names is not None else None,
        factor_shares=factor_shares,
        interaction_share=interaction_share,
        most_influential_factor=most_influential,
        per_tool=tuple(per_tool),
        headline_tool=headline_tool,
        headline_top_fraction=headline_top_fraction,
        headline_rank_span=per_tool[headline_tool].rank_span,
        headline_rank_by_dataset=headline_rank_by_dataset,
    )
