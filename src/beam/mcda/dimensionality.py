"""Dimensionality of a metric group (how many factors the metrics carry).

``beam.mcda.metric_reliability`` reports standardized Cronbach's alpha for a
construct group, and alpha reads a group as one reliable scale when it is high.
That reading rests on an assumption alpha cannot check: that the group is a
single reflective factor, one underlying quantity each metric measures with
noise. Alpha also rises with the number of metrics, so a long group can reach a
high alpha while carrying more than one factor. This module checks the
assumption directly by counting the factors in the group.

The check is principal component analysis of the same oriented Spearman
correlation matrix that ``metric_validity`` and ``metric_reliability`` use, so
the three diagnostics rest on one set of numbers. For a group of ``k`` metrics
the correlation matrix has ``k`` eigenvalues that sum to ``k`` (its trace). A
single dominant eigenvalue means one factor; several eigenvalues of comparable
size mean several. The report carries, per group:

- the eigenvalues in descending order;
- the share of variance the first component explains, ``lambda_1 / k``;
- the number of components by the Kaiser (1960) rule, the count of eigenvalues
  above one;
- the number of components by parallel analysis (Horn 1965), the count of
  observed eigenvalues that exceed the level a random matrix of the same size
  reaches at the same rank.

Kaiser is the quick rule and is known to keep too many components, since with a
finite sample the later eigenvalues sit above one by chance. Parallel analysis
corrects for that by comparing each observed eigenvalue against the level chance
alone would reach. The level is the 95th percentile of the random eigenvalues at
each rank (Glorfeld 1995 sharpens Horn's original mean rule, which retains a
component too readily on noise), so it is the verdict the report uses for the
unidimensional flag. A group is reported as unidimensional when parallel
analysis retains exactly one component.

Dimensionality reads alongside reliability rather than instead of it. A high
alpha on a group that turns out to carry two factors is the case this check
exists to surface: the group is internally consistent enough to look like one
scale, but it is not one thing. As with the other two diagnostics, the result is
descriptive of the methods and datasets in the input, and a small benchmark
gives a coarse estimate.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from scipy.stats import rankdata

from .metric_validity import _oriented, _pairwise_spearman


@dataclass(frozen=True)
class MetricDimensionalityReport:
    """How many factors each metric group carries.

    Attributes
    ----------
    metric_ids
        Metric labels in column order, or ``None`` when the input carried none.
    groups
        Construct label per metric, aligned with ``metric_ids``.
    eigenvalues_by_group
        Eigenvalues of the within-group correlation matrix in descending order,
        per assessed group. They sum to the group size ``k``.
    pc1_explained_by_group
        Share of total variance the first component explains, ``lambda_1 / k``,
        per assessed group. Runs from ``1 / k`` (no shared variance) to 1 (one
        perfect factor).
    kaiser_components_by_group
        Number of eigenvalues above one per assessed group, the Kaiser (1960)
        rule. This rule tends to keep too many components.
    parallel_components_by_group
        Number of components parallel analysis (Horn 1965) retains per assessed
        group, the count of observed eigenvalues above the chance level. This is
        the recommended reading.
    k_by_group
        Number of metrics in each assessed group.
    unidimensional_groups
        Groups parallel analysis retains exactly one component for, sorted. These
        read as one factor, so a high reliability on them reflects one scale.
    multidimensional_groups
        Groups parallel analysis retains more than one component for, each as
        ``(group, n_components)`` sorted by descending component count. A high
        reliability on these reflects more than one factor.
    undefined_groups
        Groups that could not be assessed, each as ``(group, reason)``. A group
        is undefined when its within-group correlation matrix has a missing entry
        (a metric pair with too few shared observations or a constant metric), or
        when the input has too few observations to run parallel analysis against
        the group size.
    n_observations
        Number of observation rows (method-by-dataset cells) the correlations
        were computed over, before the per-pair NaN masking.
    n_iter
        Number of random matrices parallel analysis averaged over.
    seed
        Seed for the parallel-analysis random draws, so the report reproduces.
    """

    metric_ids: tuple[str, ...] | None
    groups: tuple[str, ...]
    eigenvalues_by_group: dict[str, tuple[float, ...]]
    pc1_explained_by_group: dict[str, float]
    kaiser_components_by_group: dict[str, int]
    parallel_components_by_group: dict[str, int]
    k_by_group: dict[str, int]
    unidimensional_groups: tuple[str, ...]
    multidimensional_groups: tuple[tuple[str, int], ...]
    undefined_groups: tuple[tuple[str, str], ...]
    n_observations: int
    n_iter: int
    seed: int


def _parallel_reference(n_obs: int, k: int, n_iter: int, seed: int) -> np.ndarray:
    """95th-percentile descending eigenvalues of random rank-correlation matrices.

    Draws ``n_iter`` matrices of ``n_obs`` rows by ``k`` independent standard
    normal columns, ranks each column, and takes the eigenvalues of the resulting
    Spearman correlation matrix. The 95th percentile per rank is the level chance
    alone reaches with no real association between the metrics, the benchmark
    parallel analysis compares the observed eigenvalues against (Glorfeld 1995).
    """
    rng = np.random.default_rng([seed, k])
    draws = np.empty((n_iter, k))
    for i in range(n_iter):
        data = rng.standard_normal((n_obs, k))
        ranked = np.apply_along_axis(rankdata, 0, data)
        eigenvalues = np.linalg.eigvalsh(np.corrcoef(ranked, rowvar=False))
        draws[i] = np.sort(eigenvalues)[::-1]
    return np.percentile(draws, 95, axis=0)


def metric_dimensionality(
    scores,
    polarity: Sequence[str],
    groups: Sequence[str],
    metric_ids: Sequence[str] | None = None,
    min_pairwise: int = 3,
    n_iter: int = 500,
    seed: int = 0,
) -> MetricDimensionalityReport:
    """Count the factors in each construct group of metrics.

    Each method-by-dataset cell is one observation. The function orients every
    metric to higher-is-better, computes the Spearman rank correlation between
    every pair of metrics over their shared observations (the same engine as
    ``metric_validity`` and ``metric_reliability``), and, for each group, takes
    the eigenvalues of the within-group correlation matrix. It reports how many
    factors the group carries by the Kaiser rule and by parallel analysis, and
    flags the groups that read as one factor.

    Parameters
    ----------
    scores
        Array-like of shape ``(n_observations, n_metrics)`` or a tensor of shape
        ``(n_methods, n_datasets, n_metrics)``, reshaped so that each
        method-by-dataset cell is one observation row. Missing cells are NaN and
        handled pairwise.
    polarity
        Length ``n_metrics`` sequence of ``"higher_is_better"`` or
        ``"lower_is_better"``. Use ``beam.cards.polarities_for`` to source it
        from the registry. A ``"target_value"`` metric has no monotone quality
        direction; drop it before calling.
    groups
        Length ``n_metrics`` construct label per metric. Metrics sharing a label
        are read together as one composite scale.
    metric_ids
        Optional length ``n_metrics`` labels carried into the report.
    min_pairwise
        Minimum shared observations for a pair's correlation to be computed.
        Default 3.
    n_iter
        Number of random matrices parallel analysis averages over. Default 500.
    seed
        Seed for the parallel-analysis random draws, so the result reproduces.
        Default 0.

    Returns
    -------
    MetricDimensionalityReport

    Raises
    ------
    ValueError
        If the shapes do not line up, a polarity is not one of the two monotone
        values, or no group has at least two metrics (so no factor count is
        defined).

    Examples
    --------
    >>> import numpy as np
    >>> from beam.mcda import metric_dimensionality
    >>> rng = np.random.default_rng(0)
    >>> factor = rng.normal(size=(60, 1))
    >>> scores = np.hstack([factor + rng.normal(0, 0.2, (60, 1)) for _ in range(4)])
    >>> report = metric_dimensionality(
    ...     scores,
    ...     ["higher_is_better"] * 4,
    ...     ["bio"] * 4,
    ... )
    >>> "bio" in report.unidimensional_groups
    True
    """
    scores = np.asarray(scores, dtype=float)
    if scores.ndim == 3:
        scores = scores.reshape(-1, scores.shape[2])
    if scores.ndim != 2:
        raise ValueError(
            f"scores must be 2D (observations, metrics) or 3D "
            f"(methods, datasets, metrics); got shape {scores.shape}"
        )
    n_metrics = scores.shape[1]
    polarity = list(polarity)
    groups = list(groups)
    if len(polarity) != n_metrics:
        raise ValueError(f"polarity has {len(polarity)} entries but scores has {n_metrics} columns")
    if len(groups) != n_metrics:
        raise ValueError(f"groups has {len(groups)} entries but scores has {n_metrics} columns")
    bad = sorted({p for p in polarity if p not in ("higher_is_better", "lower_is_better")})
    if bad:
        raise ValueError(
            f"metric_dimensionality needs a monotone polarity per metric; got {bad}. "
            f"Drop target_value metrics before calling."
        )
    ids = None if metric_ids is None else list(metric_ids)
    if ids is not None and len(ids) != n_metrics:
        raise ValueError(f"metric_ids has {len(ids)} entries but scores has {n_metrics} columns")

    unique_groups = list(dict.fromkeys(groups))
    group_sizes = {g: groups.count(g) for g in unique_groups}
    if max(group_sizes.values()) < 2:
        raise ValueError(
            "metric_dimensionality needs at least one group with two or more metrics; "
            "every group has a single metric, so no factor count is defined"
        )

    n_obs = int(scores.shape[0])
    oriented = _oriented(scores, polarity)
    corr, _coverage = _pairwise_spearman(oriented, min_pairwise)

    eigenvalues_by_group: dict[str, tuple[float, ...]] = {}
    pc1_explained_by_group: dict[str, float] = {}
    kaiser_by_group: dict[str, int] = {}
    parallel_by_group: dict[str, int] = {}
    k_by_group: dict[str, int] = {}
    undefined: list[tuple[str, str]] = []
    for g in unique_groups:
        members = [i for i, gi in enumerate(groups) if gi == g]
        k = len(members)
        if k < 2:
            continue
        block = corr[np.ix_(members, members)]
        if not np.isfinite(block).all():
            undefined.append((g, "incomplete within-group correlations"))
            continue
        if n_obs <= k:
            undefined.append((g, f"{n_obs} observations is too few for {k} metrics"))
            continue
        eigenvalues = np.sort(np.linalg.eigvalsh(block))[::-1]
        reference = _parallel_reference(n_obs, k, n_iter, seed)
        eigenvalues_by_group[g] = tuple(float(v) for v in eigenvalues)
        pc1_explained_by_group[g] = float(eigenvalues[0] / k)
        kaiser_by_group[g] = int((eigenvalues > 1.0).sum())
        parallel_by_group[g] = int((eigenvalues > reference).sum())
        k_by_group[g] = k

    unidimensional = sorted(g for g, n in parallel_by_group.items() if n == 1)
    multidimensional = sorted(
        ((g, n) for g, n in parallel_by_group.items() if n > 1),
        key=lambda t: (-t[1], t[0]),
    )

    return MetricDimensionalityReport(
        metric_ids=tuple(ids) if ids is not None else None,
        groups=tuple(groups),
        eigenvalues_by_group=eigenvalues_by_group,
        pc1_explained_by_group=pc1_explained_by_group,
        kaiser_components_by_group=kaiser_by_group,
        parallel_components_by_group=parallel_by_group,
        k_by_group=k_by_group,
        unidimensional_groups=tuple(unidimensional),
        multidimensional_groups=tuple(multidimensional),
        undefined_groups=tuple(undefined),
        n_observations=n_obs,
        n_iter=n_iter,
        seed=seed,
    )
