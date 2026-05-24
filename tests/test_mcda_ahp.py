"""Tests for the AHP pairwise weighting scheme.

The reference example is a 3 by 3 pairwise comparison matrix on Saaty's 1 to 9
scale, reproduced in many AHP tutorials of Saaty (1980). Its principal
eigenvector and consistency ratio are recomputed here and checked against the
published priorities, and a perfectly consistent matrix is used to confirm the
method recovers its generating weights with a consistency ratio of zero.
"""

from __future__ import annotations

import numpy as np
import pytest

from beam.mcda.weights import InconsistentPairwiseMatrixError, ahp_weights


def test_saaty_three_by_three_example() -> None:
    # Pairwise matrix on the 1 to 9 scale. The published eigenvector priorities
    # are about 0.649, 0.279, 0.072, with a consistency ratio near 0.056, which
    # is below the 0.1 threshold.
    matrix = np.array(
        [
            [1.0, 3.0, 7.0],
            [1.0 / 3.0, 1.0, 5.0],
            [1.0 / 7.0, 1.0 / 5.0, 1.0],
        ]
    )
    weights, consistency_ratio = ahp_weights(matrix)

    assert np.allclose(weights, [0.649, 0.279, 0.072], atol=1e-3)
    assert np.isclose(consistency_ratio, 0.056, atol=1e-3)
    assert consistency_ratio < 0.1
    assert np.isclose(weights.sum(), 1.0)
    assert np.all(weights > 0)


def test_perfectly_consistent_matrix_recovers_weights() -> None:
    true_weights = np.array([0.5, 0.3, 0.15, 0.05])
    matrix = true_weights[:, None] / true_weights[None, :]

    weights, consistency_ratio = ahp_weights(matrix)

    assert np.allclose(weights, true_weights, atol=1e-10)
    assert np.isclose(consistency_ratio, 0.0, atol=1e-10)


def test_order_two_matrix_is_always_consistent() -> None:
    matrix = np.array([[1.0, 4.0], [0.25, 1.0]])
    weights, consistency_ratio = ahp_weights(matrix)

    assert np.isclose(consistency_ratio, 0.0)
    assert np.allclose(weights, [0.8, 0.2], atol=1e-10)


def _inconsistent_matrix() -> np.ndarray:
    # A cyclic set of strong preferences that contradict each other:
    # 1 beats 2, 2 beats 3, but 3 beats 1. The consistency ratio is far above
    # the 0.1 threshold.
    return np.array(
        [
            [1.0, 9.0, 1.0 / 9.0],
            [1.0 / 9.0, 1.0, 9.0],
            [9.0, 1.0 / 9.0, 1.0],
        ]
    )


def test_inconsistent_matrix_warns_by_default() -> None:
    matrix = _inconsistent_matrix()
    with pytest.warns(UserWarning, match="consistency ratio"):
        _, consistency_ratio = ahp_weights(matrix)
    assert consistency_ratio > 0.1


def test_inconsistent_matrix_can_raise() -> None:
    matrix = _inconsistent_matrix()
    with pytest.raises(InconsistentPairwiseMatrixError, match="inconsistent"):
        ahp_weights(matrix, raise_on_inconsistency=True)


def test_rejects_non_square_matrix() -> None:
    matrix = np.array([[1.0, 2.0, 3.0], [0.5, 1.0, 2.0]])
    with pytest.raises(ValueError, match="square"):
        ahp_weights(matrix)


def test_rejects_non_positive_matrix() -> None:
    matrix = np.array([[1.0, 0.0], [0.0, 1.0]])
    with pytest.raises(ValueError, match="positive"):
        ahp_weights(matrix)


def test_rejects_non_reciprocal_matrix() -> None:
    matrix = np.array(
        [
            [1.0, 3.0, 7.0],
            [0.5, 1.0, 5.0],
            [1.0 / 7.0, 1.0 / 5.0, 1.0],
        ]
    )
    with pytest.raises(ValueError, match="reciprocal"):
        ahp_weights(matrix)
