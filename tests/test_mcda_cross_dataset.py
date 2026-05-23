"""Tests for the across-datasets aggregation primitive."""

import numpy as np
import pytest

from beam.mcda import aggregate_across_datasets


def test_arithmetic_mean_matches_numpy():
    scores = np.array(
        [
            [1.0, 2.0, 3.0],
            [4.0, 5.0, 6.0],
        ]
    )
    np.testing.assert_allclose(aggregate_across_datasets(scores, "arithmetic_mean"), [2.0, 5.0])


def test_geometric_mean_on_runtime_like_values():
    """Geometric mean of [1, 10, 100] is 10; arithmetic mean would be 37."""
    scores = np.array([[1.0, 10.0, 100.0]])
    out = aggregate_across_datasets(scores, "geometric_mean")
    np.testing.assert_allclose(out, [10.0])


def test_geometric_mean_rejects_non_positive():
    scores = np.array([[1.0, 0.0, 100.0]])
    with pytest.raises(ValueError, match="positive"):
        aggregate_across_datasets(scores, "geometric_mean")


def test_median_outlier_robustness():
    """Single huge dataset value should not pull the median."""
    scores = np.array([[1.0, 2.0, 3.0, 1000.0]])
    np.testing.assert_allclose(aggregate_across_datasets(scores, "median"), [2.5])


def test_rank_mean_uses_within_dataset_ranks():
    """Tool 0 is best on both datasets, tool 1 second on both, tool 2 last on both."""
    scores = np.array(
        [
            [0.9, 0.85],
            [0.5, 0.45],
            [0.1, 0.05],
        ]
    )
    out = aggregate_across_datasets(scores, "rank_mean")
    np.testing.assert_allclose(out, [1.0, 2.0, 3.0])


def test_rejects_unknown_rule():
    with pytest.raises(ValueError, match="unknown rule"):
        aggregate_across_datasets(np.array([[1.0, 2.0]]), "harmonic_mean")


def test_rejects_one_dimensional_input():
    with pytest.raises(ValueError, match="2D"):
        aggregate_across_datasets(np.array([1.0, 2.0]), "arithmetic_mean")
