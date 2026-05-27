"""Tests for the MCDA normalization step."""

import numpy as np
import pytest

from beam.mcda import min_max_normalize, normalization_warnings, normalize


def test_higher_is_better_min_max():
    scores = np.array([[0.5], [0.9], [0.1]])
    result = min_max_normalize(scores, ["higher_is_better"])
    np.testing.assert_allclose(result, [[0.5], [1.0], [0.0]])


def test_lower_is_better_min_max():
    scores = np.array([[10.0], [50.0], [5.0]])
    result = min_max_normalize(scores, ["lower_is_better"])
    np.testing.assert_allclose(result, [[8 / 9], [0.0], [1.0]])


def test_mixed_polarity():
    scores = np.array([[0.9, 100.0], [0.5, 10.0]])
    result = min_max_normalize(scores, ["higher_is_better", "lower_is_better"])
    np.testing.assert_allclose(result, [[1.0, 0.0], [0.0, 1.0]])


def test_zero_range_column_maps_to_half():
    scores = np.array([[0.5], [0.5], [0.5]])
    result = min_max_normalize(scores, ["higher_is_better"])
    np.testing.assert_allclose(result, [[0.5], [0.5], [0.5]])


def test_polarity_count_mismatch_raises():
    with pytest.raises(ValueError, match="polarity"):
        min_max_normalize(np.array([[1.0, 2.0]]), ["higher_is_better"])


def test_unknown_polarity_raises():
    with pytest.raises(ValueError, match="unknown polarity"):
        min_max_normalize(np.array([[1.0], [2.0]]), ["nonsense"])


def test_one_dimensional_input_raises():
    with pytest.raises(ValueError, match="2D"):
        min_max_normalize(np.array([1.0, 2.0, 3.0]), ["higher_is_better"])


def test_log_min_max_compresses_a_heavy_tail():
    """A 100x outlier leaves the small values spread out under log scaling,
    whereas plain min-max would crush them all near the same value."""
    scores = np.array([[10.0], [20.0], [40.0], [4000.0]])
    out = normalize(scores, ["lower_is_better"], ["log_min_max"])
    # fastest maps to 1, slowest to 0, and the two middle methods stay apart
    assert out[0, 0] == pytest.approx(1.0)
    assert out[3, 0] == pytest.approx(0.0)
    assert out[1, 0] - out[2, 0] > 0.1


def test_log_min_max_requires_positive_values():
    with pytest.raises(ValueError, match="strictly positive"):
        normalize(np.array([[1.0], [0.0]]), ["lower_is_better"], ["log_min_max"])


def test_rank_is_scale_free_and_outlier_proof():
    """Rank normalization depends only on order, so a 100x outlier does not
    change the spacing of the other methods."""
    a = normalize(np.array([[10.0], [20.0], [40.0]]), ["lower_is_better"], ["rank"])
    b = normalize(np.array([[10.0], [20.0], [4000.0]]), ["lower_is_better"], ["rank"])
    np.testing.assert_allclose(a, b)
    np.testing.assert_allclose(a.ravel(), [1.0, 0.5, 0.0])


def test_rank_ties_share_the_mean_rank():
    out = normalize(np.array([[5.0], [5.0], [1.0]]), ["higher_is_better"], ["rank"])
    assert out[0, 0] == out[1, 0]


def test_zscore_maps_the_mean_method_to_half():
    out = normalize(np.array([[1.0], [2.0], [3.0]]), ["higher_is_better"], ["zscore"])
    assert out[1, 0] == pytest.approx(0.5)
    assert 0.0 < out[0, 0] < 0.5 < out[2, 0] < 1.0


def test_baseline_relative_maps_chance_to_zero():
    """A chance-level value (0) maps to 0, not to the column midpoint."""
    scores = np.array([[0.8], [0.0], [-0.2]])
    out = normalize(
        scores,
        ["higher_is_better"],
        ["baseline_relative"],
        bounds=[(-1, 1)],
        baselines=[0.0],
    )
    np.testing.assert_allclose(out.ravel(), [0.8, 0.0, 0.0])


