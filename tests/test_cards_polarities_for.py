"""Tests for the beam.cards.polarities_for helper."""

import pytest

from beam.cards import Registry, polarities_for


def test_polarities_for_default_registry():
    pols = polarities_for(["ari", "runtime"])
    assert pols == ["higher_is_better", "lower_is_better"]


def test_polarities_for_preserves_order():
    pols = polarities_for(["runtime", "ari"])
    assert pols == ["lower_is_better", "higher_is_better"]


def test_polarities_for_with_explicit_registry():
    reg = Registry()
    pols = polarities_for(["accuracy", "peak_memory"], registry=reg)
    assert pols == ["higher_is_better", "lower_is_better"]


def test_polarities_for_unknown_id_raises():
    with pytest.raises(KeyError):
        polarities_for(["ari", "nonexistent_metric_id"])


def test_polarities_for_empty_list():
    assert polarities_for([]) == []
