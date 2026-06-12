"""Tests for the normalization-agreement diagnostic."""

import numpy as np
import pytest

from beam.mcda import (
    NormalizationAgreementReport,
    normalization_agreement,
)


def _two_metric_polarity():
    return ["higher_is_better", "lower_is_better"]


def test_dominant_tool_is_unanimous_with_full_agreement():
    """A tool best on every metric ranks first under every normalization, so the
    orderings agree exactly and the consensus top is unanimous."""
    scores = np.array(
        [
            [0.95, 10.0],
            [0.80, 20.0],
            [0.60, 30.0],
            [0.40, 40.0],
        ]
    )
    report = normalization_agreement(scores, _two_metric_polarity())
    assert isinstance(report, NormalizationAgreementReport)
    assert report.labels == ("min_max", "log_min_max", "rank", "zscore")
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
    report = normalization_agreement(scores, _two_metric_polarity())
    n = len(report.labels)
    assert report.tau_matrix.shape == (n, n)
    np.testing.assert_allclose(np.diag(report.tau_matrix), np.ones(n))
    np.testing.assert_allclose(report.tau_matrix, report.tau_matrix.T)
    assert -1.0 <= report.mean_pairwise_tau <= 1.0


def test_recommended_is_added_as_a_first_labelled_candidate():
    """A per-metric recommended normalization enters the report as its own
    'recommended' column, ahead of the uniform strategies."""
    scores = np.array([[0.9, 30.0], [0.7, 50.0], [0.5, 40.0], [0.3, 20.0]])
    report = normalization_agreement(
        scores, _two_metric_polarity(), recommended=["min_max", "log_min_max"]
    )
    assert report.labels[0] == "recommended"
    assert "recommended" in report.ranks_by_label
    assert report.ranks_by_label["recommended"].shape == (4,)


def test_consensus_matches_mean_of_per_label_ranks():
    """The consensus ranking follows the per-label mean ranks, and the rank span
    bounds it."""
    rng = np.random.default_rng(0)
    scores = rng.uniform(0.1, 1.0, size=(6, 3))
    polarity = ["higher_is_better"] * 3
    report = normalization_agreement(scores, polarity)

    stacked = np.vstack([report.ranks_by_label[label] for label in report.labels])
    mean_rank = stacked.mean(axis=0)
    order_by_mean = np.argsort(mean_rank, kind="stable")
    assert report.consensus_ranks[order_by_mean[0]] <= report.consensus_ranks[order_by_mean[-1]]

    np.testing.assert_array_equal(report.rank_low, stacked.min(axis=0))
    np.testing.assert_array_equal(report.rank_high, stacked.max(axis=0))
    assert np.all(report.rank_low <= report.rank_high)


def test_log_min_max_dropped_on_non_positive_column():
    """log_min_max needs strictly positive values, so a column with a zero drops
    that candidate rather than failing the whole analysis."""
    scores = np.array([[0.9, 0.0], [0.7, 5.0], [0.5, 4.0], [0.3, 2.0]])
    report = normalization_agreement(scores, _two_metric_polarity())
    assert "log_min_max" not in report.labels
    assert len(report.labels) >= 2


def test_fewer_than_two_normalizations_raises():
    """A single normalization cannot be compared with anything, so the diagnostic
    refuses rather than reporting a one-candidate agreement of one."""
    scores = np.array([[0.9, 30.0], [0.7, 50.0], [0.5, 40.0]])
    with pytest.raises(ValueError, match="at least two normalizations"):
        normalization_agreement(scores, _two_metric_polarity(), strategies=["rank"])


def test_constant_input_gives_nan_tau_without_raising():
    """When every tool scores identically, each normalization ranks them all
    first; tau-b is undefined on a constant ranking, so the mean tau is nan and
    the diagnostic still returns a report."""
    scores = np.full((4, 2), 0.5)
    report = normalization_agreement(scores, _two_metric_polarity())
    assert np.isnan(report.mean_pairwise_tau)
    assert np.all(report.consensus_ranks == 1)
    assert report.top_is_unanimous


def test_tool_names_are_carried():
    """Tool labels pass through to the report unchanged."""
    scores = np.array([[0.9, 30.0], [0.7, 50.0], [0.5, 40.0]])
    report = normalization_agreement(scores, _two_metric_polarity(), tool_names=["a", "b", "c"])
    assert report.tool_names == ("a", "b", "c")
