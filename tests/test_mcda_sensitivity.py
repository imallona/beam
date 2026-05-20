"""Tests for the leave-one-metric-out sensitivity primitive."""

import numpy as np
import pytest

from beam.mcda import SensitivityReport, leave_one_metric_out


def _toy_scores():
    return np.array(
        [
            [0.85, 120.0],
            [0.70, 30.0],
            [0.60, 90.0],
        ]
    )


_TOY_POLARITY = ["higher_is_better", "lower_is_better"]


def test_returns_sensitivity_report():
    report = leave_one_metric_out(_toy_scores(), _TOY_POLARITY)
    assert isinstance(report, SensitivityReport)


def test_leave_one_out_dict_has_one_entry_per_metric():
    report = leave_one_metric_out(_toy_scores(), _TOY_POLARITY)
    assert set(report.leave_one_out.keys()) == {0, 1}
    for r in report.leave_one_out.values():
        assert r.scores.shape == (3, 1)
        assert r.ranks.shape == (3,)


def test_rank_stability_in_unit_interval():
    report = leave_one_metric_out(_toy_scores(), _TOY_POLARITY)
    assert (report.rank_stability >= 0).all()
    assert (report.rank_stability <= 1).all()
    assert report.rank_stability.shape == (3,)


def test_removing_constant_metric_preserves_base_ranks():
    scores = np.array(
        [
            [0.9, 0.5],
            [0.5, 0.5],
            [0.1, 0.5],
        ]
    )
    report = leave_one_metric_out(scores, ["higher_is_better", "higher_is_better"])
    np.testing.assert_array_equal(report.leave_one_out[1].ranks, report.base.ranks)


def test_most_influential_metric_is_the_one_that_swings_ranks():
    scores = np.array(
        [
            [0.5, 0.9],
            [0.5, 0.7],
            [0.5, 0.1],
        ]
    )
    report = leave_one_metric_out(scores, ["higher_is_better", "higher_is_better"])
    assert report.most_influential_metric == 1
    assert report.max_rank_shift >= 1


def test_perfect_stability_when_two_metrics_agree():
    """If two metrics induce the same ranking, removing either keeps the ranks."""
    scores = np.array(
        [
            [0.9, 0.8],
            [0.6, 0.5],
            [0.2, 0.1],
        ]
    )
    report = leave_one_metric_out(scores, ["higher_is_better", "higher_is_better"])
    np.testing.assert_allclose(report.rank_stability, [1.0, 1.0, 1.0])
    assert report.max_rank_shift == 0


def test_requires_at_least_two_metrics():
    with pytest.raises(ValueError, match="at least 2 metrics"):
        leave_one_metric_out(np.array([[0.5], [0.7]]), ["higher_is_better"])


def test_rejects_one_dimensional_scores():
    with pytest.raises(ValueError, match="2D"):
        leave_one_metric_out(np.array([0.5, 0.7]), ["higher_is_better"])


def test_validates_polarity_length():
    with pytest.raises(ValueError, match="polarity"):
        leave_one_metric_out(np.array([[0.5, 0.7]]), ["higher_is_better"])


def test_validates_metric_ids_length():
    with pytest.raises(ValueError, match="metric_ids"):
        leave_one_metric_out(
            _toy_scores(),
            _TOY_POLARITY,
            metric_ids=["a", "b", "c"],
        )


def test_metric_ids_preserved_in_report():
    report = leave_one_metric_out(
        _toy_scores(),
        _TOY_POLARITY,
        metric_ids=["ari", "runtime"],
    )
    assert report.metric_ids == ("ari", "runtime")


def test_metric_ids_none_when_not_provided():
    report = leave_one_metric_out(_toy_scores(), _TOY_POLARITY)
    assert report.metric_ids is None


def test_forwards_weights_and_method_to_run():
    report = leave_one_metric_out(
        _toy_scores(),
        _TOY_POLARITY,
        weights="entropy",
        method="topsis",
    )
    assert report.base.weighting == "entropy"
    assert report.base.method == "topsis"
    for r in report.leave_one_out.values():
        assert r.weighting == "entropy"
        assert r.method == "topsis"
