"""Tests for TOPSIS aggregation."""

import numpy as np
import pytest

from beam.mcda import topsis


def test_topsis_dominator_reaches_one():
    """A tool that beats every other on every metric should hit closeness 1."""
    normalised = np.array([[1.0, 1.0], [0.0, 0.0]])
    weights = np.array([0.5, 0.5])
    result = topsis(normalised, weights)
    np.testing.assert_allclose(result, [1.0, 0.0])


def test_topsis_identical_tools_get_half():
    """No ideal exists when every tool is identical. Closeness defaults to 0.5."""
    normalised = np.array([[0.5, 0.5], [0.5, 0.5], [0.5, 0.5]])
    weights = np.array([0.5, 0.5])
    result = topsis(normalised, weights)
    np.testing.assert_allclose(result, [0.5, 0.5, 0.5])


def test_topsis_single_tool_returns_half():
    """A single tool has no comparator. Closeness is 0.5 by convention."""
    normalised = np.array([[0.7, 0.3]])
    weights = np.array([0.6, 0.4])
    result = topsis(normalised, weights)
    np.testing.assert_allclose(result, [0.5])


def test_topsis_symmetric_setup_ties_all_three():
    """In a perfectly symmetric two-metric setup, every tool gets closeness 0.5.

    TOPSIS measures distance to ideal and anti-ideal. With opposite extremes
    and an exact midpoint, all three sit on the same isodistance contour.
    TOPSIS does not favour compromise tools the way VIKOR does.
    """
    normalised = np.array(
        [
            [1.0, 0.0],
            [0.5, 0.5],
            [0.0, 1.0],
        ]
    )
    weights = np.array([0.5, 0.5])
    result = topsis(normalised, weights)
    np.testing.assert_allclose(result, [0.5, 0.5, 0.5])


def test_topsis_weight_tilt_picks_the_metric_specialist():
    """If most weight is on metric 0, the tool that is best on metric 0 wins."""
    normalised = np.array(
        [
            [1.0, 0.0],
            [0.5, 0.5],
            [0.0, 1.0],
        ]
    )
    result = topsis(normalised, np.array([0.9, 0.1]))
    assert result[0] > result[1] > result[2]


def test_topsis_validates_dimensions():
    with pytest.raises(ValueError):
        topsis(np.array([[1.0, 2.0]]), np.array([0.5]))


def test_topsis_rejects_one_dimensional_matrix():
    with pytest.raises(ValueError, match="2D"):
        topsis(np.array([1.0, 2.0]), np.array([0.5, 0.5]))


def test_topsis_rejects_two_dimensional_weights():
    with pytest.raises(ValueError, match="1D"):
        topsis(np.array([[1.0, 2.0]]), np.array([[0.5, 0.5]]))


def test_topsis_rejects_negative_weights():
    with pytest.raises(ValueError, match="non-negative"):
        topsis(np.array([[1.0], [0.5]]), np.array([-0.5]))


def test_topsis_output_always_in_unit_interval():
    """Closeness is always in [0, 1] for any non-negative input."""
    rng = np.random.default_rng(0)
    for _ in range(50):
        n_tools = int(rng.integers(2, 10))
        n_metrics = int(rng.integers(1, 8))
        normalised = rng.random((n_tools, n_metrics))
        weights = rng.random(n_metrics)
        weights = weights / weights.sum()
        result = topsis(normalised, weights)
        assert (result >= 0).all(), "closeness must be >= 0"
        assert (result <= 1).all(), "closeness must be <= 1"
        assert result.shape == (n_tools,)


def test_topsis_invariant_under_uniform_weight_scaling():
    """Multiplying every weight by the same positive constant preserves closeness."""
    rng = np.random.default_rng(1)
    normalised = rng.random((6, 4))
    weights = rng.random(4)
    base = topsis(normalised, weights)
    scaled = topsis(normalised, weights * 3.7)
    np.testing.assert_allclose(base, scaled, rtol=1e-9)


def test_topsis_zero_weight_metric_is_ignored():
    """A metric with weight zero should not influence the closeness."""
    normalised = np.array(
        [
            [0.9, 0.0],
            [0.1, 1.0],
        ]
    )
    # With weight only on column 0, tool 0 wins.
    result = topsis(normalised, np.array([1.0, 0.0]))
    assert result[0] > result[1]
    # Now flip the weight onto column 1; tool 1 wins.
    result = topsis(normalised, np.array([0.0, 1.0]))
    assert result[1] > result[0]
