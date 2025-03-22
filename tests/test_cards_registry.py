"""Tests for the metric card registry."""

import pytest

from beam.cards import Registry


def test_default_registry_finds_all_seeds():
    reg = Registry()
    ids = reg.list_ids()
    for expected in ("ari", "runtime", "nmi", "peak_memory", "accuracy", "f1_score", "silhouette"):
        assert expected in ids


def test_get_by_id_returns_latest_version():
    reg = Registry()
    card = reg.get("ari")
    assert card.id == "ari"
    assert card.version == "v1"


def test_get_explicit_version():
    reg = Registry()
    card = reg.get("runtime", version="v1")
    assert card.version == "v1"


def test_get_unknown_id_raises():
    reg = Registry()
    with pytest.raises(KeyError):
        reg.get("nonexistent_metric_id")


def test_get_unknown_version_raises():
    reg = Registry()
    with pytest.raises(KeyError):
        reg.get("ari", version="v99")


def test_iter_yields_all_cards():
    reg = Registry()
    cards = list(reg)
    assert len(cards) == len(reg)


def test_list_versions():
    reg = Registry()
    versions = reg.list_versions("ari")
    assert versions == ["v1"]
