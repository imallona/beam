"""Tests for the SMAA weight-sampling sensitivity primitive."""

import numpy as np
import pytest

from beam.mcda import SMAAReport, smaa


def _toy_scores():
    return np.array(
        [
            [0.85, 120.0],
            [0.70, 30.0],
            [0.60, 90.0],
        ]
    )


_TOY_POLARITY = ["higher_is_better", "lower_is_better"]


def test_returns_smaa_report():
    report = smaa(_toy_scores(), _TOY_POLARITY, n_samples=64, seed=0)
    assert isinstance(report, SMAAReport)


def test_shapes_match_inputs_and_n_samples():
    report = smaa(_toy_scores(), _TOY_POLARITY, n_samples=64, seed=0)
    assert report.sampled_weights.shape == (64, 2)
    assert report.sampled_ranks.shape == (64, 3)
    assert report.rank_acceptability_index.shape == (3, 3)
    assert report.central_weight_vector.shape == (3, 2)
    assert report.confidence_factor.shape == (3,)


def test_rank_acceptability_index_rows_sum_to_one():
    report = smaa(_toy_scores(), _TOY_POLARITY, n_samples=128, seed=0)
    np.testing.assert_allclose(report.rank_acceptability_index.sum(axis=1), 1.0)


def test_rank_acceptability_index_columns_sum_to_one():
    """Across tools, every sample assigns each rank exactly once."""
    report = smaa(_toy_scores(), _TOY_POLARITY, n_samples=128, seed=0)
    np.testing.assert_allclose(report.rank_acceptability_index.sum(axis=0), 1.0)


def test_confidence_factor_equals_rank_one_column():
    report = smaa(_toy_scores(), _TOY_POLARITY, n_samples=128, seed=0)
    np.testing.assert_allclose(report.confidence_factor, report.rank_acceptability_index[:, 0])


def test_sampled_weights_lie_on_the_simplex():
    report = smaa(_toy_scores(), _TOY_POLARITY, n_samples=128, seed=0)
    assert (report.sampled_weights >= 0).all()
    np.testing.assert_allclose(report.sampled_weights.sum(axis=1), 1.0, atol=1e-12)


def test_dominant_tool_is_always_top_ranked():
    """A tool that dominates on every metric wins under any positive weights."""
    scores = np.array(
        [
            [0.9, 0.9],
            [0.5, 0.4],
            [0.1, 0.2],
        ]
    )
    report = smaa(scores, ["higher_is_better", "higher_is_better"], n_samples=200, seed=0)
    assert report.confidence_factor[0] == pytest.approx(1.0)
    assert report.rank_acceptability_index[0, 0] == pytest.approx(1.0)


def test_central_weight_vector_zero_when_tool_never_wins():
    """A dominated tool has an all-zero central weight vector."""
    scores = np.array(
        [
            [0.9, 0.9],
            [0.5, 0.4],
            [0.1, 0.2],
        ]
    )
    report = smaa(scores, ["higher_is_better", "higher_is_better"], n_samples=64, seed=0)
    np.testing.assert_array_equal(report.central_weight_vector[2], np.zeros(2))


def test_same_seed_reproduces_results():
    a = smaa(_toy_scores(), _TOY_POLARITY, n_samples=64, seed=42)
    b = smaa(_toy_scores(), _TOY_POLARITY, n_samples=64, seed=42)
    np.testing.assert_array_equal(a.sampled_weights, b.sampled_weights)
    np.testing.assert_array_equal(a.sampled_ranks, b.sampled_ranks)


def test_different_seeds_yield_different_samples():
    a = smaa(_toy_scores(), _TOY_POLARITY, n_samples=64, seed=1)
    b = smaa(_toy_scores(), _TOY_POLARITY, n_samples=64, seed=2)
    assert not np.array_equal(a.sampled_weights, b.sampled_weights)


def test_supports_topsis():
    report = smaa(_toy_scores(), _TOY_POLARITY, n_samples=64, method="topsis", seed=0)
    assert report.method == "topsis"
    assert report.base.method == "topsis"


def test_records_n_samples_and_seed():
    report = smaa(_toy_scores(), _TOY_POLARITY, n_samples=32, seed=7)
    assert report.n_samples == 32
    assert report.seed == 7


def test_rejects_unknown_method():
    with pytest.raises(ValueError, match="unknown method"):
        smaa(_toy_scores(), _TOY_POLARITY, method="vikor")


def test_rejects_one_dimensional_scores():
    with pytest.raises(ValueError, match="2D"):
        smaa(np.array([0.5, 0.7]), ["higher_is_better"])


def test_validates_polarity_length():
    with pytest.raises(ValueError, match="polarity"):
        smaa(np.array([[0.5, 0.7]]), ["higher_is_better"])


def test_rejects_non_positive_n_samples():
    with pytest.raises(ValueError, match="n_samples"):
        smaa(_toy_scores(), _TOY_POLARITY, n_samples=0)


def test_rejects_wrong_alpha_shape():
    with pytest.raises(ValueError, match="alpha"):
        smaa(_toy_scores(), _TOY_POLARITY, alpha=[1.0, 1.0, 1.0])


def test_rejects_non_positive_alpha():
    with pytest.raises(ValueError, match="alpha"):
        smaa(_toy_scores(), _TOY_POLARITY, alpha=[1.0, 0.0])


def test_custom_alpha_biases_the_sample_mean():
    """A high alpha on metric 0 should push the mean weight of column 0 above 0.5."""
    report = smaa(_toy_scores(), _TOY_POLARITY, n_samples=512, alpha=[10.0, 1.0], seed=0)
    assert report.sampled_weights[:, 0].mean() > 0.7
