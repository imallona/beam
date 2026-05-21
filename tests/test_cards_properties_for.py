"""Tests for the properties_for helper and the MetricProperties view."""

import pytest

from beam.cards import MetricProperties, properties_for


def test_returns_metric_properties_in_order():
    out = properties_for(["ari", "runtime"])
    assert all(isinstance(p, MetricProperties) for p in out)
    assert [p.id for p in out] == ["ari", "runtime"]


def test_pulls_polarity_from_card():
    [ari, runtime] = properties_for(["ari", "runtime"])
    assert ari.polarity == "higher_is_better"
    assert runtime.polarity == "lower_is_better"


def test_pulls_scale_type_from_card():
    [ari, runtime, peak] = properties_for(["ari", "runtime", "peak_memory"])
    assert ari.scale_type == "interval"
    assert runtime.scale_type == "ratio"
    assert peak.scale_type == "ratio"


def test_pulls_declared_bounds():
    [ari, runtime] = properties_for(["ari", "runtime"])
    assert ari.range_lower == -1
    assert ari.range_upper == 1
    assert runtime.range_lower == 0
    assert runtime.range_upper is None  # unbounded above


def test_pulls_allowed_transformations():
    [ari, runtime] = properties_for(["ari", "runtime"])
    assert "affine" in ari.allowed_transformations
    assert "affine" in runtime.allowed_transformations  # added in this round
    assert "log" in runtime.allowed_transformations


def test_pulls_recommended_aggregation_across_datasets():
    [ari, runtime, peak] = properties_for(["ari", "runtime", "peak_memory"])
    assert ari.recommended_aggregation_across_datasets == "arithmetic_mean"
    assert runtime.recommended_aggregation_across_datasets == "geometric_mean"
    assert peak.recommended_aggregation_across_datasets == "geometric_mean"


def test_unknown_metric_id_raises():
    with pytest.raises(KeyError):
        properties_for(["definitely_not_a_metric"])
