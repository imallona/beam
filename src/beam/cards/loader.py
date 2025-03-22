"""Load a metric card from disk, validate it, and return a MetricCard."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from .model import MetricCard

_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "schema" / "metric_card.schema.json"
_SCHEMA: dict | None = None


def _schema() -> dict:
    global _SCHEMA
    if _SCHEMA is None:
        with _SCHEMA_PATH.open() as f:
            _SCHEMA = json.load(f)
    return _SCHEMA


def load_card(path: str | Path) -> MetricCard:
    """Read a metric card YAML, validate against the schema, return a MetricCard."""
    path = Path(path)
    with path.open() as f:
        raw = yaml.safe_load(f)
    _validate(raw, source=path)
    return _build(raw)


def _validate(raw: dict[str, Any], source: Path) -> None:
    validator = jsonschema.Draft202012Validator(_schema())
    errors = sorted(validator.iter_errors(raw), key=lambda e: list(e.path))
    if errors:
        formatted = "; ".join(
            f"{'.'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errors
        )
        raise ValueError(f"{source} failed metric card validation: {formatted}")


def _build(raw: dict[str, Any]) -> MetricCard:
    return MetricCard(
        id=raw["id"],
        version=raw["version"],
        name=raw["name"],
        description=raw["description"],
        metric_kind=raw["metric_kind"],
        measurand=raw["measurand"],
        task=tuple(raw["task"]),
        requires_ground_truth=raw["requires_ground_truth"],
        output=raw["output"],
        semantics=raw["semantics"],
        comparability=raw["comparability"],
        implementations=tuple(raw["implementations"]),
        examples=tuple(raw["examples"]),
        provenance=raw["provenance"],
        aliases=tuple(raw.get("aliases", [])),
        citations=tuple(raw.get("citations", [])),
        ground_truth=raw.get("ground_truth"),
        inputs=tuple(raw.get("inputs", [])),
        mappings=raw.get("mappings", {}),
        raw=raw,
    )
