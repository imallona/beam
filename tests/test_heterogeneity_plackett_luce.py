"""Tests for the Plackett-Luce wrapper.

The ranking construction and input validation are pure Python and run
everywhere. The model fits need R with the PlackettLuce package and are
skipped when it is absent.
"""

from __future__ import annotations

import numpy as np
import pytest

from beam.datasets import load_duo2018
from beam.heterogeneity import (
    PlackettLuceReport,
    plackett_luce,
    plackett_luce_available,
    rankings_from_matrix,
)

HAVE_PL = plackett_luce_available()
needs_pl = pytest.mark.skipif(not HAVE_PL, reason="Rscript with PlackettLuce not available")


def test_plackett_luce_available_returns_bool():
    assert isinstance(plackett_luce_available(), bool)


def test_rankings_higher_is_better():
    # rows are methods, columns are datasets.
    matrix = np.array([[3.0, 3.0, 2.0], [2.0, 2.0, 3.0], [1.0, 1.0, 1.0]])
    ranks = rankings_from_matrix(matrix, "higher_is_better")
    expected = np.array([[1, 2, 3], [1, 2, 3], [2, 1, 3]])
    np.testing.assert_array_equal(ranks, expected)


def test_rankings_dense_ties_and_missing():
    # dataset 0: methods 0 and 1 tie at the top (dense rank 1, 1), method 2 second.
    # dataset 1: method 1 missing -> left out of that ranking (0).
    matrix = np.array([[5.0, 5.0], [5.0, np.nan], [2.0, 1.0]])
    # rankings_from_matrix returns one row per dataset, one column per method.
    ranks = rankings_from_matrix(matrix, "higher_is_better")
    assert list(ranks[0]) == [1, 1, 2]  # dataset 0: methods 0,1 tie at the top
    assert list(ranks[1]) == [1, 0, 2]  # dataset 1: method 1 missing (0)


def test_rankings_polarity_flips_order():
    matrix = np.array([[3.0], [2.0], [1.0]])  # 3 methods, 1 dataset
    high = rankings_from_matrix(matrix, "higher_is_better")
    low = rankings_from_matrix(matrix, "lower_is_better")
    assert list(high[0]) == [1, 2, 3]
    assert list(low[0]) == [3, 2, 1]


def test_rankings_validation():
    with pytest.raises(ValueError, match="polarity"):
        rankings_from_matrix(np.zeros((2, 2)), "bigger")
    with pytest.raises(ValueError, match="2D"):
        rankings_from_matrix(np.zeros((2, 2, 2)), "higher_is_better")
    with pytest.raises(ValueError, match="at least 2 methods"):
        rankings_from_matrix(np.zeros((1, 3)), "higher_is_better")


def test_plackett_luce_input_validation():
    with pytest.raises(ValueError, match="method_names"):
        plackett_luce(np.zeros((3, 4)), ["a", "b"])
    with pytest.raises(ValueError, match="npseudo"):
        plackett_luce(np.zeros((3, 4)), ["a", "b", "c"], npseudo=-1)
    # only one dataset has two ranked methods, so too few rankings survive.
    sparse = np.array([[1.0, np.nan], [np.nan, np.nan], [2.0, np.nan]])
    with pytest.raises(ValueError, match="at least 2 datasets"):
        plackett_luce(sparse, ["a", "b", "c"])


@needs_pl
def test_plackett_luce_recovers_clear_ordering():
    # A leads on two datasets, B on one, C is last everywhere.
    matrix = np.array([[3.0, 3.0, 2.0], [2.0, 2.0, 3.0], [1.0, 1.0, 1.0]])
    rep = plackett_luce(matrix, ["A", "B", "C"])
    assert isinstance(rep, PlackettLuceReport)
    assert rep.ranking() == ["A", "B", "C"]
    assert rep.worth[0] > rep.worth[1] > rep.worth[2]
    assert abs(float(np.nansum(rep.worth)) - 1.0) < 1e-9


@needs_pl
def test_plackett_luce_on_duo_agrees_with_other_diagnostics():
    duo = load_duo2018()
    ari = duo.tensor(("ari",))[:, :, 0]
    rep = plackett_luce(ari, duo.method_names, polarity="higher_is_better")
    assert rep.n_rankings == 12
    assert abs(float(np.nansum(rep.worth)) - 1.0) < 1e-9
    # SC3 leads the Plackett-Luce worth, matching the Bradley-Terry global
    # ranking and the mixed-effects marginal means on Duo 2018.
    assert rep.top_tool() == "SC3"
    # RaceID2 and FlowSOM are the weakest, as in the other diagnostics.
    bottom_two = set(rep.ranking()[-2:])
    assert bottom_two == {"RaceID2", "FlowSOM"}
