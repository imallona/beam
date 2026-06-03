"""Internal-consistency reliability of a metric group (Cronbach's alpha).

A benchmark often treats a group of metrics as one criterion. The scIB
integration score, for example, groups its metrics into biological conservation
and batch correction and weights the two groups 0.6 and 0.4, so each group acts
as a single composite scale. ``beam.mcda.metric_validity`` asks whether that
grouping is valid (do same-group metrics agree and different-group metrics
differ). Reliability asks the companion question: if the group is going to be
read as one scale, how consistently do its metrics measure one thing?

Cronbach (1951) alpha is the standard internal-consistency coefficient. This
module reports the standardized form, which depends only on the number of
metrics in the group ``k`` and the mean correlation between them ``r_bar``:

    alpha = k * r_bar / (1 + (k - 1) * r_bar)

The standardized form is the right choice here for the same reason
``metric_validity`` uses rank correlation: the metrics live on different scales,
so a coefficient built from the inter-item correlation, not from raw
covariances, is the scale-free reading. The correlations are the oriented
Spearman correlations ``metric_validity`` already computes, so the two
diagnostics share one engine and read together. Reliability is the rank-based
analogue of classical alpha, consistent with the project's use of Spearman for
every cross-metric comparison.

Alpha rises with both the mean inter-item correlation and the number of metrics.
A high value can therefore mean a tightly agreeing group or merely a large one,
so the report carries ``k`` and ``r_bar`` next to each alpha. The per-metric
"alpha if dropped" diagnostic recomputes a group's alpha with one metric removed
and flags any metric whose removal raises the group's reliability, the metric
that pulls hardest against the rest of its group.

The standard reading of alpha (a single-factor reflective model, a group that is
meant to be unidimensional) is an assumption, not a fact about a benchmark's
metrics. A low alpha says the group does not behave as one reliable scale; it
does not say which metric to trust. As with ``metric_validity``, the result is
descriptive of the methods and datasets in the input, and a small benchmark
gives a coarse estimate.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from .metric_validity import _oriented, _pairwise_spearman


@dataclass(frozen=True)
class MetricReliabilityReport:
    """Internal-consistency reliability of each metric group.

    Attributes
    ----------
    metric_ids
        Metric labels in column order, or ``None`` when the input carried none.
    groups
        Construct label per metric, aligned with ``metric_ids``.
    alpha_by_group
        Standardized Cronbach's alpha per group with at least two metrics and at
        least one finite within-group correlation. A group with no finite pair is
        absent. Alpha can be negative when the metrics correlate negatively once
        oriented, which itself signals a group that is not one scale.
    mean_inter_item_by_group
        Mean within-group correlation ``r_bar`` per group, the quantity alpha is
        built from. Matches ``metric_validity``'s ``convergent_by_group``.
    k_by_group
        Number of metrics in each reported group, the ``k`` in the alpha formula.
    alpha_if_dropped
        Per metric in a group of three or more, the group's alpha recomputed
        without that metric, as ``(metric, group, alpha_without)``. A value above
        the group's ``alpha_by_group`` means dropping the metric makes the group
        more reliable. Metrics in a group of two are omitted (dropping one leaves
        a single metric, for which alpha is undefined).
    low_reliability_groups
        Groups whose alpha is below ``alpha_threshold``, each as
        ``(group, alpha)`` sorted by ascending alpha. These groups do not read as
        one reliable scale at the chosen cutoff.
    n_observations
        Number of observation rows (method-by-dataset cells) the correlations
        were computed over, before the per-pair NaN masking.
    """

    metric_ids: tuple[str, ...] | None
    groups: tuple[str, ...]
    alpha_by_group: dict[str, float]
    mean_inter_item_by_group: dict[str, float]
    k_by_group: dict[str, int]
    alpha_if_dropped: tuple[tuple[str, str, float], ...]
    low_reliability_groups: tuple[tuple[str, float], ...]
    n_observations: int


def _standardized_alpha(corr: np.ndarray, members: Sequence[int]) -> tuple[float, float]:
    """Standardized alpha and mean inter-item correlation over a group block.

    Averages the off-diagonal correlations of the group's metrics over the finite
    entries, then applies the standardized-alpha formula. Returns ``(nan, nan)``
    when the group has fewer than two metrics or no finite within-group pair, and
    a ``nan`` alpha with a finite ``r_bar`` when the denominator
    ``1 + (k - 1) * r_bar`` is zero.
    """
    k = len(members)
    if k < 2:
        return float("nan"), float("nan")
    block = corr[np.ix_(members, members)]
    off_diagonal = block[~np.eye(k, dtype=bool)]
    finite = off_diagonal[np.isfinite(off_diagonal)]
    if not finite.size:
        return float("nan"), float("nan")
    r_bar = float(finite.mean())
    denominator = 1.0 + (k - 1) * r_bar
    if denominator == 0:
        return float("nan"), r_bar
    alpha = k * r_bar / denominator
    return float(alpha), r_bar


def metric_reliability(
    scores,
    polarity: Sequence[str],
    groups: Sequence[str],
    metric_ids: Sequence[str] | None = None,
    alpha_threshold: float = 0.7,
    min_pairwise: int = 3,
) -> MetricReliabilityReport:
    """Standardized Cronbach's alpha for each construct group of metrics.

    Each method-by-dataset cell is one observation. The function orients every
    metric to higher-is-better, computes the Spearman rank correlation between
    every pair of metrics over their shared observations (the same engine as
    ``metric_validity``), and reports the standardized alpha
    ``k * r_bar / (1 + (k - 1) * r_bar)`` for each group, where ``k`` is the
    group size and ``r_bar`` the mean within-group correlation.

    Parameters
    ----------
    scores
        Array-like of shape ``(n_observations, n_metrics)`` or a tensor of shape
        ``(n_methods, n_datasets, n_metrics)``, reshaped so that each
        method-by-dataset cell is one observation row. Missing cells are NaN and
        handled pairwise.
    polarity
        Length ``n_metrics`` sequence of ``"higher_is_better"`` or
        ``"lower_is_better"``. Use ``beam.cards.polarities_for`` to source it from
        the registry. A ``"target_value"`` metric has no monotone quality
        direction; drop it before calling.
    groups
        Length ``n_metrics`` construct label per metric. Metrics sharing a label
        are read together as one composite scale.
    metric_ids
        Optional length ``n_metrics`` labels carried into the report and used to
        name the alpha-if-dropped entries.
    alpha_threshold
        Alpha below which a group is reported as low-reliability. Default 0.7,
        the conventional cutoff.
    min_pairwise
        Minimum shared observations for a pair's correlation to be computed.
        Default 3.

    Returns
    -------
    MetricReliabilityReport

    Raises
    ------
    ValueError
        If the shapes do not line up, a polarity is not one of the two monotone
        values, or no group has at least two metrics (so no alpha is defined).

    Examples
    --------
    >>> import numpy as np
    >>> from beam.mcda import metric_reliability
    >>> rng = np.random.default_rng(0)
    >>> factor = rng.normal(size=(40, 1))
    >>> scores = np.hstack([factor + rng.normal(0, 0.2, (40, 1)) for _ in range(3)])
    >>> report = metric_reliability(
    ...     scores,
    ...     ["higher_is_better"] * 3,
    ...     ["bio", "bio", "bio"],
    ... )
    >>> report.alpha_by_group["bio"] > 0.8
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
            f"metric_reliability needs a monotone polarity per metric; got {bad}. "
            f"Drop target_value metrics before calling."
        )
    ids = None if metric_ids is None else list(metric_ids)
    if ids is not None and len(ids) != n_metrics:
        raise ValueError(f"metric_ids has {len(ids)} entries but scores has {n_metrics} columns")

    unique_groups = list(dict.fromkeys(groups))
    group_sizes = {g: groups.count(g) for g in unique_groups}
    if max(group_sizes.values()) < 2:
        raise ValueError(
            "metric_reliability needs at least one group with two or more metrics; "
            "every group has a single metric, so no alpha is defined"
        )

    oriented = _oriented(scores, polarity)
    corr, _coverage = _pairwise_spearman(oriented, min_pairwise)

    def _name(i: int) -> str:
        return ids[i] if ids is not None else f"metric_{i}"

    alpha_by_group: dict[str, float] = {}
    mean_inter_item_by_group: dict[str, float] = {}
    k_by_group: dict[str, int] = {}
    alpha_if_dropped: list[tuple[str, str, float]] = []
    for g in unique_groups:
        members = [i for i, gi in enumerate(groups) if gi == g]
        if len(members) < 2:
            continue
        alpha, r_bar = _standardized_alpha(corr, members)
        if not np.isfinite(r_bar):
            continue
        alpha_by_group[g] = alpha
        mean_inter_item_by_group[g] = r_bar
        k_by_group[g] = len(members)
        if len(members) >= 3:
            for dropped in members:
                kept = [i for i in members if i != dropped]
                alpha_without, _ = _standardized_alpha(corr, kept)
                if np.isfinite(alpha_without):
                    alpha_if_dropped.append((_name(dropped), g, alpha_without))

    low_reliability = [
        (g, a) for g, a in alpha_by_group.items() if np.isfinite(a) and a < alpha_threshold
    ]
    low_reliability.sort(key=lambda t: t[1])

    return MetricReliabilityReport(
        metric_ids=tuple(ids) if ids is not None else None,
        groups=tuple(groups),
        alpha_by_group=alpha_by_group,
        mean_inter_item_by_group=mean_inter_item_by_group,
        k_by_group=k_by_group,
        alpha_if_dropped=tuple(alpha_if_dropped),
        low_reliability_groups=tuple(low_reliability),
        n_observations=int(scores.shape[0]),
    )
