"""Tests for the MCDA normalisation step."""

import numpy as np
import pytest

from beam.mcda import min_max_normalize


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
