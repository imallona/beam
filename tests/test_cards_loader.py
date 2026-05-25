"""Tests for the metric card loader."""

from importlib import resources
from pathlib import Path

import pytest

from beam.cards import load_card

METRICS_DIR = Path(str(resources.files("beam").joinpath("metrics")))


def _all_card_paths():
    return sorted(METRICS_DIR.glob("*/v*.yaml"))


@pytest.mark.parametrize(
    "card_path",
    _all_card_paths(),
    ids=lambda p: f"{p.parent.name}/{p.name}",
)
def test_card_loads_and_round_trips(card_path):
    card = load_card(card_path)
    assert card.id == card_path.parent.name
    assert card.version == card_path.stem
    assert card.raw["id"] == card.id


def test_ari_card_semantics():
    card = load_card(METRICS_DIR / "ari" / "v1.yaml")
    assert card.scale_type == "interval"
    assert card.polarity == "higher_is_better"
    assert card.is_higher_better
    assert not card.is_lower_better
    assert card.range_lower == -1
    assert card.range_upper == 1
    assert card.requires_ground_truth
    assert "affine" in card.allowed_transformations


def test_runtime_card_semantics():
    card = load_card(METRICS_DIR / "runtime" / "v1.yaml")
    assert card.scale_type == "ratio"
    assert card.polarity == "lower_is_better"
    assert card.is_lower_better
    assert card.range_lower == 0
    assert card.range_upper is None
    assert not card.requires_ground_truth
    assert card.metric_kind == "measured"
