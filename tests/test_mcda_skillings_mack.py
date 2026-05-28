"""Tests for the Skillings-Mack coverage-aware Friedman test."""

from __future__ import annotations

import dataclasses
import math

import numpy as np
import pytest

from beam.mcda import (
    IncompleteMatrixError,
    SkillingsMackReport,
    coverage_aware_critical_difference,
    critical_difference,
    skillings_mack,
)


def test_complete_matrix_equals_friedman_chi_squared():
    """On a complete matrix the Skillings-Mack statistic matches the Friedman
    chi-squared from beam.mcda.critical_difference to machine precision."""
    rng = np.random.default_rng(0)
    scores = rng.uniform(size=(5, 8))
    sm = skillings_mack(scores)
    cd = critical_difference(scores)
    assert sm.statistic == pytest.approx(cd.friedman_statistic, abs=1e-10)
    assert sm.df == cd.n_tools - 1


def test_complete_matrix_without_ties_equals_friedman_at_random():
    """Several random seeds with no ties: the two statistics agree to
    machine precision. scipy's Friedman applies a tie correction the
    standard Skillings-Mack formulation does not, so the equality only holds
    when the within-block ranks are strict.
    """
    for seed in range(5):
        rng = np.random.default_rng(seed)
        scores = rng.uniform(size=(5, 7))
        sm = skillings_mack(scores)
        cd = critical_difference(scores)
        assert sm.statistic == pytest.approx(cd.friedman_statistic, abs=1e-10)


def test_hand_computed_three_methods_one_missing_cell():
    """Three methods, four blocks, one missing cell. The statistic has a
    closed-form value worked out below.

    Layout (rows are methods 0..2, columns are blocks 0..3):

        method 0:   10,  5,  8,  3
        method 1:  NaN,  4,  7,  2
        method 2:    1,  3,  6,  1

    Higher is better. Within-block ranks (1 lowest, k highest):

        block 0 (k=2): method 0 -> rank 2, method 2 -> rank 1.
            Standardising factor sqrt(12/3) = 2.
            Contributions A_0 += (2 - 1.5) * 2 = 1; A_2 += (1 - 1.5) * 2 = -1.
        blocks 1, 2, 3 (k=3 each, all three methods present):
            ranks always 3, 2, 1 for methods 0, 1, 2 respectively;
            factor = sqrt(3). Each contributes
            A_0 += sqrt(3), A_1 += 0, A_2 += -sqrt(3).

    So A_0 = 1 + 3*sqrt(3), A_1 = 0, A_2 = -(1 + 3*sqrt(3)).

    Sigma diagonal: block contributes k-1 to each present method.
        method 0: 1 + 2 + 2 + 2 = 7.
        method 1: 2 + 2 + 2 = 6.
        method 2: 1 + 2 + 2 + 2 = 7.

    Sigma offdiagonal: count of blocks containing both methods, negated.
        (0, 1): blocks 1, 2, 3 -> -3.
        (0, 2): all four blocks -> -4.
        (1, 2): blocks 1, 2, 3 -> -3.

    Dropping the last row and column:

        Sigma_red = [[7, -3], [-3, 6]], det = 33.
        Sigma_red^-1 = (1/33) * [[6, 3], [3, 7]].
        A_red = [1 + 3*sqrt(3), 0].
        T = A_red @ Sigma_red^-1 @ A_red = (6 / 33) * (1 + 3*sqrt(3))**2
            = (6 / 33) * (28 + 6*sqrt(3))
            = (168 + 36*sqrt(3)) / 33.
    """
    scores = np.array(
        [
            [10.0, 5.0, 8.0, 3.0],
            [np.nan, 4.0, 7.0, 2.0],
            [1.0, 3.0, 6.0, 1.0],
        ]
    )
    report = skillings_mack(scores)
    expected = (168.0 + 36.0 * math.sqrt(3.0)) / 33.0
    assert report.statistic == pytest.approx(expected, abs=1e-12)
    assert report.df == 2
    expected_a_0 = 1.0 + 3.0 * math.sqrt(3.0)
    np.testing.assert_allclose(
        report.adjusted_rank_sums, [expected_a_0, 0.0, -expected_a_0], atol=1e-12
    )
    np.testing.assert_array_equal(report.coverage, [4, 3, 4])
    assert report.n_methods == 3 and report.n_blocks == 4


