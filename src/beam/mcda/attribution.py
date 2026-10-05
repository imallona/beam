"""Analyst choice, dataset and benchmarker on one rank-variance scale.

``rank_sensitivity`` splits the rank variance within one benchmark between
the analyst's choices (weighting, aggregation) and the dataset.
``source_variance_decomposition`` splits the variance of the mean ranks
across benchmarks between the method and the benchmark. The two are on
different scales.

``attribution_synthesis`` expresses both as shares of one total. For each
setting there are three non-negative shares summing to one:

- analyst choice: the weighting and the aggregation;
- dataset: the dataset the methods are scored on;
- benchmarker: the scoring benchmark or pipeline.

No single decomposition covers all three in every setting, so each setting
has its own rule:

- Within one benchmark, from a ``RankSensitivityReport``: analyst choice is
  the weighting plus aggregation share, dataset is the dataset main effect,
  and benchmarker is zero. The interaction share is divided between analyst
  choice and dataset in proportion to their main effects.

- Across pooled benchmarks, from a ``SourceVarianceReport`` plus an
  analyst-choice share measured on the pooled matrix: the remainder is
  divided between benchmarker (the method-by-benchmark component) and
  dataset (every other component) in the ratio from the mixed model.

- On a same-data contrast, where two or more pipelines score the methods on
  the same datasets: dataset is zero. After centring each method on its mean
  rank, the remaining variance is divided into a pipeline offset
  (benchmarker) and a method-by-pipeline reordering (analyst choice).

Passed in order, from one benchmark to a same-data contrast, the analyst
choice share rises as the dataset contribution is removed.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class AttributionSetting:
    """One setting's rank variance split over the three sources.

    Attributes
    ----------
    label
        The setting name shown on the figure axis.
    analyst_choice_share, dataset_share, benchmarker_share
        Non-negative shares of the setting's rank variance, summing to one.
        ``analyst_choice_share`` is the weighting and aggregation,
        ``dataset_share`` the dataset the methods are scored on, and
        ``benchmarker_share`` the scoring benchmark or pipeline.
    basis
        The decomposition the shares came from, for provenance.
    """

    label: str
    analyst_choice_share: float
    dataset_share: float
    benchmarker_share: float
    basis: str


@dataclass(frozen=True)
class AttributionReport:
    """The attribution split across an ordered list of settings."""

    settings: tuple[AttributionSetting, ...]


def _normalize_triple(
    analyst: float, dataset: float, benchmarker: float
) -> tuple[float, float, float]:
    """Scale three non-negative shares to sum to one, or to nan when all zero."""
    parts = np.array([analyst, dataset, benchmarker], dtype=float)
    parts = np.where(np.isfinite(parts) & (parts > 0), parts, 0.0)
    total = float(parts.sum())
    if total <= 0:
        return float("nan"), float("nan"), float("nan")
    a, d, b = parts / total
    return float(a), float(d), float(b)


def setting_from_rank_sensitivity(report, label: str) -> AttributionSetting:
    """Within-benchmark split from a rank-sensitivity decomposition.

    The weighting and aggregation shares are the analyst choice, the dataset
    share is the dataset main effect, and the benchmarker share is zero. The
    interaction share is divided between analyst choice and dataset in
    proportion to their main effects, so the three sum to one.
    """
    shares = report.factor_shares
    analyst = float(shares.get("weighting", 0.0)) + float(shares.get("aggregation", 0.0))
    dataset = float(shares.get("dataset", 0.0) or 0.0)
    interaction = float(report.interaction_share)
    base = analyst + dataset
    if np.isfinite(interaction) and base > 0:
        analyst += interaction * analyst / base
        dataset += interaction * dataset / base
    a, d, b = _normalize_triple(analyst, dataset, 0.0)
    return AttributionSetting(label, a, d, b, "rank_sensitivity")


def setting_from_source_variance(
    report, analyst_choice_share: float, label: str
) -> AttributionSetting:
    """Pooled cross-benchmark split from a source-variance decomposition.

    ``analyst_choice_share`` is the weighting-plus-aggregation rank-variance
    share measured on the pooled matrix, in ``[0, 1]``. The remainder,
    ``1 - analyst_choice_share``, is split between the benchmarker (the
    method-by-benchmark component) and the dataset (every other component) in the
    ratio from the mixed model.
    """
    analyst = float(np.clip(analyst_choice_share, 0.0, 1.0))
    benchmarker_raw = float(report.method_benchmark_share)
    dataset_raw = 1.0 - benchmarker_raw
    remaining = 1.0 - analyst
    benchmarker = remaining * benchmarker_raw
    dataset = remaining * dataset_raw
    a, d, b = _normalize_triple(analyst, dataset, benchmarker)
    return AttributionSetting(label, a, d, b, "source_variance")


def setting_from_same_data_contrast(
    ranks_by_source: Mapping[str, Sequence[float]], label: str
) -> AttributionSetting:
    """Same-data split from per-method ranks under two or more pipelines.

    Every source scores the methods on the same datasets, so the dataset
    share is zero. Each method's rank is centred on its mean across sources,
    which removes the order shared by the sources. The remaining variance is
    divided into a source offset (benchmarker) and a method-by-source
    reordering (analyst choice).
    """
    sources = list(ranks_by_source)
    if len(sources) < 2:
        raise ValueError("a same-data contrast needs at least two sources")
    table = np.array([np.asarray(ranks_by_source[s], dtype=float) for s in sources]).T
    if table.ndim != 2 or table.shape[0] < 2:
        raise ValueError("each source must give a rank per method, with at least two methods")
    centered = table - table.mean(axis=1, keepdims=True)
    ss_total = float((centered**2).sum())
    n_methods = table.shape[0]
    source_means = centered.mean(axis=0)
    ss_source = n_methods * float((source_means**2).sum())
    ss_reorder = ss_total - ss_source
    if ss_total <= 0:
        a, d, b = _normalize_triple(0.0, 0.0, 0.0)
    else:
        a, d, b = _normalize_triple(ss_reorder, 0.0, ss_source)
    return AttributionSetting(label, a, d, b, "same_data_contrast")


def attribution_synthesis(settings: Sequence[AttributionSetting]) -> AttributionReport:
    """Bundle an ordered list of attribution settings into one report.

    Pass the settings in order, from one benchmark to a same-data contrast,
    so the figure shows the analyst choice share rising as the dataset
    contribution is removed.
    """
    settings = tuple(settings)
    if not settings:
        raise ValueError("attribution_synthesis needs at least one setting")
    return AttributionReport(settings=settings)
