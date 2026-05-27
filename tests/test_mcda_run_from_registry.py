"""Tests for the ontology-aware run_from_registry entry point."""

import numpy as np
import pytest

from beam.mcda import IncompatibleScaleError, Result, run_from_registry


def test_returns_a_result():
    scores = np.array([[0.85, 120.0], [0.70, 30.0], [0.60, 90.0]])
    out = run_from_registry(scores, ["ari", "runtime"])
    assert isinstance(out, Result)


def test_records_metric_ids_on_result():
    scores = np.array([[0.85, 120.0], [0.70, 30.0]])
    out = run_from_registry(scores, ["ari", "runtime"])
    assert out.metric_ids == ("ari", "runtime")


def test_records_declared_bounds_on_result():
    """ARI's declared range is [-1, 1] and runtime's lower is 0; both must reach the Result."""
    scores = np.array([[0.85, 120.0], [0.70, 30.0]])
    out = run_from_registry(scores, ["ari", "runtime"])
    assert out.bounds == ((-1, 1), (0, None))


def test_pulls_polarity_from_cards():
    scores = np.array([[0.85, 120.0], [0.70, 30.0]])
    out = run_from_registry(scores, ["ari", "runtime"])
    assert out.polarity == ("higher_is_better", "lower_is_better")


def test_ari_uses_baseline_relative_normalization():
    """ARI declares baseline_relative with a chance baseline of 0 and upper 1, so
    0.85 maps to 0.85, not the 0.925 that a min-max against [-1, 1] would give. A
    chance-level method (ARI 0) maps to 0 rather than to the column midpoint."""
    scores = np.array([[0.85, 120.0], [0.0, 30.0]])
    out = run_from_registry(scores, ["ari", "runtime"])
    assert out.normalization[0] == "baseline_relative"
    assert out.normalized[0, 0] == pytest.approx(0.85)
    assert out.normalized[1, 0] == pytest.approx(0.0)


def test_rejects_out_of_range_value():
    """ARI is declared in [-1, 1]; a value of 2 must be rejected."""
    scores = np.array([[2.0, 30.0], [0.5, 60.0]])
    with pytest.raises(ValueError, match="above declared upper bound"):
        run_from_registry(scores, ["ari", "runtime"])


def test_unknown_metric_raises_keyerror():
    scores = np.array([[0.5, 1.0]])
    with pytest.raises(KeyError):
        run_from_registry(scores, ["ari", "not_a_real_metric"])


def test_forwards_weighting_and_method():
    scores = np.array([[0.85, 120.0], [0.70, 30.0], [0.60, 90.0]])
    out = run_from_registry(scores, ["ari", "runtime"], weights="entropy", method="topsis")
    assert out.weighting == "entropy"
    assert out.method == "topsis"


def test_target_value_metric_runs_through_the_registry_path():
    """A target_value card (calibration_slope) resolves target_relative and ranks.

    The method whose calibration slope sits on the target (1.0) and whose ARI is
    highest must rank first, since target_relative maps the on-target method to 1.
    """
    # columns: calibration_slope (target 1.0), ari (higher is better)
    scores = np.array([[1.0, 0.9], [0.5, 0.6], [1.4, 0.3]])
    out = run_from_registry(scores, ["calibration_slope", "ari"], weights="equal", method="saw")
    assert out.normalization[0] == "target_relative"
    assert out.normalized[0, 0] == 1.0
    assert out.ranks[0] == 1


def test_validation_blocks_incompatible_scale(monkeypatch):
    """If a card declared nominal scale, run_from_registry must raise."""
    from beam.cards import MetricProperties
    from beam.mcda import facade

    def fake_properties(metric_ids, registry=None):
        return [
            MetricProperties(
                id=metric_ids[0],
                polarity="higher_is_better",
                scale_type="nominal",
                range_lower=None,
                range_upper=None,
                allowed_transformations=("rank",),
                recommended_aggregation_across_datasets=None,
            )
        ]

    monkeypatch.setattr(facade, "properties_for", fake_properties)
    with pytest.raises(IncompatibleScaleError):
        run_from_registry(np.array([[0.5], [0.7]]), ["fake_nominal"])
