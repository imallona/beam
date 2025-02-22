"""Validate that every metric card in metrics/ conforms to the metric card JSON Schema.

Runs in Python via jsonschema. The same schema is also validated from R in
tests/validate_cards.R so the metric card format stays cross-language-clean
from day one.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "schema" / "metric_card.schema.json"
METRICS_DIR = REPO_ROOT / "metrics"


def _load_schema() -> dict:
    with SCHEMA_PATH.open() as f:
        return json.load(f)


def _discover_cards() -> list[Path]:
    return sorted(METRICS_DIR.glob("*/v*.yaml"))


@pytest.fixture(scope="module")
def schema() -> dict:
    return _load_schema()


@pytest.fixture(scope="module")
def validator(schema: dict) -> jsonschema.Draft202012Validator:
    return jsonschema.Draft202012Validator(schema)


def test_schema_itself_is_valid() -> None:
    jsonschema.Draft202012Validator.check_schema(_load_schema())


def test_at_least_one_card_exists() -> None:
    assert _discover_cards(), "no metric cards found under metrics/<id>/v*.yaml"


@pytest.mark.parametrize(
    "card_path",
    _discover_cards(),
    ids=lambda p: f"{p.parent.name}/{p.name}",
)
def test_card_validates(card_path: Path, validator: jsonschema.Draft202012Validator) -> None:
    with card_path.open() as f:
        card = yaml.safe_load(f)
    errors = sorted(validator.iter_errors(card), key=lambda e: list(e.path))
    if errors:
        formatted = "; ".join(
            f"{'.'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errors
        )
        pytest.fail(f"{card_path.relative_to(REPO_ROOT)} failed validation: {formatted}")


@pytest.mark.parametrize(
    "card_path",
    _discover_cards(),
    ids=lambda p: f"{p.parent.name}/{p.name}",
)
def test_card_id_matches_directory(card_path: Path) -> None:
    with card_path.open() as f:
        card = yaml.safe_load(f)
    assert card["id"] == card_path.parent.name, (
        f"id field {card['id']!r} does not match directory {card_path.parent.name!r}"
    )


@pytest.mark.parametrize(
    "card_path",
    _discover_cards(),
    ids=lambda p: f"{p.parent.name}/{p.name}",
)
def test_card_version_matches_filename(card_path: Path) -> None:
    with card_path.open() as f:
        card = yaml.safe_load(f)
    assert card["version"] == card_path.stem, (
        f"version field {card['version']!r} does not match filename stem {card_path.stem!r}"
    )
