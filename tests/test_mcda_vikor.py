"""Tests for VIKOR aggregation, with pymcdm as the regression oracle.

pymcdm.methods.VIKOR returns the canonical Q where lower is better; beam
returns -Q so that higher is better. Comparisons therefore reverse one side.
pymcdm applies its own internal min-max normalization, which is monotone on a
column already spanning [0, 1], so rankings are preserved.
"""

import numpy as np
import pytest
from pymcdm.methods import VIKOR

from beam.mcda import rank
from beam.mcda.vikor import vikor


def _spanning_matrix(rng, n_tools, n_metrics):
    """Random matrix in [0, 1] whose every column spans the full range.

    Forces one row to 0 and one row to 1 per column so no column has zero
    range, which keeps pymcdm's internal min-max well defined.
    """
    matrix = rng.random((n_tools, n_metrics))
    matrix[0, :] = 0.0
    matrix[1, :] = 1.0
    return matrix


def test_vikor_matches_pymcdm_ranking():
    """beam's induced ranking matches pymcdm VIKOR on seeded spanning matrices."""
    rng = np.random.default_rng(20240524)
    types = None  # set per matrix below
    for _ in range(30):
        n_tools = int(rng.integers(4, 9))
        n_metrics = int(rng.integers(2, 6))
        matrix = _spanning_matrix(rng, n_tools, n_metrics)
        weights = rng.random(n_metrics)
        weights = weights / weights.sum()
        types = np.ones(n_metrics)

        beam_score = vikor(matrix, weights)
        beam_ranks = rank(beam_score)

        oracle_q = VIKOR()(matrix, weights, types, validation=False)
        # pymcdm Q is lower is better, so rank its negation to match beam.
        oracle_ranks = rank(-oracle_q)

        np.testing.assert_array_equal(beam_ranks, oracle_ranks)


def test_vikor_dominant_tool_ranks_first():
    """A tool that beats every other on every metric has Q = 0, so it ranks first."""
    normalized = np.array(
        [
            [0.9, 0.9, 0.9],
            [0.1, 0.2, 0.3],
            [0.5, 0.4, 0.6],
        ]
    )
    weights = np.array([0.3, 0.3, 0.4])
    score = vikor(normalized, weights)
    ranks = rank(score)
    assert ranks[0] == 1
    # The dominant row sits at the ideal on every metric, so -Q is its maximum.
    assert score[0] == pytest.approx(0.0)
    assert score[0] == score.max()


def test_vikor_identical_rows_tie():
    """Two identical rows must receive the same score and the same rank."""
    normalized = np.array(
        [
            [0.8, 0.2],
            [0.3, 0.7],
            [0.8, 0.2],
        ]
    )
    weights = np.array([0.5, 0.5])
    score = vikor(normalized, weights)
    assert score[0] == pytest.approx(score[2])
    ranks = rank(score)
    assert ranks[0] == ranks[2]


def test_vikor_v_extremes_follow_s_and_r():
    """v = 1 follows group utility S only; v = 0 follows individual regret R only.

    Build a case where the S-best tool and the R-best tool differ. Tool 0 is
    balanced (good average, moderate worst metric). Tool 1 is lopsided (great
    on one metric, poor on another). At v = 1 the index is S; at v = 0 it is R.
    Compare beam against pymcdm at both extremes.
    """
    rng = np.random.default_rng(7)
    matrix = _spanning_matrix(rng, 6, 3)
    weights = np.array([0.4, 0.35, 0.25])
    types = np.ones(3)

    for v in (0.0, 1.0):
        beam_ranks = rank(vikor(matrix, weights, v=v))
        oracle_ranks = rank(-VIKOR(v=v)(matrix, weights, types, validation=False))
        np.testing.assert_array_equal(beam_ranks, oracle_ranks)


def test_vikor_v_changes_the_compromise():
    """Moving v should change at least one Q-derived ranking on a suitable matrix.

    Confirms v is wired into the blend rather than ignored. The matrix mixes a
    balanced tool with a lopsided one so S and R disagree on the order.
    """
    normalized = np.array(
        [
            [0.000, 0.000, 0.000],
            [1.000, 1.000, 1.000],
            [0.607, 0.729, 0.544],
            [0.935, 0.816, 0.003],
            [0.857, 0.034, 0.730],
        ]
    )
    weights = np.array([0.34, 0.33, 0.33])
    ranks_s = rank(vikor(normalized, weights, v=1.0))
    ranks_r = rank(vikor(normalized, weights, v=0.0))
    assert not np.array_equal(ranks_s, ranks_r)


def test_vikor_zero_range_metric_is_ignored():
    """A metric on which every tool is identical contributes nothing.

    Adding a constant column should not change the ranking induced by the
    informative columns.
    """
    informative = np.array(
        [
            [0.9, 0.1],
            [0.4, 0.8],
            [0.2, 0.5],
        ]
    )
    weights_two = np.array([0.5, 0.5])
    base = rank(vikor(informative, weights_two))

    with_constant = np.column_stack([informative, np.full(3, 0.5)])
    weights_three = np.array([0.4, 0.4, 0.2])
    extended = rank(vikor(with_constant, weights_three))
    np.testing.assert_array_equal(base, extended)


def test_vikor_single_tool_returns_zero():
    """A single tool has zero S and R range; Q is zero and the score is its negation."""
    score = vikor(np.array([[0.7, 0.3]]), np.array([0.6, 0.4]))
    np.testing.assert_allclose(score, [0.0])


def test_vikor_validates_dimensions():
    with pytest.raises(ValueError):
        vikor(np.array([[1.0, 2.0]]), np.array([0.5]))


def test_vikor_rejects_one_dimensional_matrix():
    with pytest.raises(ValueError, match="2D"):
        vikor(np.array([1.0, 2.0]), np.array([0.5, 0.5]))


def test_vikor_rejects_two_dimensional_weights():
    with pytest.raises(ValueError, match="1D"):
        vikor(np.array([[1.0, 2.0]]), np.array([[0.5, 0.5]]))


def test_vikor_rejects_negative_weights():
    with pytest.raises(ValueError, match="non-negative"):
        vikor(np.array([[1.0], [0.5]]), np.array([-0.5]))


def test_vikor_rejects_v_out_of_range():
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        vikor(np.array([[1.0], [0.5]]), np.array([1.0]), v=1.5)