def test_baseline_relative_needs_a_baseline():
    with pytest.raises(ValueError, match="score_of_random_baseline"):
        normalize(np.array([[0.8], [0.2]]), ["higher_is_better"], ["baseline_relative"])


def test_baseline_relative_rejects_lower_is_better():
    with pytest.raises(ValueError, match="higher_is_better"):
        normalize(
            np.array([[0.8], [0.2]]),
            ["lower_is_better"],
            ["baseline_relative"],
            baselines=[0.0],
        )


def test_target_relative_maps_the_target_to_one():
    """The method at the target maps to 1, the farthest to 0, by deviation."""
    scores = np.array([[1.0], [0.7], [1.3], [2.0]])
    out = normalize(scores, ["target_value"], ["target_relative"], targets=[1.0])
    # deviations 0, 0.3, 0.3, 1.0; min-max of a lower-is-better deviation gives 1 - d.
    np.testing.assert_allclose(out.ravel(), [1.0, 0.7, 0.7, 0.0])


def test_target_relative_is_symmetric_around_the_target():
    """Equal deviations on either side of the target map to the same score."""
    scores = np.array([[0.5], [1.5], [1.0]])
    out = normalize(scores, ["target_value"], ["target_relative"], targets=[1.0])
    assert out[0, 0] == out[1, 0]
    assert out[2, 0] == 1.0


def test_target_relative_keeps_nan_and_handles_zero_range():
    """A missing cell stays NaN; all-equidistant methods map to 0.5."""
    scores = np.array([[0.5], [1.5], [np.nan]])
    out = normalize(scores, ["target_value"], ["target_relative"], targets=[1.0])
    assert np.isnan(out[2, 0])
    np.testing.assert_allclose(out[:2, 0], [0.5, 0.5])


def test_target_relative_needs_a_target():
    with pytest.raises(ValueError, match=r"semantics\.target"):
        normalize(np.array([[0.8], [1.2]]), ["target_value"], ["target_relative"])


def test_target_value_polarity_requires_target_relative():
    with pytest.raises(ValueError, match="requires the 'target_relative'"):
        normalize(np.array([[0.8], [1.2]]), ["target_value"], ["min_max"])


def test_target_relative_rejects_a_monotone_polarity():
    with pytest.raises(ValueError, match="for 'target_value' metrics only"):
        normalize(
            np.array([[0.8], [1.2]]),
            ["higher_is_better"],
            ["target_relative"],
            targets=[1.0],
        )


def test_out_of_range_check_applies_to_every_strategy():
    """The declared-range guard fires regardless of the strategy chosen."""
    with pytest.raises(ValueError, match="above declared upper bound"):
        normalize(np.array([[2.0], [0.5]]), ["higher_is_better"], ["rank"], bounds=[(-1, 1)])


def test_unknown_strategy_raises():
    with pytest.raises(ValueError, match="unknown normalization strategy"):
        normalize(np.array([[1.0], [2.0]]), ["higher_is_better"], ["bogus"])


def test_warns_on_empirical_bound():
    scores = np.array([[10.0], [20.0], [30.0]])
    warnings = normalization_warnings(
        scores, ["min_max"], bounds=[(0, None)], metric_ids=["runtime"]
    )
    assert any("empirical upper bound" in w for w in warnings)


def test_warns_on_heavy_tail():
    scores = np.array([[1.0], [2.0], [500.0]])
    warnings = normalization_warnings(
        scores, ["min_max"], bounds=[(0, 1000)], metric_ids=["runtime"]
    )
    assert any("heavy-tailed" in w for w in warnings)


def test_no_warning_for_bounded_min_max():
    scores = np.array([[0.2], [0.5], [0.9]])
    warnings = normalization_warnings(scores, ["min_max"], bounds=[(0, 1)], metric_ids=["nmi"])
    assert warnings == []


def test_no_warning_for_non_min_max_strategies():
    scores = np.array([[10.0], [20.0], [5000.0]])
    warnings = normalization_warnings(scores, ["log_min_max"], bounds=[(0, None)])
    assert warnings == []
