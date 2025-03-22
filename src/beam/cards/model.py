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
