"""Validate that every metric card conforms to the metric card JSON Schema.

The schema and the seed cards ship inside the package at beam/schema/ and
beam/metrics/, so this test resolves them through importlib.resources, the
same way beam itself does at runtime. The same schema is also validated from
R in tests/validate_cards.R so the metric card format stays
cross-language-clean from day one.
"""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path

import jsonschema
import pytest
import yaml

SCHEMA_PATH = Path(str(resources.files("beam").joinpath("schema", "metric_card.schema.json")))
METRICS_DIR = Path(str(resources.files("beam").joinpath("metrics")))


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
    assert _discover_cards(), "no metric cards found under beam/metrics/<id>/v*.yaml"


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
        pytest.fail(f"{card_path.parent.name}/{card_path.name} failed validation: {formatted}")


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
