"""Compare raw method scores to per-metric reference levels.

Two honesty checks read raw scores against a declared reference value on each
metric, before any normalization or weighting. They qualify a ranking that the
MCDA pipeline would otherwise present without a caveat.

``beats_random_baseline`` reads ``semantics.score_of_random_baseline``: per
metric, the share of tools whose score is better than chance. A tool that beats
chance on no metric is no better than a random method on the evidence given.

``noise_floor_separation`` reads ``comparability.noise_floor``: the smallest
difference in native units that is interpretable on a metric. A pair of tools
separated by less than the noise floor on every metric that declares one is not
distinguishable within measurement noise. Any ranking between them, and any
weight perturbation that flips them, then rests on differences below the floor.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class MetricBaseline:
    """How many tools beat the chance level on one metric.

    Attributes
    ----------
    metric
        Metric id, or ``None`` when the matrix carried no ids.
    baseline
        The declared chance score in native units.
    polarity
        The metric polarity, which sets the direction of "beats".
    n_observed
        Tools with a non-NaN score on this metric.
    n_beating
        Tools strictly better than the baseline.
    fraction_beating
        ``n_beating / n_observed``, NaN when ``n_observed`` is 0.
    """

    metric: str | None
    baseline: float
    polarity: str
    n_observed: int
    n_beating: int
    fraction_beating: float


@dataclass(frozen=True)
class RandomBaselineReport:
    """Per-metric chance comparison plus the tools that never beat chance.

    ``per_metric`` covers only the metrics that declare a baseline.
    ``tools_never_beating`` lists the indices of tools that beat chance on none
    of those metrics while having at least one observed score among them. On the
    evidence given those tools are not distinguishable from a random method.
    """

    per_metric: tuple[MetricBaseline, ...]
    tools_never_beating: tuple[int, ...]

    @property
    def active(self) -> bool:
        """True when at least one metric declares a chance baseline."""
        return len(self.per_metric) > 0


@dataclass(frozen=True)
class PairSeparation:
    """Whether two tools are separated above the noise floor on any metric.

    Attributes
    ----------
    a, b
        Tool indices, with ``a < b``.
    separated
        True when at least one metric separates the pair by at least its noise
        floor.
    comparable
        True when the pair has at least one observed score on a metric that
        declares a floor. A pair that is not comparable is neither separated nor
        flagged indistinguishable, because the floors say nothing about it.
    max_metric
        Index of the metric with the largest difference-over-floor ratio, or
        ``-1`` when the pair is not comparable.
    max_ratio
        That largest ``|score_a - score_b| / noise_floor`` ratio, ``0.0`` when
        the pair is not comparable.
    """

    a: int
    b: int
    separated: bool
    comparable: bool
    max_metric: int
    max_ratio: float


@dataclass(frozen=True)
class NoiseFloorReport:
    """Pairwise separation against the per-metric noise floors.

    ``per_pair`` holds every unordered pair (empty when no metric declares a
    floor). ``indistinguishable_pairs`` holds the comparable pairs that no metric
    separates above its floor. ``top_pair`` is the pair of the two top-ranked
    tools when ``ranks`` was given, and ``top_pair_indistinguishable`` flags when
    that pair falls within the noise floor on every metric that declares one.
    """

    per_pair: tuple[PairSeparation, ...]
    indistinguishable_pairs: tuple[tuple[int, int], ...]
    top_pair: tuple[int, int] | None
    top_pair_indistinguishable: bool

    @property
    def active(self) -> bool:
        """True when at least one metric declares a noise floor."""
        return len(self.per_pair) > 0


def beats_random_baseline(
    scores,
    polarity: Sequence[str],
    baselines: Sequence[float | None],
    metric_ids: Sequence[str] | None = None,
) -> RandomBaselineReport:
    """Count, per metric, how many tools score better than chance.

    A tool beats chance on a metric when its score is strictly past the declared
    baseline in the metric's favourable direction: above the baseline for a
    ``higher_is_better`` metric, below it for ``lower_is_better``. A
    ``target_value`` metric has no chance level, so it is skipped even if a
    baseline is declared. Metrics without a baseline are skipped.

    Parameters
    ----------
    scores
        Array-like of shape ``(n_tools, n_metrics)`` in native units.
    polarity
        Length ``n_metrics`` polarity strings.
    baselines
        Length ``n_metrics`` chance scores, ``None`` where the card declares
        none. Pass ``beam.mcda.registry_context(...).baselines``.
    metric_ids
        Optional metric ids used to label the per-metric rows.

    Returns
    -------
    RandomBaselineReport
    """
    x = np.asarray(scores, dtype=float)
    if x.ndim != 2:
        raise ValueError(f"scores must be 2D; got shape {x.shape}")
    polarity = tuple(polarity)
    baselines = tuple(baselines)
    n_tools, n_metrics = x.shape
    if len(polarity) != n_metrics or len(baselines) != n_metrics:
        raise ValueError("polarity and baselines must each have one entry per metric column")

    per_metric: list[MetricBaseline] = []
    beats = np.zeros((n_tools, n_metrics), dtype=bool)
    observed_floored = np.zeros((n_tools, n_metrics), dtype=bool)

    for k in range(n_metrics):
        base = baselines[k]
        if base is None or polarity[k] == "target_value":
            continue
        col = x[:, k]
        observed = ~np.isnan(col)
        if polarity[k] == "higher_is_better":
            col_beats = observed & (col > base)
        else:
            col_beats = observed & (col < base)
        beats[:, k] = col_beats
        observed_floored[:, k] = observed
        n_obs = int(observed.sum())
        n_beat = int(col_beats.sum())
        per_metric.append(
            MetricBaseline(
                metric=metric_ids[k] if metric_ids is not None else None,
                baseline=float(base),
                polarity=polarity[k],
                n_observed=n_obs,
                n_beating=n_beat,
                fraction_beating=(n_beat / n_obs) if n_obs else float("nan"),
            )
        )

    never = observed_floored.any(axis=1) & ~beats.any(axis=1)
    tools_never = tuple(int(i) for i in np.nonzero(never)[0])
    return RandomBaselineReport(per_metric=tuple(per_metric), tools_never_beating=tools_never)


def noise_floor_separation(
    scores,
    noise_floors: Sequence[float | None],
    ranks: Sequence[int] | None = None,
) -> NoiseFloorReport:
    """Test every pair of tools against the per-metric noise floors.

    For each unordered pair the function takes the largest native-unit score
    difference relative to the floor over the metrics that declare one. The pair
    is separated when that ratio reaches 1 on at least one metric. A pair that is
    comparable (has an observed floored score on both tools for some metric) but
    reaches the floor on no metric is recorded as indistinguishable.

    Parameters
    ----------
    scores
        Array-like of shape ``(n_tools, n_metrics)`` in native units.
    noise_floors
        Length ``n_metrics`` floors in native units, ``None`` (or a
        non-positive value) where the card declares none. Pass
        ``beam.mcda.registry_context(...).noise_floors``.
    ranks
        Optional length ``n_tools`` ranks (1 is best). When given, the report
        names the top two tools and flags whether they are indistinguishable.

    Returns
    -------
    NoiseFloorReport
    """
    x = np.asarray(scores, dtype=float)
    if x.ndim != 2:
        raise ValueError(f"scores must be 2D; got shape {x.shape}")
    noise_floors = tuple(noise_floors)
    n_tools, n_metrics = x.shape
    if len(noise_floors) != n_metrics:
        raise ValueError("noise_floors must have one entry per metric column")

    floored_k = [
        k for k in range(n_metrics) if noise_floors[k] is not None and float(noise_floors[k]) > 0.0
    ]
    top_pair = _top_pair(ranks)
    if not floored_k:
        return NoiseFloorReport((), (), top_pair, False)

    per_pair: list[PairSeparation] = []
    indistinguishable: list[tuple[int, int]] = []
    for a in range(n_tools):
        for b in range(a + 1, n_tools):
            best_metric = -1
            best_ratio = 0.0
            separated = False
            comparable = False
            for k in floored_k:
                da, db = x[a, k], x[b, k]
                if np.isnan(da) or np.isnan(db):
                    continue
                comparable = True
                ratio = abs(float(da) - float(db)) / float(noise_floors[k])
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_metric = k
                if ratio >= 1.0:
                    separated = True
            per_pair.append(
                PairSeparation(
                    a=a,
                    b=b,
                    separated=separated,
                    comparable=comparable,
                    max_metric=best_metric,
                    max_ratio=best_ratio,
                )
            )
            if comparable and not separated:
                indistinguishable.append((a, b))

    indist_set = set(indistinguishable)
    top_indist = top_pair is not None and tuple(sorted(top_pair)) in indist_set
    return NoiseFloorReport(
        per_pair=tuple(per_pair),
        indistinguishable_pairs=tuple(indistinguishable),
        top_pair=top_pair,
        top_pair_indistinguishable=top_indist,
    )


def _top_pair(ranks: Sequence[int] | None) -> tuple[int, int] | None:
    """Indices of the two best-ranked tools, or ``None`` when fewer than two."""
    if ranks is None:
        return None
    order = np.argsort(np.asarray(ranks))
    if len(order) < 2:
        return None
    return int(order[0]), int(order[1])
