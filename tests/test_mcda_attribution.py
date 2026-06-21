"""Tests for the attribution synthesis budget.

The budget rules are deterministic and pure Python (no R), so they are checked
directly here: every setting's three shares are non-negative and sum to one, the
weighting and aggregation map to analyst choice, the dataset to data, and the
same-data contrast carries no data share.
"""

import numpy as np
import pytest

from beam.mcda import (
    attribution_synthesis,
    rank_sensitivity,
    setting_from_rank_sensitivity,
    setting_from_same_data_contrast,
    setting_from_source_variance,
)


def _shares(setting):
    return (setting.analyst_choice_share, setting.dataset_share, setting.benchmarker_share)


def test_rank_sensitivity_setting_sums_to_one():
    """A tensor decomposition gives analyst plus dataset shares that sum to one."""
    rng = np.random.default_rng(0)
    scores = rng.random((6, 4, 3))
    report = rank_sensitivity(
        scores,
        ["higher_is_better", "lower_is_better", "higher_is_better"],
        missing="worst",
    )
    setting = setting_from_rank_sensitivity(report, "duo")
    a, d, b = _shares(setting)
    assert b == 0.0
    assert a >= 0.0 and d >= 0.0
    assert a + d + b == pytest.approx(1.0)


def test_rank_sensitivity_setting_maps_dataset_to_dataset_share():
    """When the dataset drives the ranking, the dataset share is the largest."""
    # Tool order flips entirely between the two datasets, so the dataset is the
    # only thing that moves the ranking.
    scores = np.zeros((3, 2, 2))
    scores[:, 0, :] = [[0.9, 0.9], [0.5, 0.5], [0.1, 0.1]]
    scores[:, 1, :] = [[0.1, 0.1], [0.5, 0.5], [0.9, 0.9]]
    report = rank_sensitivity(scores, ["higher_is_better", "higher_is_better"], missing="worst")
    setting = setting_from_rank_sensitivity(report, "flip")
    a, d, _ = _shares(setting)
    assert d > a


def test_same_data_contrast_has_no_dataset_share():
    """A same-data contrast holds the datasets fixed, so its dataset share is zero."""
    setting = setting_from_same_data_contrast(
        {"pipeline_a": [1, 2, 3, 4, 5], "pipeline_b": [1, 3, 2, 5, 4]}, "contrast"
    )
    a, d, b = _shares(setting)
    assert d == 0.0
    assert a + b == pytest.approx(1.0)
    # The pipelines agree on the first method but reorder the rest, so the
    # method-by-pipeline reordering (analyst choice) carries the budget.
    assert a > b


def test_same_data_contrast_identical_orders_are_undefined():
    """Two identical orderings have no rank movement, so the shares are nan."""
    setting = setting_from_same_data_contrast(
        {"a": [1, 2, 3], "b": [1, 2, 3]}, "identical"
    )
    a, d, b = _shares(setting)
    assert np.isnan(a) and np.isnan(d) and np.isnan(b)


def test_same_data_contrast_needs_two_sources():
    with pytest.raises(ValueError, match="two sources"):
        setting_from_same_data_contrast({"only": [1, 2, 3]}, "one")


class _FakeSourceVariance:
    """A stand-in source-variance report with a fixed method-by-benchmark share."""

    def __init__(self, method_benchmark_share):
        self._share = method_benchmark_share

    @property
    def method_benchmark_share(self):
        return self._share


def test_source_variance_setting_splits_the_remaining_budget():
    """With analyst share zero, benchmarker and dataset split per the model ratio."""
    setting = setting_from_source_variance(_FakeSourceVariance(0.42), 0.0, "pooled")
    a, d, b = _shares(setting)
    assert a == 0.0
    assert b == pytest.approx(0.42)
    assert d == pytest.approx(0.58)
    assert a + d + b == pytest.approx(1.0)


def test_source_variance_setting_honours_analyst_share():
    """A non-zero analyst share scales the dataset and benchmarker into the rest."""
    setting = setting_from_source_variance(_FakeSourceVariance(0.5), 0.2, "pooled")
    a, d, b = _shares(setting)
    assert a == pytest.approx(0.2)
    assert b == pytest.approx(0.8 * 0.5)
    assert d == pytest.approx(0.8 * 0.5)
    assert a + d + b == pytest.approx(1.0)


def test_attribution_synthesis_preserves_order_and_rejects_empty():
    s1 = setting_from_same_data_contrast({"a": [1, 2], "b": [2, 1]}, "first")
    s2 = setting_from_source_variance(_FakeSourceVariance(0.3), 0.0, "second")
    report = attribution_synthesis([s1, s2])
    assert [s.label for s in report.settings] == ["first", "second"]
    with pytest.raises(ValueError, match="at least one setting"):
        attribution_synthesis([])
