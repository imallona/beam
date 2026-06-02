"""Convergent and discriminant validity of a metric set.

A benchmark scores every method on several metrics. Some of those metrics are
meant to measure the same underlying quantity (for example the scIB
biological-conservation metrics ARI, NMI and isolated-label F1 all read how well
cell-type structure survives integration), and others are meant to measure a
different quantity (the batch-correction metrics kBET, iLISI, batch silhouette).
Campbell and Fiske (1959) asked the validity question that follows: do the
metrics that claim to measure the same construct actually agree, and do the
metrics that claim to measure different constructs actually differ?

``metric_validity`` answers it from the scores alone. Each method-by-dataset
cell is one observation; the metrics are the variables. The function orients
every metric so that higher means better (it negates the ranks of a
``lower_is_better`` metric), then computes the Spearman rank correlation between
every pair of metrics over the observations they share. Spearman is the right
choice here: the metrics live on different scales, and a rank correlation reads
"do these two metrics order the methods the same way" without assuming a common
unit.

Grouping the metrics by the construct they claim to measure splits the
correlations into two sets. Within-group correlations are the convergent
evidence: metrics measuring one construct should agree. Between-group
correlations are the discriminant evidence: metrics measuring different
constructs should agree less. When the mean within-group correlation exceeds the
mean between-group correlation, the grouping holds up, and treating the groups as
separate criteria in the MCDA weighting (the scIB 0.6 bio / 0.4 batch split, for
example) is justified by the data rather than by assertion. The report also
flags near-duplicate metrics inside a group (redundant criteria) and any metric
that correlates more with another group than with its own (a metric that does
not measure what its group claims).

This is the trait facet of a multitrait-multimethod matrix. beam records one
measurement per metric per cell, so there is no separate method facet to vary;
the diagnostic is the convergent and discriminant reading of the metric
correlations, not the full MTMM design.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from scipy.stats import spearmanr

_ORIENTATION = {"higher_is_better": 1.0, "lower_is_better": -1.0}


@dataclass(frozen=True)
class MetricValidityReport:
    """Convergent and discriminant validity of a metric set.

    Attributes
    ----------
    metric_ids
        Metric labels in column order, or ``None`` when the input carried none.
    groups
        Construct label per metric, aligned with ``metric_ids``.
    correlation
        ``(n_metrics, n_metrics)`` Spearman rank correlation between metrics,
        oriented so that higher means better on every metric. The diagonal is 1.
        An entry is ``nan`` when the two metrics share fewer than
        ``min_pairwise`` observations or one is constant on the shared rows.
    coverage
        ``(n_metrics, n_metrics)`` count of observations where both metrics are
        observed, the denominator behind each correlation.
    convergent_by_group
        Mean within-group off-diagonal correlation per group, over finite
        entries. A group with one metric has no within-group pair and is absent.
    mean_convergent
        Mean of every within-group off-diagonal correlation, over finite
        entries. The overall convergent-validity summary.
    mean_discriminant
        Mean of every between-group correlation, over finite entries. The
        overall discriminant-validity summary.
    discriminant_ok
        True when ``mean_convergent`` is greater than ``mean_discriminant``, the
        basic Campbell-Fiske criterion that same-construct metrics agree more
        than cross-construct metrics.
    redundant_pairs
        Within-group metric pairs whose correlation is at least
        ``redundant_threshold``, each as ``(metric_a, metric_b, r)`` sorted by
        descending ``r``. Near-duplicate criteria; candidates to drop.
    crossloading_metrics
        Metrics whose mean between-group correlation exceeds their mean
        within-group correlation, each as
        ``(metric, group, mean_within_r, mean_between_r, nearest_group)``, where
        ``nearest_group`` is the other group it correlates with most strongly. A
        metric here agrees more with the other constructs than with its own, the
        per-metric form of a discriminant-validity failure.
    n_observations
        Number of observation rows (method-by-dataset cells) the correlations
        were computed over, before the per-pair NaN masking.
    """

    metric_ids: tuple[str, ...] | None
    groups: tuple[str, ...]
    correlation: np.ndarray
    coverage: np.ndarray
    convergent_by_group: dict[str, float]
    mean_convergent: float
    mean_discriminant: float
    discriminant_ok: bool
    redundant_pairs: tuple[tuple[str, str, float], ...]
    crossloading_metrics: tuple[tuple[str, str, float, float, str], ...]
    n_observations: int


def _oriented(scores: np.ndarray, polarity: Sequence[str]) -> np.ndarray:
    """Return scores with each lower_is_better column negated.

    After this, a higher value is better on every column, so a positive Spearman
    correlation between two columns means they order the methods the same way by
    quality.
    """
    signs = np.array([_ORIENTATION[p] for p in polarity], dtype=float)
    return scores * signs


def _pairwise_spearman(oriented: np.ndarray, min_pairwise: int) -> tuple[np.ndarray, np.ndarray]:
    """Spearman correlation and shared-observation count for every metric pair.

    Computes each pair on the rows where both metrics are observed
    (pairwise-complete). A pair with fewer than ``min_pairwise`` shared rows, or
    one where a metric is constant on the shared rows, gets ``nan``.
    """
    n_metrics = oriented.shape[1]
    corr = np.full((n_metrics, n_metrics), np.nan)
    coverage = np.zeros((n_metrics, n_metrics), dtype=int)
    np.fill_diagonal(corr, 1.0)
    for a in range(n_metrics):
        col_a = oriented[:, a]
        for b in range(a + 1, n_metrics):
            both = np.isfinite(col_a) & np.isfinite(oriented[:, b])
            n_shared = int(both.sum())
            coverage[a, b] = coverage[b, a] = n_shared
            if n_shared < min_pairwise:
                continue
            xa = col_a[both]
            xb = oriented[both, b]
            if np.ptp(xa) == 0 or np.ptp(xb) == 0:
                continue
            r = float(spearmanr(xa, xb).statistic)
            corr[a, b] = corr[b, a] = r
    return corr, coverage


def metric_validity(
    scores,
    polarity: Sequence[str],
    groups: Sequence[str],
    metric_ids: Sequence[str] | None = None,
    redundant_threshold: float = 0.9,
    min_pairwise: int = 3,
) -> MetricValidityReport:
    """Test whether a metric set has convergent and discriminant validity.

    Each method-by-dataset cell is one observation. The function orients every
    metric to higher-is-better, computes the Spearman rank correlation between
    every pair of metrics over their shared observations, and splits the
    correlations by the construct grouping into convergent (within-group) and
    discriminant (between-group) evidence.

    Parameters
    ----------
    scores
        Array-like of shape ``(n_observations, n_metrics)`` or a tensor of shape
        ``(n_methods, n_datasets, n_metrics)``, which is reshaped so that each
        method-by-dataset cell is one observation row. Missing cells are NaN and
        handled pairwise.
    polarity
        Length ``n_metrics`` sequence of ``"higher_is_better"`` or
        ``"lower_is_better"``. Use ``beam.cards.polarities_for`` to source it
        from the registry. A ``"target_value"`` metric has no monotone quality
        direction; drop it before calling.
    groups
        Length ``n_metrics`` construct label per metric, for example
        ``"bio"`` or ``"batch"``. Metrics sharing a label claim to measure the
        same construct.
    metric_ids
        Optional length ``n_metrics`` labels carried into the report and used to
        name the flagged pairs and metrics.
    redundant_threshold
        Within-group correlation at or above which a pair is reported as
        redundant. Default 0.9.
    min_pairwise
        Minimum shared observations for a pair's correlation to be computed.
        Default 3.

    Returns
    -------
    MetricValidityReport

    Raises
    ------
    ValueError
        If the shapes do not line up, a polarity is not one of the two monotone
        values, or the grouping has fewer than two distinct groups or no group
        with at least two metrics (so convergent and discriminant evidence are
        both undefined).

    Examples
    --------
    >>> import numpy as np
    >>> from beam.mcda import metric_validity
    >>> rng = np.random.default_rng(0)
    >>> bio = rng.normal(size=(40, 1))
    >>> batch = rng.normal(size=(40, 1))
    >>> scores = np.hstack([bio + rng.normal(0, 0.1, (40, 1)),
    ...                     bio + rng.normal(0, 0.1, (40, 1)),
    ...                     batch + rng.normal(0, 0.1, (40, 1)),
    ...                     batch + rng.normal(0, 0.1, (40, 1))])
    >>> report = metric_validity(
    ...     scores,
    ...     ["higher_is_better"] * 4,
    ...     ["bio", "bio", "batch", "batch"],
    ... )
    >>> report.discriminant_ok
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
    bad = sorted({p for p in polarity if p not in _ORIENTATION})
    if bad:
        raise ValueError(
            f"metric_validity needs a monotone polarity per metric; got {bad}. "
            f"Drop target_value metrics before calling."
        )
    ids = None if metric_ids is None else list(metric_ids)
    if ids is not None and len(ids) != n_metrics:
        raise ValueError(f"metric_ids has {len(ids)} entries but scores has {n_metrics} columns")

    unique_groups = list(dict.fromkeys(groups))
    if len(unique_groups) < 2:
        raise ValueError(
            f"metric_validity needs at least two distinct groups for discriminant "
            f"evidence; got {unique_groups}"
        )
    group_sizes = {g: groups.count(g) for g in unique_groups}
    if max(group_sizes.values()) < 2:
        raise ValueError(
            "metric_validity needs at least one group with two or more metrics "
            "for convergent evidence; every group has a single metric"
        )

    oriented = _oriented(scores, polarity)
    corr, coverage = _pairwise_spearman(oriented, min_pairwise)

    same_group = np.array(groups)[:, None] == np.array(groups)[None, :]
    off_diagonal = ~np.eye(n_metrics, dtype=bool)
    within_mask = same_group & off_diagonal
    between_mask = ~same_group

    def _name(i: int) -> str:
        return ids[i] if ids is not None else f"metric_{i}"

    convergent_by_group: dict[str, float] = {}
    for g in unique_groups:
        members = [i for i, gi in enumerate(groups) if gi == g]
        if len(members) < 2:
            continue
        block = corr[np.ix_(members, members)]
        block_off = block[~np.eye(len(members), dtype=bool)]
        finite = block_off[np.isfinite(block_off)]
        if finite.size:
            convergent_by_group[g] = float(finite.mean())

    within_values = corr[within_mask]
    within_finite = within_values[np.isfinite(within_values)]
    mean_convergent = float(within_finite.mean()) if within_finite.size else float("nan")

    between_values = corr[between_mask]
    between_finite = between_values[np.isfinite(between_values)]
    mean_discriminant = float(between_finite.mean()) if between_finite.size else float("nan")

    discriminant_ok = bool(
        np.isfinite(mean_convergent)
        and np.isfinite(mean_discriminant)
        and mean_convergent > mean_discriminant
    )

    redundant: list[tuple[str, str, float]] = []
    for a in range(n_metrics):
        for b in range(a + 1, n_metrics):
            if within_mask[a, b] and np.isfinite(corr[a, b]) and corr[a, b] >= redundant_threshold:
                redundant.append((_name(a), _name(b), float(corr[a, b])))
    redundant.sort(key=lambda t: t[2], reverse=True)

    crossloading: list[tuple[str, str, float, float, str]] = []
    for i in range(n_metrics):
        own = groups[i]
        own_members = [j for j in range(n_metrics) if j != i and groups[j] == own]
        own_r = [corr[i, j] for j in own_members if np.isfinite(corr[i, j])]
        between_r = [corr[i, j] for j in range(n_metrics) if groups[j] != own]
        between_finite = [r for r in between_r if np.isfinite(r)]
        if not own_r or not between_finite:
            continue
        mean_own = float(np.mean(own_r))
        mean_between = float(np.mean(between_finite))
        nearest_group = own
        nearest_mean = -np.inf
        for g in unique_groups:
            if g == own:
                continue
            g_r = [corr[i, j] for j in range(n_metrics) if groups[j] == g]
            g_finite = [r for r in g_r if np.isfinite(r)]
            if g_finite and np.mean(g_finite) > nearest_mean:
                nearest_mean = float(np.mean(g_finite))
                nearest_group = g
        if mean_between > mean_own:
            crossloading.append((_name(i), own, mean_own, mean_between, nearest_group))

    return MetricValidityReport(
        metric_ids=tuple(ids) if ids is not None else None,
        groups=tuple(groups),
        correlation=corr,
        coverage=coverage,
        convergent_by_group=convergent_by_group,
        mean_convergent=mean_convergent,
        mean_discriminant=mean_discriminant,
        discriminant_ok=discriminant_ok,
        redundant_pairs=tuple(redundant),
        crossloading_metrics=tuple(crossloading),
        n_observations=int(scores.shape[0]),
    )
