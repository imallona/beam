"""Run the three metric-set diagnostics over one grouping in a single call.

``metric_validity``, ``metric_reliability`` and ``metric_dimensionality`` take
the same inputs (a method-by-dataset-by-metric tensor, the polarity per metric,
and a construct label per metric) and rest on the same oriented pairwise-complete
Spearman correlations. They answer three questions about a metric grouping:

- validity: is the grouping the right split (do same-group metrics agree and
  different-group metrics differ);
- reliability: does each group hold together as one scale (Cronbach's alpha);
- dimensionality: how many factors does each group actually carry.

``metric_diagnostics`` runs all three on one set of inputs and returns the three
frozen reports together, so a caller reads the grouping from every angle without
repeating the boilerplate. Validity is skipped (left ``None``) when there is only
one construct, since convergent and discriminant evidence need at least two.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .dimensionality import MetricDimensionalityReport, metric_dimensionality
from .metric_validity import MetricValidityReport, metric_validity
from .reliability import MetricReliabilityReport, metric_reliability


@dataclass(frozen=True)
class MetricDiagnosticsReport:
    """The three metric-set diagnostics for one grouping.

    Attributes
    ----------
    validity
        Convergent and discriminant validity of the grouping, or ``None`` when
        the input has a single construct (validity needs at least two).
    reliability
        Internal-consistency reliability (standardized Cronbach's alpha) per
        group.
    dimensionality
        Factor count per group by parallel analysis.
    """

    validity: MetricValidityReport | None
    reliability: MetricReliabilityReport
    dimensionality: MetricDimensionalityReport


def metric_diagnostics(
    scores,
    polarity: Sequence[str],
    groups: Sequence[str],
    metric_ids: Sequence[str] | None = None,
    min_pairwise: int = 3,
    redundant_threshold: float = 0.9,
    alpha_threshold: float = 0.7,
    n_iter: int = 500,
    seed: int = 0,
) -> MetricDiagnosticsReport:
    """Run validity, reliability and dimensionality on one metric grouping.

    Parameters
    ----------
    scores
        Array-like of shape ``(n_observations, n_metrics)`` or a tensor of shape
        ``(n_methods, n_datasets, n_metrics)``, passed through to each
        diagnostic unchanged.
    polarity
        Length ``n_metrics`` sequence of ``"higher_is_better"`` or
        ``"lower_is_better"``. Use ``beam.cards.polarities_for`` to source it
        from the registry.
    groups
        Length ``n_metrics`` construct label per metric.
    metric_ids
        Optional length ``n_metrics`` labels carried into each report.
    min_pairwise
        Minimum shared observations for a metric pair's correlation, shared by
        all three diagnostics. Default 3.
    redundant_threshold
        Within-group correlation at or above which ``metric_validity`` reports a
        pair as redundant. Default 0.9.
    alpha_threshold
        Alpha below which ``metric_reliability`` flags a group. Default 0.7.
    n_iter
        Random matrices ``metric_dimensionality`` averages parallel analysis
        over. Default 500.
    seed
        Seed for the parallel-analysis draws. Default 0.

    Returns
    -------
    MetricDiagnosticsReport

    Raises
    ------
    ValueError
        Propagated from the underlying diagnostics if the shapes do not line up,
        a polarity is not monotone, or no group has two or more metrics.

    Examples
    --------
    >>> import numpy as np
    >>> from beam.mcda import metric_diagnostics
    >>> rng = np.random.default_rng(0)
    >>> bio = rng.normal(size=(60, 1))
    >>> batch = rng.normal(size=(60, 1))
    >>> scores = np.hstack([bio + rng.normal(0, 0.1, (60, 1)),
    ...                     bio + rng.normal(0, 0.1, (60, 1)),
    ...                     batch + rng.normal(0, 0.1, (60, 1)),
    ...                     batch + rng.normal(0, 0.1, (60, 1))])
    >>> report = metric_diagnostics(
    ...     scores,
    ...     ["higher_is_better"] * 4,
    ...     ["bio", "bio", "batch", "batch"],
    ... )
    >>> report.validity.discriminant_ok
    True
    """
    has_two_constructs = len(dict.fromkeys(groups)) >= 2
    validity = (
        metric_validity(
            scores,
            polarity,
            groups,
            metric_ids=metric_ids,
            redundant_threshold=redundant_threshold,
            min_pairwise=min_pairwise,
        )
        if has_two_constructs
        else None
    )
    reliability = metric_reliability(
        scores,
        polarity,
        groups,
        metric_ids=metric_ids,
        alpha_threshold=alpha_threshold,
        min_pairwise=min_pairwise,
    )
    dimensionality = metric_dimensionality(
        scores,
        polarity,
        groups,
        metric_ids=metric_ids,
        min_pairwise=min_pairwise,
        n_iter=n_iter,
        seed=seed,
    )
    return MetricDiagnosticsReport(
        validity=validity,
        reliability=reliability,
        dimensionality=dimensionality,
    )
