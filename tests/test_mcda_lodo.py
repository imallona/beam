"""Tests for the leave-one-dataset-out sensitivity primitive."""

import numpy as np
import pytest

from beam.mcda import DatasetSensitivityReport, leave_one_dataset_out


def _toy_tensor():
    """Three tools, three datasets, two metrics (higher better, lower better)."""
    return np.array(
        [
            [[0.85, 120.0], [0.80, 100.0], [0.90, 110.0]],
            [[0.70, 30.0], [0.65, 40.0], [0.60, 35.0]],
            [[0.60, 90.0], [0.55, 95.0], [0.50, 85.0]],
        ]
    )


_TOY_POLARITY = ["higher_is_better", "lower_is_better"]
_TOY_RULES = ["arithmetic_mean", "arithmetic_mean"]


def test_returns_dataset_sensitivity_report():
    report = leave_one_dataset_out(_toy_tensor(), _TOY_POLARITY, _TOY_RULES)
    assert isinstance(report, DatasetSensitivityReport)


def test_one_run_per_dataset_when_all_evaluable():
    report = leave_one_dataset_out(_toy_tensor(), _TOY_POLARITY, _TOY_RULES)
    assert set(report.leave_one_out.keys()) == {0, 1, 2}
    assert report.evaluated_datasets == (0, 1, 2)
    for r in report.leave_one_out.values():
        assert r.scores.shape == (3, 2)


def test_rank_stability_in_unit_interval():
    report = leave_one_dataset_out(_toy_tensor(), _TOY_POLARITY, _TOY_RULES)
    assert (report.rank_stability >= 0).all()
    assert (report.rank_stability <= 1).all()
    assert report.rank_stability.shape == (3,)


def test_perfect_stability_when_one_tool_dominates_every_dataset():
    """Tool 0 dominates on both metrics in every dataset, so its rank never moves."""
    tensor = np.array(
        [
            [[0.9, 1.0], [0.9, 1.0], [0.9, 1.0]],
            [[0.5, 0.5], [0.5, 0.5], [0.5, 0.5]],
            [[0.1, 0.1], [0.1, 0.1], [0.1, 0.1]],
        ]
    )
    report = leave_one_dataset_out(tensor, ["higher_is_better", "higher_is_better"], _TOY_RULES)
    np.testing.assert_allclose(report.rank_stability, [1.0, 1.0, 1.0])
    assert report.max_rank_shift == 0


def test_most_influential_dataset_is_the_outlier():
    """Datasets 0 and 1 agree; dataset 2 reverses the top two, so its removal moves ranks."""
    tensor = np.array(
        [
            [[0.9], [0.9], [0.1]],
            [[0.6], [0.6], [0.95]],
            [[0.1], [0.1], [0.05]],
        ]
    )
    report = leave_one_dataset_out(
        tensor, ["higher_is_better"], ["arithmetic_mean"], dataset_names=["d0", "d1", "d2"]
    )
    assert report.most_influential_dataset == 2
    assert report.max_rank_shift >= 1


def test_skips_dataset_whose_removal_leaves_a_tool_unobserved():
    """Tool 1 is only observed on dataset 1, so dropping dataset 1 is skipped."""
    tensor = np.array(
        [
            [[0.8], [0.7], [0.6]],
            [[np.nan], [0.5], [np.nan]],
            [[0.2], [0.3], [0.4]],
        ]
    )
    report = leave_one_dataset_out(tensor, ["higher_is_better"], ["arithmetic_mean"])
    assert 1 not in report.evaluated_datasets
    assert set(report.evaluated_datasets) == {0, 2}


def test_dataset_names_preserved():
    report = leave_one_dataset_out(
        _toy_tensor(), _TOY_POLARITY, _TOY_RULES, dataset_names=["a", "b", "c"]
    )
    assert report.dataset_names == ("a", "b", "c")


def test_requires_at_least_two_datasets():
    tensor = np.zeros((3, 1, 2))
    with pytest.raises(ValueError, match="at least 2 datasets"):
        leave_one_dataset_out(tensor, _TOY_POLARITY, _TOY_RULES)


def test_rejects_non_tensor_input():
    with pytest.raises(ValueError, match="3D"):
        leave_one_dataset_out(np.zeros((3, 2)), _TOY_POLARITY, _TOY_RULES)


def test_validates_polarity_and_rule_lengths():
    tensor = _toy_tensor()
    with pytest.raises(ValueError, match="polarity"):
        leave_one_dataset_out(tensor, ["higher_is_better"], _TOY_RULES)
    with pytest.raises(ValueError, match="reduction_rules"):
        leave_one_dataset_out(tensor, _TOY_POLARITY, ["arithmetic_mean"])


def test_forwards_weights_and_method():
    report = leave_one_dataset_out(
        _toy_tensor(), _TOY_POLARITY, _TOY_RULES, weights="entropy", method="topsis"
    )
    assert report.base.weighting == "entropy"
    assert report.base.method == "topsis"
    for r in report.leave_one_out.values():
        assert r.method == "topsis"
