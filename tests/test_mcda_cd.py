"""Tests for the Demsar Friedman-Nemenyi critical-difference module."""

import numpy as np
import pytest

from beam.mcda import (
    CriticalDifferenceReport,
    critical_difference,
    nemenyi_critical_difference,
)


def test_nemenyi_q_matches_demsar_table():
    """The q term (CD divided by the design factor) must match Demsar (2006)
    Table 5: 2.728 for five methods at alpha 0.05."""
    n_tools, n_datasets = 5, 10
    cd = nemenyi_critical_difference(n_tools, n_datasets, alpha=0.05)
    design = np.sqrt(n_tools * (n_tools + 1) / (6 * n_datasets))
    assert cd / design == pytest.approx(2.728, abs=1e-3)


def test_consistent_ranking_is_significant():
    """A method that is best on every dataset gets average rank 1, the Friedman
    test rejects, and it never shares a clique with the worst method."""
    base = np.array([4.0, 3.0, 2.0, 1.0])
    scores = np.column_stack([base for _ in range(8)])
    report = critical_difference(scores)
    assert isinstance(report, CriticalDifferenceReport)
    np.testing.assert_allclose(report.average_ranks, [1.0, 2.0, 3.0, 4.0])
    assert report.order[0] == 0
    assert report.friedman_pvalue < 0.05
    best, worst = 0, 3
    assert not any(best in c and worst in c for c in report.cliques)


def test_balanced_rotation_is_not_significant():
    """When each method takes each rank equally often, no method is separable:
    the Friedman test does not reject and every method falls in one clique."""
    cols = [np.roll(np.array([4.0, 3.0, 2.0, 1.0]), d % 4) for d in range(8)]
    scores = np.column_stack(cols)
    report = critical_difference(scores)
    np.testing.assert_allclose(report.average_ranks, [2.5, 2.5, 2.5, 2.5])
    assert report.friedman_pvalue > 0.05
    assert len(report.cliques) == 1
    assert set(report.cliques[0]) == {0, 1, 2, 3}


def test_lower_is_better_orientation():
    """With higher_is_better False, the tool with the smallest scores ranks first."""
    scores = np.array([[1.0, 1.0], [2.0, 2.0], [3.0, 3.0]])
    report = critical_difference(scores, higher_is_better=False)
    assert report.order[0] == 0
    assert report.average_ranks[0] == pytest.approx(1.0)


def test_friedman_statistic_is_orientation_invariant():
    rng = np.random.default_rng(0)
    scores = rng.uniform(size=(4, 6))
    high = critical_difference(scores, higher_is_better=True)
    low = critical_difference(scores, higher_is_better=False)
    assert high.friedman_statistic == pytest.approx(low.friedman_statistic)
    assert high.friedman_pvalue == pytest.approx(low.friedman_pvalue)


def test_ties_within_a_dataset_get_average_rank():
    scores = np.array([[5.0, 5.0], [5.0, 5.0], [1.0, 1.0]])
    report = critical_difference(scores)
    # the two tied top tools share rank 1.5, the third gets rank 3
    assert report.average_ranks[0] == pytest.approx(1.5)
    assert report.average_ranks[1] == pytest.approx(1.5)
    assert report.average_ranks[2] == pytest.approx(3.0)


def test_tool_names_carried():
    scores = np.column_stack([np.array([3.0, 2.0, 1.0]) for _ in range(3)])
    report = critical_difference(scores, tool_names=["a", "b", "c"])
    assert report.tool_names == ("a", "b", "c")


def test_too_few_tools_raises():
    with pytest.raises(ValueError, match="at least 3 tools"):
        critical_difference(np.array([[1.0, 2.0], [3.0, 4.0]]))


def test_too_few_datasets_raises():
    with pytest.raises(ValueError, match="at least 2 datasets"):
        critical_difference(np.array([[1.0], [2.0], [3.0]]))