def test_lower_is_better_flips_a_signs_but_keeps_statistic():
    """The chi-squared statistic does not depend on orientation."""
    rng = np.random.default_rng(1)
    scores = rng.uniform(size=(4, 7))
    # introduce a missing cell
    scores[2, 3] = np.nan
    high = skillings_mack(scores, higher_is_better=True)
    low = skillings_mack(scores, higher_is_better=False)
    assert high.statistic == pytest.approx(low.statistic, abs=1e-12)
    np.testing.assert_allclose(high.adjusted_rank_sums, -low.adjusted_rank_sums, atol=1e-12)


def test_method_in_only_one_block_runs():
    """A method that ran on exactly one block (with at least one other method
    present) is acceptable. Coverage records 1 and the test still runs."""
    scores = np.array(
        [
            [3.0, 2.0, 4.0, 1.0, 5.0],
            [2.0, 1.0, 3.0, 0.0, 4.0],
            [1.0, np.nan, np.nan, np.nan, np.nan],
        ]
    )
    report = skillings_mack(scores)
    assert int(report.coverage[2]) == 1
    assert int(report.coverage[0]) == 5
    assert math.isfinite(report.statistic)
    assert report.df == 2


def test_all_nan_row_refused():
    """A method with no observed block at all is refused with a clear error."""
    scores = np.array(
        [
            [1.0, 2.0, 3.0],
            [4.0, 5.0, 6.0],
            [np.nan, np.nan, np.nan],
        ]
    )
    with pytest.raises(ValueError, match="no observed block"):
        skillings_mack(scores, method_names=("a", "b", "c"))


def test_singleton_only_method_refused():
    """A method whose only observed blocks have no co-runner is refused."""
    scores = np.array(
        [
            [1.0, np.nan, np.nan],
            [np.nan, 2.0, np.nan],
            [np.nan, np.nan, 3.0],
        ]
    )
    with pytest.raises(ValueError, match="singleton blocks"):
        skillings_mack(scores)


def test_critical_difference_still_refuses_nan():
    """Regression: the Friedman-Nemenyi CD test refuses missing cells.
    Skillings-Mack is the alternative, not a replacement that masks the error.
    """
    scores = np.array(
        [
            [1.0, 2.0, 3.0],
            [4.0, 5.0, 6.0],
            [np.nan, 8.0, 9.0],
        ]
    )
    with pytest.raises(IncompleteMatrixError):
        critical_difference(scores)


def test_report_is_frozen():
    """The report dataclass is frozen, like the other beam.mcda report types."""
    rng = np.random.default_rng(2)
    report = skillings_mack(rng.uniform(size=(3, 5)))
    assert dataclasses.is_dataclass(report)
    with pytest.raises(dataclasses.FrozenInstanceError):
        report.statistic = 0.0  # type: ignore[misc]


def test_method_names_carried():
    rng = np.random.default_rng(3)
    report = skillings_mack(rng.uniform(size=(3, 4)), method_names=["a", "b", "c"])
    assert report.method_names == ("a", "b", "c")


def test_coverage_aware_wrapper_reports_no_cliques():
    """coverage_aware_critical_difference returns a SkillingsMackReport with
    no Nemenyi cliques and a note explaining why."""
    scores = np.array(
        [
            [10.0, 5.0, 8.0, 3.0],
            [np.nan, 4.0, 7.0, 2.0],
            [1.0, 3.0, 6.0, 1.0],
        ]
    )
    report = coverage_aware_critical_difference(scores)
    assert isinstance(report, SkillingsMackReport)
    assert report.nemenyi_cliques is None
    assert "complete matrix" in report.note


def test_too_few_methods_or_blocks_raises():
    with pytest.raises(ValueError, match="at least 3 methods"):
        skillings_mack(np.array([[1.0, 2.0], [3.0, 4.0]]))
    with pytest.raises(ValueError, match="at least 2 blocks"):
        skillings_mack(np.array([[1.0], [2.0], [3.0]]))


def test_method_names_length_mismatch_raises():
    scores = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
    with pytest.raises(ValueError, match="method_names"):
        skillings_mack(scores, method_names=["a", "b"])
