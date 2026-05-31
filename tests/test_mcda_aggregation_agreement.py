"""Tests for the aggregation-agreement diagnostic."""

import numpy as np
import pytest

from beam.mcda import (
    AggregationAgreementReport,
    aggregation_agreement,
)


def _two_metric_polarity():
    return ["higher_is_better", "lower_is_better"]


def test_dominant_tool_is_unanimous_with_full_agreement():
    """A tool that is best on every metric ranks first under every aggregation,
    so the orderings agree exactly and the consensus top is unanimous."""
    scores = np.array(
        [
            [0.95, 10.0],
            [0.80, 20.0],
            [0.60, 30.0],
            [0.40, 40.0],
        ]
    )
    report = aggregation_agreement(scores, _two_metric_polarity())
    assert isinstance(report, AggregationAgreementReport)
    assert report.methods == ("saw", "topsis", "vikor", "promethee_ii", "comet")
    assert report.top_tool == 0
    assert report.top_is_unanimous
    assert report.consensus_ranks[0] == 1
    assert report.mean_pairwise_tau == pytest.approx(1.0)


def test_tau_matrix_is_symmetric_with_unit_diagonal():
    """The pairwise tau matrix is square, symmetric, and 1 on the diagonal."""
    scores = np.array(
        [
            [0.9, 30.0],
            [0.7, 50.0],
            [0.5, 40.0],
            [0.95, 60.0],
            [0.2, 10.0],
        ]
    )
    report = aggregation_agreement(scores, _two_metric_polarity())
    n = len(report.methods)
    assert report.tau_matrix.shape == (n, n)
    np.testing.assert_allclose(np.diag(report.tau_matrix), np.ones(n))
    np.testing.assert_allclose(report.tau_matrix, report.tau_matrix.T)
    assert -1.0 <= report.mean_pairwise_tau <= 1.0


def test_consensus_matches_mean_of_per_method_ranks():
    """The consensus ranking is the ranking of the per-method mean ranks, and
    the per-tool rank span bounds the consensus rank."""
    rng = np.random.default_rng(0)
    scores = rng.uniform(0.0, 1.0, size=(6, 3))
    polarity = ["higher_is_better"] * 3
    report = aggregation_agreement(scores, polarity)

    stacked = np.vstack([report.ranks_by_method[m] for m in report.methods])
    mean_rank = stacked.mean(axis=0)
    # A smaller mean rank must get a better (smaller) consensus rank.
    order_by_mean = np.argsort(mean_rank, kind="stable")
    assert report.consensus_ranks[order_by_mean[0]] <= report.consensus_ranks[order_by_mean[-1]]

    np.testing.assert_array_equal(report.rank_low, stacked.min(axis=0))
    np.testing.assert_array_equal(report.rank_high, stacked.max(axis=0))
    assert np.all(report.rank_low <= report.rank_high)


def test_fewer_than_two_methods_raises():
    """A single aggregation cannot be compared with anything, so the diagnostic
    refuses rather than reporting a one-method agreement of one."""
    scores = np.array([[0.9, 30.0], [0.7, 50.0], [0.5, 40.0]])
    with pytest.raises(ValueError, match="at least two aggregations"):
        aggregation_agreement(scores, _two_metric_polarity(), methods=["saw"])


def test_constant_input_gives_nan_tau_without_raising():
    """When every tool scores identically, each method ranks them all first;
    tau-b is undefined on a constant ranking, so the mean tau is nan and the
    diagnostic still returns a report instead of raising."""
    scores = np.full((4, 2), 0.5)
    report = aggregation_agreement(scores, _two_metric_polarity())
    assert np.isnan(report.mean_pairwise_tau)
    assert np.all(report.consensus_ranks == 1)
    # Every tool is tied first, so the consensus top is trivially unanimous.
    assert report.top_is_unanimous


def test_methods_that_fail_are_dropped():
    """Restricting to two valid methods reports exactly those two; an unknown
    method name in the list is dropped rather than failing the run."""
    scores = np.array([[0.9, 30.0], [0.7, 50.0], [0.5, 40.0], [0.3, 20.0]])
    report = aggregation_agreement(
        scores, _two_metric_polarity(), methods=["saw", "topsis", "not_a_method"]
    )
    assert report.methods == ("saw", "topsis")
    assert set(report.ranks_by_method) == {"saw", "topsis"}


def test_tool_names_are_carried():
    """Tool labels pass through to the report unchanged."""
    scores = np.array([[0.9, 30.0], [0.7, 50.0], [0.5, 40.0]])
    names = ["a", "b", "c"]
    report = aggregation_agreement(scores, _two_metric_polarity(), tool_names=names)
    assert report.tool_names == ("a", "b", "c")
