"""Tests for the across-datasets aggregation primitive."""

import numpy as np
import pytest

from beam.mcda import aggregate_across_datasets, reduce_tensor


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


def test_reduce_tensor_per_metric_rules():
    """Two tools, three datasets, two metrics: mean for one, geometric for the other."""
    tensor = np.array(
        [
            [[0.8, 1.0], [0.6, 10.0], [0.4, 100.0]],
            [[0.2, 2.0], [0.4, 2.0], [0.6, 2.0]],
        ]
    )
    out = reduce_tensor(tensor, ["arithmetic_mean", "geometric_mean"])
    np.testing.assert_allclose(out[:, 0], [0.6, 0.4])
    np.testing.assert_allclose(out[:, 1], [10.0, 2.0])


def test_reduce_tensor_is_nan_aware():
    """A missing cell is skipped, so the tool's summary is over observed datasets only."""
    tensor = np.array([[[0.8], [0.4], [np.nan]]]).reshape(1, 3, 1)
    out = reduce_tensor(tensor, ["arithmetic_mean"])
    np.testing.assert_allclose(out, [[0.6]])


def test_reduce_tensor_rejects_tool_with_no_observation():
    tensor = np.full((2, 3, 1), np.nan)
    tensor[0, :, 0] = [0.5, 0.6, 0.7]
    with pytest.raises(ValueError, match="no observed dataset"):
        reduce_tensor(tensor, ["arithmetic_mean"], metric_ids=["ari"])


def test_reduce_tensor_rank_mean_rejected_with_missing_cells():
    tensor = np.array([[[0.8], [np.nan]], [[0.2], [0.5]]]).reshape(2, 2, 1)
    with pytest.raises(NotImplementedError, match="rank_mean"):
        reduce_tensor(tensor, ["rank_mean"])


def test_reduce_tensor_rank_mean_ok_when_complete():
    tensor = np.array([[[0.9], [0.85]], [[0.5], [0.45]], [[0.1], [0.05]]]).reshape(3, 2, 1)
    out = reduce_tensor(tensor, ["rank_mean"])
    np.testing.assert_allclose(out[:, 0], [1.0, 2.0, 3.0])


def test_reduce_tensor_validates_shape_and_rule_count():
    with pytest.raises(ValueError, match="3D"):
        reduce_tensor(np.zeros((2, 3)), ["arithmetic_mean"])
    with pytest.raises(ValueError, match="rules"):
        reduce_tensor(np.zeros((2, 3, 2)), ["arithmetic_mean"])
