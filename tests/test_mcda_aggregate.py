"""Tests for the MCDA aggregation step."""

import numpy as np
import pytest

from beam.mcda import rank, weighted_sum


def test_weighted_sum_uniform_weights():
    normalised = np.array([[0.5, 0.5], [1.0, 0.0]])
    weights = np.array([0.5, 0.5])
    result = weighted_sum(normalised, weights)
    np.testing.assert_allclose(result, [0.5, 0.5])


def test_weighted_sum_skewed_weights():
    normalised = np.array([[1.0, 0.0], [0.0, 1.0]])
    weights = np.array([0.8, 0.2])
    result = weighted_sum(normalised, weights)
    np.testing.assert_allclose(result, [0.8, 0.2])


def test_weighted_sum_dim_mismatch_raises():
    with pytest.raises(ValueError):
        weighted_sum(np.array([[1.0, 2.0]]), np.array([0.5, 0.5, 0.5]))


def test_weighted_sum_negative_weights_raises():
    with pytest.raises(ValueError, match="non-negative"):
        weighted_sum(np.array([[1.0]]), np.array([-1.0]))


def test_rank_basic_no_ties():
    scores = np.array([0.5, 0.9, 0.1, 0.7])
    result = rank(scores)
    np.testing.assert_array_equal(result, [3, 1, 4, 2])


def test_rank_with_ties():
    scores = np.array([0.5, 0.5, 0.9, 0.1])
    result = rank(scores)
    np.testing.assert_array_equal(result, [2, 2, 1, 4])


def test_rank_single_element():
    scores = np.array([0.5])
    result = rank(scores)
    np.testing.assert_array_equal(result, [1])
