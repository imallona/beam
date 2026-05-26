"""The seed registry and schema must resolve as package resources.

beam is installable as a wheel, which has no repo root, so the
card loader and the registry must find metrics/ and schema/ inside the beam
package rather than through a path relative to the source tree. These tests
assert that the resolved locations live under the package and that loading
works through them, which is what breaks first if the packaging regresses.
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path

from beam.cards import Registry, load_card
from beam.cards.loader import _schema


def _package_root() -> Path:
    return Path(str(resources.files("beam")))


def test_default_registry_dir_is_inside_the_package() -> None:
    reg = Registry()
    assert reg.metrics_dir == _package_root() / "metrics"
    assert reg.metrics_dir.is_dir()


def test_registry_loads_cards_from_package_resources() -> None:
    reg = Registry()
    assert "ari" in reg.list_ids()
    assert "runtime" in reg.list_ids()
    assert len(reg) >= 1


def test_schema_resolves_from_package_resources() -> None:
    schema_file = _package_root() / "schema" / "metric_card.schema.json"
    assert schema_file.is_file()
    schema = _schema()
    assert schema["$schema"].startswith("https://json-schema.org/")


def test_every_packaged_card_loads_and_validates() -> None:
    metrics_dir = _package_root() / "metrics"
    card_paths = sorted(metrics_dir.glob("*/v*.yaml"))
    assert card_paths, "no packaged cards found under beam/metrics/<id>/v*.yaml"
    for path in card_paths:
        card = load_card(path)
        assert card.id == path.parent.name
