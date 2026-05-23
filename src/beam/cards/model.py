"""Dataclass representation of a metric card."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MetricCard:
    """A loaded and validated metric card.

    The fields mirror the JSON Schema in schema/metric_card.schema.json.
    Nested structures (semantics, comparability, output, etc.) are kept
    as plain dicts, with typed accessors for the most-used fields.
    """

    id: str
    version: str
    name: str
    description: str
    metric_kind: str
    measurand: str
    task: tuple[str, ...]
    requires_ground_truth: bool
    output: dict[str, Any]
    semantics: dict[str, Any]
    comparability: dict[str, Any]
    implementations: tuple[dict[str, Any], ...]
    examples: tuple[dict[str, Any], ...]
    provenance: dict[str, Any]

    aliases: tuple[str, ...] = ()
    citations: tuple[dict[str, Any], ...] = ()
    ground_truth: dict[str, Any] | None = None
    inputs: tuple[dict[str, Any], ...] = ()
    mappings: dict[str, str] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def scale_type(self) -> str:
        return self.semantics["scale_type"]

    @property
    def polarity(self) -> str:
        return self.semantics["polarity"]

    @property
    def is_higher_better(self) -> bool:
        return self.polarity == "higher_is_better"

    @property
    def is_lower_better(self) -> bool:
        return self.polarity == "lower_is_better"

    @property
    def range_lower(self) -> float | None:
        return self.semantics.get("range", {}).get("lower")

    @property
    def range_upper(self) -> float | None:
        return self.semantics.get("range", {}).get("upper")

    @property
    def allowed_transformations(self) -> tuple[str, ...]:
        return tuple(self.semantics.get("allowed_transformations", []))

    @property
    def recommended_aggregation_across_datasets(self) -> str | None:
        """Recommended way to aggregate this metric's scores across datasets.

        Set on the card under comparability.recommended_aggregation_across_datasets.
        One of arithmetic_mean, geometric_mean, median, rank_mean, or None if
        unspecified.
        """
        return self.comparability.get("recommended_aggregation_across_datasets")

    @property
    def recommended_normalization(self) -> str | None:
        """Recommended way to rescale this metric to [0, 1] before weighting.

        Set on the card under comparability.recommended_normalization. One of
        min_max, log_min_max, rank, zscore, baseline_relative, or None if
        unspecified (the pipeline then falls back to min_max).
        """
        return self.comparability.get("recommended_normalization")

    @property
    def score_of_random_baseline(self) -> float | None:
        """Score a chance-level method reaches, if the card declares one.

        Set under semantics.score_of_random_baseline. Consumed by the
        baseline_relative normalization.
        """
        return self.semantics.get("score_of_random_baseline")


@dataclass(frozen=True)
class MetricProperties:
    """A small read-only view onto the metric card fields that the MCDA pipeline consumes.

    Returned by ``beam.cards.properties_for`` so that downstream code can
    work against a uniform structure rather than reaching into the nested
    semantics dict of a ``MetricCard``.
    """

    id: str
    polarity: str
    scale_type: str
    range_lower: float | None
    range_upper: float | None
    allowed_transformations: tuple[str, ...]
    recommended_aggregation_across_datasets: str | None
    recommended_normalization: str | None = None
    score_of_random_baseline: float | None = None
