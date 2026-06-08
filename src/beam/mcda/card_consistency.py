"""Audit a metric card's declared numeric claims against the observed scores.

A metric card is a contract. It declares a value range, a chance baseline, an
ideal target, and a noise floor, and the MCDA pipeline trusts every one of them:
the range bounds the normalization, the baseline anchors ``baseline_relative``
scaling and the beats-chance check, the target drives ``target_relative``
scaling, and the noise floor sets which method differences are interpretable. If
the score matrix contradicts a declared value, every downstream step inherits the
error silently. The classic case is a unit mismatch: a metric reported as a
percentage against a card that declares the ``[0, 1]`` fraction range. The column
is still numeric and interval, so it passes schema validation and the
scale-versus-method check, and then it distorts the min-max normalization for
that metric and the weighting that rests on it.

``card_data_consistency`` reads the raw scores against the card values before any
normalization and reports where they disagree. It separates hard contradictions
from data-dependent observations. A contradiction is a violation: a score outside
the declared range, a baseline or target outside that range, a non-positive noise
floor, or a malformed range where the lower bound exceeds the upper. Each is a
card bug or a data bug that needs fixing. An observation is a note: a metric that
is constant on this data, a noise floor wider than the whole observed spread, or
a metric with no observations at all. A note is true of this particular score
matrix, not necessarily wrong, but worth surfacing before the ranking is read.

This is the card-facing companion to ``beats_random_baseline`` and
``noise_floor_separation``, which read the same raw scores to compare the methods
to each other. Here the comparison is the card against its own data.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

VIOLATION = "violation"
NOTE = "note"


@dataclass(frozen=True)
class ConsistencyFinding:
    """One disagreement between a metric card and its observed scores.

    Attributes
    ----------
    metric
        Metric id, or ``None`` when the matrix carried no ids.
    code
        Machine-readable label for the kind of finding: ``out_of_range``,
        ``baseline_out_of_range``, ``target_out_of_range``,
        ``nonpositive_noise_floor``, ``malformed_range``,
        ``noise_floor_exceeds_spread``, ``degenerate`` or ``no_observations``.
    severity
        ``"violation"`` for a hard card-or-data contradiction, ``"note"`` for a
        data-dependent observation.
    message
        Plain-language description naming the declared value, the observed value,
        and what disagrees.
    """

    metric: str | None
    code: str
    severity: str
    message: str


@dataclass(frozen=True)
class MetricConsistency:
    """The card-versus-data audit for one metric.

    Attributes
    ----------
    metric
        Metric id, or ``None`` when the matrix carried no ids.
    n_observed
        Tools with a non-NaN score on this metric.
    observed_min, observed_max
        The smallest and largest observed score in native units, both ``nan``
        when nothing is observed.
    declared_lower, declared_upper
        The card's range bounds, ``None`` where the card leaves a side open.
    n_below_range, n_above_range
        Tools whose observed score falls below ``declared_lower`` or above
        ``declared_upper`` by more than the tolerance.
    findings
        The findings raised for this metric, possibly empty.
    """

    metric: str | None
    n_observed: int
    observed_min: float
    observed_max: float
    declared_lower: float | None
    declared_upper: float | None
    n_below_range: int
    n_above_range: int
    findings: tuple[ConsistencyFinding, ...]


@dataclass(frozen=True)
class CardDataConsistencyReport:
    """The card-versus-data audit over every metric in a score matrix.

    ``per_metric`` holds one record per metric column in order. ``findings`` is
    every finding flattened across the metrics, in column order. The convenience
    views split them by severity and give the headline ``ok`` flag.
    """

    per_metric: tuple[MetricConsistency, ...]
    findings: tuple[ConsistencyFinding, ...]

    @property
    def violations(self) -> tuple[ConsistencyFinding, ...]:
        """The findings that are hard card-or-data contradictions."""
        return tuple(f for f in self.findings if f.severity == VIOLATION)

    @property
    def notes(self) -> tuple[ConsistencyFinding, ...]:
        """The findings that are data-dependent observations, not contradictions."""
        return tuple(f for f in self.findings if f.severity == NOTE)

    @property
    def ok(self) -> bool:
        """True when no metric contradicts its card (notes do not count)."""
        return not self.violations


def card_data_consistency(
    scores,
    polarity: Sequence[str],
    bounds: Sequence[tuple[float | None, float | None]],
    baselines: Sequence[float | None] | None = None,
    targets: Sequence[float | None] | None = None,
    noise_floors: Sequence[float | None] | None = None,
    metric_ids: Sequence[str] | None = None,
    range_tol: float = 0.0,
) -> CardDataConsistencyReport:
    """Audit each metric card's declared numeric claims against the raw scores.

    Reads the native-unit score matrix against the values the cards declare,
    before any normalization, and reports where they disagree. Pass the card
    values from a resolved context: ``context.bounds``, ``context.baselines``,
    ``context.targets`` and ``context.noise_floors`` of a
    ``beam.mcda.registry_context`` line up with ``context.polarity`` and the
    matrix columns.

    The checks per metric:

    - ``malformed_range`` (violation): the declared lower bound exceeds the upper.
    - ``out_of_range`` (violation): an observed score falls below the lower bound
      or above the upper bound by more than ``range_tol``.
    - ``baseline_out_of_range`` (violation): a declared chance baseline lies
      outside the declared range. A ``target_value`` metric has no chance level,
      so its baseline, if any, is not checked.
    - ``target_out_of_range`` (violation): a declared target lies outside the
      declared range.
    - ``nonpositive_noise_floor`` (violation): a declared noise floor is zero or
      negative, which is not a width in native units.
    - ``noise_floor_exceeds_spread`` (note): a positive noise floor is at least
      as large as the whole observed spread, so the metric separates no pair of
      tools on this data.
    - ``degenerate`` (note): the metric is constant across the observed tools, so
      it carries no ranking signal here.
    - ``no_observations`` (note): every cell of the metric is NaN.

    Parameters
    ----------
    scores
        Array-like of shape ``(n_tools, n_metrics)`` in native units. Missing
        cells are NaN and excluded from the per-metric statistics.
    polarity
        Length ``n_metrics`` polarity strings. Only ``target_value`` is read
        specially, to skip the baseline check; the range, target and noise-floor
        checks do not depend on direction.
    bounds
        Length ``n_metrics`` ``(lower, upper)`` pairs from the cards, either side
        ``None`` where the card declares no bound.
    baselines
        Optional length ``n_metrics`` chance scores, ``None`` where the card
        declares none. Defaults to all ``None``.
    targets
        Optional length ``n_metrics`` target values, ``None`` where the card
        declares none. Defaults to all ``None``.
    noise_floors
        Optional length ``n_metrics`` noise floors in native units, ``None``
        where the card declares none. Defaults to all ``None``.
    metric_ids
        Optional length ``n_metrics`` labels carried into the findings.
    range_tol
        Non-negative absolute tolerance on the range edges, to absorb float
        round-off at an exact boundary. Default 0.0.

    Returns
    -------
    CardDataConsistencyReport

    Raises
    ------
    ValueError
        If ``scores`` is not 2D, a per-metric sequence has the wrong length, or
        ``range_tol`` is negative.

    Examples
    --------
    >>> import numpy as np
    >>> from beam.mcda import card_data_consistency
    >>> scores = np.array([[0.4, 5.0], [0.9, 12.0]])  # second metric as percent
    >>> report = card_data_consistency(
    ...     scores,
    ...     ["higher_is_better", "higher_is_better"],
    ...     [(0.0, 1.0), (0.0, 1.0)],
    ...     metric_ids=["ari", "accuracy"],
    ... )
    >>> report.ok
    False
    >>> [f.code for f in report.violations]
    ['out_of_range']
    """
    x = np.asarray(scores, dtype=float)
    if x.ndim != 2:
        raise ValueError(f"scores must be 2D (tools, metrics); got shape {x.shape}")
    _, n_metrics = x.shape

    polarity = tuple(polarity)
    bounds = [tuple(b) for b in bounds]
    if len(polarity) != n_metrics:
        raise ValueError(f"polarity has {len(polarity)} entries but scores has {n_metrics} columns")
    if len(bounds) != n_metrics:
        raise ValueError(f"bounds has {len(bounds)} entries but scores has {n_metrics} columns")

    baselines = tuple(baselines) if baselines is not None else (None,) * n_metrics
    targets = tuple(targets) if targets is not None else (None,) * n_metrics
    noise_floors = tuple(noise_floors) if noise_floors is not None else (None,) * n_metrics
    for seq_name, seq in (
        ("baselines", baselines),
        ("targets", targets),
        ("noise_floors", noise_floors),
    ):
        if len(seq) != n_metrics:
            raise ValueError(
                f"{seq_name} has {len(seq)} entries but scores has {n_metrics} columns"
            )
    if range_tol < 0:
        raise ValueError(f"range_tol must be non-negative; got {range_tol}")

    ids = None if metric_ids is None else list(metric_ids)
    if ids is not None and len(ids) != n_metrics:
        raise ValueError(f"metric_ids has {len(ids)} entries but scores has {n_metrics} columns")

    per_metric: list[MetricConsistency] = []
    all_findings: list[ConsistencyFinding] = []

    for k in range(n_metrics):
        name = ids[k] if ids is not None else None
        col = x[:, k]
        observed = col[~np.isnan(col)]
        n_obs = int(observed.size)
        obs_min = float(observed.min()) if n_obs else float("nan")
        obs_max = float(observed.max()) if n_obs else float("nan")
        lower, upper = bounds[k]
        lower = None if lower is None else float(lower)
        upper = None if upper is None else float(upper)

        findings: list[ConsistencyFinding] = []

        def add(code, severity, message, _findings=findings, _metric=name):
            _findings.append(
                ConsistencyFinding(metric=_metric, code=code, severity=severity, message=message)
            )

        label = name if name is not None else f"metric_{k}"

        if lower is not None and upper is not None and lower > upper:
            add(
                "malformed_range",
                VIOLATION,
                f"{label}: declared range lower {lower:g} exceeds upper {upper:g}",
            )

        n_below = 0
        n_above = 0
        if n_obs:
            if lower is not None:
                below = observed < lower - range_tol
                n_below = int(below.sum())
            if upper is not None:
                above = observed > upper + range_tol
                n_above = int(above.sum())
            if n_below or n_above:
                parts = []
                if n_below:
                    parts.append(f"{n_below} below {lower:g} (min {obs_min:g})")
                if n_above:
                    parts.append(f"{n_above} above {upper:g} (max {obs_max:g})")
                add(
                    "out_of_range",
                    VIOLATION,
                    f"{label}: {n_below + n_above} of {n_obs} observed scores outside the "
                    f"declared range, " + " and ".join(parts),
                )

        base = baselines[k]
        if base is not None and polarity[k] != "target_value":
            base = float(base)
            if (lower is not None and base < lower) or (upper is not None and base > upper):
                add(
                    "baseline_out_of_range",
                    VIOLATION,
                    f"{label}: declared chance baseline {base:g} is outside the declared range "
                    f"[{_fmt(lower)}, {_fmt(upper)}]",
                )

        target = targets[k]
        if target is not None:
            target = float(target)
            if (lower is not None and target < lower) or (upper is not None and target > upper):
                add(
                    "target_out_of_range",
                    VIOLATION,
                    f"{label}: declared target {target:g} is outside the declared range "
                    f"[{_fmt(lower)}, {_fmt(upper)}]",
                )

        floor = noise_floors[k]
        if floor is not None:
            floor = float(floor)
            if floor <= 0:
                add(
                    "nonpositive_noise_floor",
                    VIOLATION,
                    f"{label}: declared noise floor {floor:g} is not a positive width",
                )
            elif n_obs >= 2:
                spread = obs_max - obs_min
                if spread > 0 and floor >= spread:
                    add(
                        "noise_floor_exceeds_spread",
                        NOTE,
                        f"{label}: noise floor {floor:g} is at least the whole observed spread "
                        f"{spread:g}, so the metric separates no pair of tools on this data",
                    )

        if n_obs == 0:
            add("no_observations", NOTE, f"{label}: every score is missing")
        elif n_obs >= 2 and obs_max == obs_min:
            add(
                "degenerate",
                NOTE,
                f"{label}: constant at {obs_min:g} across the observed tools, no ranking signal",
            )

        per_metric.append(
            MetricConsistency(
                metric=name,
                n_observed=n_obs,
                observed_min=obs_min,
                observed_max=obs_max,
                declared_lower=lower,
                declared_upper=upper,
                n_below_range=n_below,
                n_above_range=n_above,
                findings=tuple(findings),
            )
        )
        all_findings.extend(findings)

    return CardDataConsistencyReport(
        per_metric=tuple(per_metric),
        findings=tuple(all_findings),
    )


def _fmt(value: float | None) -> str:
    """Format a bound, showing an open side as a minus or plus infinity sign."""
    if value is None:
        return "open"
    return f"{value:g}"
