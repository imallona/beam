"""Tests for PROMETHEE II aggregation, with pymcdm as the regression oracle.

pymcdm.methods.PROMETHEE_II with the 'usual' preference function returns the
net outranking flow, which is already higher is better, matching beam's
convention. pymcdm applies its own internal min-max normalization, which is
monotone on a column already spanning [0, 1], so rankings are preserved.
"""

import numpy as np
import pytest
from pymcdm.methods import PROMETHEE_II

from beam.mcda import rank
from beam.mcda.promethee import promethee_ii


def _spanning_matrix(rng, n_tools, n_metrics):
    """Random matrix in [0, 1] whose every column spans the full range."""
    matrix = rng.random((n_tools, n_metrics))
    matrix[0, :] = 0.0
    matrix[1, :] = 1.0
    return matrix


def test_promethee_matches_pymcdm_net_flow():
    """beam's net flow matches pymcdm's usual-function PROMETHEE II numerically."""
    rng = np.random.default_rng(20240524)
    for _ in range(30):
        n_tools = int(rng.integers(4, 9))
        n_metrics = int(rng.integers(2, 6))
        matrix = _spanning_matrix(rng, n_tools, n_metrics)
        weights = rng.random(n_metrics)
        weights = weights / weights.sum()
        types = np.ones(n_metrics)

        beam_score = promethee_ii(matrix, weights)
        oracle_flow = PROMETHEE_II("usual")(matrix, weights, types, validation=False)

        np.testing.assert_allclose(beam_score, oracle_flow, atol=1e-12)


def test_promethee_matches_pymcdm_ranking():
    """beam's induced ranking matches pymcdm on seeded spanning matrices."""
    rng = np.random.default_rng(99)
    for _ in range(30):
        n_tools = int(rng.integers(4, 9))
        n_metrics = int(rng.integers(2, 6))
        matrix = _spanning_matrix(rng, n_tools, n_metrics)
        weights = rng.random(n_metrics)
        weights = weights / weights.sum()
        types = np.ones(n_metrics)

        beam_ranks = rank(promethee_ii(matrix, weights))
        oracle_ranks = rank(PROMETHEE_II("usual")(matrix, weights, types, validation=False))
        np.testing.assert_array_equal(beam_ranks, oracle_ranks)


def test_promethee_dominant_tool_ranks_first():
    """A tool that strictly beats every other on every metric reaches net flow 1."""
    normalized = np.array(
        [
            [0.9, 0.9, 0.9],
            [0.1, 0.2, 0.3],
            [0.5, 0.4, 0.6],
        ]
    )
    weights = np.array([0.3, 0.3, 0.4])
    score = promethee_ii(normalized, weights)
    ranks = rank(score)
    assert ranks[0] == 1
    # Tool 0 outranks both others on every metric and is outranked by none,
    # so its positive flow is 1 and its negative flow is 0.
    assert score[0] == pytest.approx(1.0)


def test_promethee_identical_rows_tie():
    """Two identical rows must receive the same net flow and the same rank."""
    normalized = np.array(
        [
            [0.8, 0.2],
            [0.3, 0.7],
            [0.8, 0.2],
        ]
    )
    weights = np.array([0.5, 0.5])
    score = promethee_ii(normalized, weights)
    assert score[0] == pytest.approx(score[2])
    ranks = rank(score)
    assert ranks[0] == ranks[2]


def test_promethee_net_flows_sum_to_zero():
    """Net flows are antisymmetric, so they sum to zero across tools."""
    rng = np.random.default_rng(3)
    matrix = _spanning_matrix(rng, 7, 4)
    weights = rng.random(4)
    weights = weights / weights.sum()
    score = promethee_ii(matrix, weights)
    assert score.sum() == pytest.approx(0.0, abs=1e-12)


def test_promethee_single_tool_returns_zero():
    """A single tool has no comparator; the net flow is zero by convention."""
    score = promethee_ii(np.array([[0.7, 0.3]]), np.array([0.6, 0.4]))
    np.testing.assert_allclose(score, [0.0])


def test_promethee_zero_weight_metric_is_ignored():
    """A metric with weight zero must not influence the net flow."""
    normalized = np.array(
        [
            [0.9, 0.0],
            [0.1, 1.0],
        ]
    )
    result = promethee_ii(normalized, np.array([1.0, 0.0]))
    assert result[0] > result[1]
    result = promethee_ii(normalized, np.array([0.0, 1.0]))
    assert result[1] > result[0]


def test_promethee_validates_dimensions():
    with pytest.raises(ValueError):
        promethee_ii(np.array([[1.0, 2.0]]), np.array([0.5]))


def test_promethee_rejects_one_dimensional_matrix():
    with pytest.raises(ValueError, match="2D"):
        promethee_ii(np.array([1.0, 2.0]), np.array([0.5, 0.5]))


def test_promethee_rejects_two_dimensional_weights():
    with pytest.raises(ValueError, match="1D"):
        promethee_ii(np.array([[1.0, 2.0]]), np.array([[0.5, 0.5]]))


def test_promethee_rejects_negative_weights():
    with pytest.raises(ValueError, match="non-negative"):
        promethee_ii(np.array([[1.0], [0.5]]), np.array([-0.5]))
