"""Tests for MCDA weight vectors."""

import numpy as np
import pytest

from beam.mcda import entropy_weights, equal_weights

# --- equal_weights ---


def test_equal_weights_sum_to_one():
    w = equal_weights(5)
    assert w.shape == (5,)
    np.testing.assert_allclose(w.sum(), 1.0)


def test_equal_weights_uniform():
    w = equal_weights(4)
    np.testing.assert_allclose(w, [0.25, 0.25, 0.25, 0.25])


def test_equal_weights_zero_raises():
    with pytest.raises(ValueError):
        equal_weights(0)


# --- entropy_weights ---


def test_entropy_uniform_column_gets_zero_weight():
    """A column with no variation across tools contributes nothing to the ranking."""
    normalised = np.array(
        [
            [0.5, 0.1],
            [0.5, 0.9],
        ]
    )
    weights = entropy_weights(normalised)
    assert weights[0] < 1e-6
    np.testing.assert_allclose(weights.sum(), 1.0)


def test_entropy_concentrated_column_gets_higher_weight_than_mild_one():
    """A high-variance column outweighs a low-variance one."""
    normalised = np.array(
        [
            [1.0, 0.4],
            [0.0, 0.5],
            [0.0, 0.6],
        ]
    )
    weights = entropy_weights(normalised)
    assert weights[0] > weights[1]


def test_entropy_weights_sum_to_one():
    rng = np.random.default_rng(1)
    normalised = rng.random((5, 4))
    weights = entropy_weights(normalised)
    np.testing.assert_allclose(weights.sum(), 1.0)


def test_entropy_weights_non_negative():
    rng = np.random.default_rng(2)
    normalised = rng.random((5, 4))
    weights = entropy_weights(normalised)
    assert (weights >= 0).all()


def test_entropy_all_uniform_falls_back_to_equal():
    """If every column is uniform, equal-weights is the safe fallback."""
    normalised = np.array(
        [
            [0.3, 0.4],
            [0.3, 0.4],
        ]
    )
    weights = entropy_weights(normalised)
    np.testing.assert_allclose(weights, [0.5, 0.5])


def test_entropy_needs_at_least_two_tools():
    with pytest.raises(ValueError, match="at least 2 tools"):
        entropy_weights(np.array([[0.5, 0.5]]))


def test_entropy_rejects_negative_values():
    with pytest.raises(ValueError, match="non-negative"):
        entropy_weights(np.array([[-0.1, 0.5], [0.5, 0.5]]))


def test_entropy_rejects_one_dimensional_input():
    with pytest.raises(ValueError, match="2D"):
        entropy_weights(np.array([0.1, 0.2, 0.3]))


def test_entropy_invariant_under_per_column_scaling():
    """Multiplying each column by its own positive constant preserves the weights.

    Entropy is computed on column proportions, not absolute values, so this
    invariance holds. It is a strong correctness check for the algorithm.
    """
    normalised = np.array(
        [
            [0.3, 0.7, 0.2],
            [0.5, 0.1, 0.8],
            [0.2, 0.2, 0.0],
        ]
    )
    base = entropy_weights(normalised)
    scaled = normalised * np.array([1.0, 10.0, 100.0])[None, :]
    rescaled = entropy_weights(scaled)
    np.testing.assert_allclose(base, rescaled, rtol=1e-10)


def test_entropy_weights_match_manual_computation():
    """Verify the formula on a small hand-checkable case."""
    normalised = np.array(
        [
            [1.0, 0.5],
            [0.0, 0.5],
        ]
    )
    # column 0: p = [1, 0]; E = -k * (1 * ln 1 + 0) = 0; d = 1
    # column 1: p = [0.5, 0.5]; E = -k * (0.5 * ln 0.5 + 0.5 * ln 0.5) = 1; d = 0
    # weights = [1/(1+0), 0/(1+0)] = [1, 0]
    weights = entropy_weights(normalised)
    np.testing.assert_allclose(weights, [1.0, 0.0], atol=1e-12)
