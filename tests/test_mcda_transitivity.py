"""Tests for the transitivity check on the pairwise majority relation."""

import numpy as np

from beam.mcda import pairwise_superiority, pairwise_transitivity


def _transitivity(scores, polarity="higher_is_better", rope=0.0, names=None):
    report = pairwise_superiority(scores, polarity, rope=rope, method_names=names)
    return pairwise_transitivity(report)


def test_transitive_tournament_has_a_choice_and_full_consistence():
    scores = np.array([[0.9, 0.8, 0.7], [0.5, 0.6, 0.4], [0.2, 0.1, 0.3]])
    cc = _transitivity(scores, names=["a", "b", "c"])
    assert cc.condorcet_choice == 0
    assert cc.is_transitive is True
    assert cc.n_circular_triads == 0
    assert cc.coefficient_of_consistence == 1.0
    assert cc.consistent_order == (0, 1, 2)
    assert cc.tied_pairs == ()


def test_cyclic_relation_has_no_choice_and_zero_consistence():
    # A cyclic benchmark: 0 outperforms 1, 1 outperforms 2, 2 outperforms 0,
    # each on two of the three datasets.
    scores = np.array([[3, 1, 2], [2, 3, 1], [1, 2, 3]], dtype=float)
    cc = _transitivity(scores, names=["a", "b", "c"])
    assert cc.condorcet_choice is None
    assert cc.is_transitive is False
    assert cc.n_circular_triads == 1
    assert cc.n_triads == 1
    assert cc.circular_triads == ((0, 1, 2),)
    assert cc.coefficient_of_consistence == 0.0
    assert cc.consistent_order is None


def test_tied_pair_leaves_no_edge_and_no_coefficient():
    # Two methods each outperform the other on one of two datasets.
    scores = np.array([[1.0, 0.0], [0.0, 1.0]])
    cc = _transitivity(scores)
    assert cc.tied_pairs == ((0, 1),)
    assert cc.dominance.sum() == 0
    assert cc.condorcet_choice is None
    assert cc.coefficient_of_consistence is None
    assert cc.consistent_order is None
    # With a tied pair the relation is vacuously transitive (no edges to break).
    assert cc.is_transitive is True


def test_rope_can_remove_a_cycle_by_making_pairs_tied():
    # The same cyclic order as above but with differences inside a 0.01 band.
    scores = np.array([[0.030, 0.010, 0.020], [0.020, 0.030, 0.010], [0.010, 0.020, 0.030]])
    strict = _transitivity(scores, rope=0.0)
    assert strict.n_circular_triads == 1
    relaxed = _transitivity(scores, rope=0.05)
    assert relaxed.tied_pairs == ((0, 1), (0, 2), (1, 2))
    assert relaxed.n_circular_triads == 0
    assert relaxed.coefficient_of_consistence is None


def test_circular_triad_count_matches_kendalls_win_count_formula():
    # On a complete tournament the brute-force triad count must equal Kendall's
    # closed form d = n(n-1)(2n-1)/12 - sum(a_i^2)/2, where a_i is the number of
    # methods that method i outperforms.
    rng = np.random.default_rng(0)
    n = 7
    scores = rng.normal(size=(n, 9))  # odd dataset count, so no pairwise ties
    cc = _transitivity(scores)
    assert cc.tied_pairs == ()
    wins = cc.dominance.sum(axis=1)
    d_formula = n * (n - 1) * (2 * n - 1) / 12 - 0.5 * float((wins**2).sum())
    assert cc.n_circular_triads == round(d_formula)


def test_carries_method_names_and_rope_from_the_report():
    scores = np.array([[0.9, 0.8], [0.4, 0.5]])
    report = pairwise_superiority(scores, "higher_is_better", rope=0.02, method_names=["x", "y"])
    cc = pairwise_transitivity(report)
    assert cc.method_names == ("x", "y")
    assert cc.rope == 0.02


def _duo_ari_transitivity(rope):
    from beam import datasets

    duo = datasets.load_duo2018()
    ari = np.asarray(duo.tensor(("ari",)), float)[:, :, 0]
    report = pairwise_superiority(
        ari, "higher_is_better", rope=rope, method_names=list(duo.method_names)
    )
    return duo, pairwise_transitivity(report)


def test_duo_ari_has_a_condorcet_choice_but_is_not_transitive():
    duo, cc = _duo_ari_transitivity(rope=0.01)  # the ARI noise floor
    # SC3 is preferred to every other method by pairwise majority, the same
    # method the standing score, marginal means and Bradley-Terry pick out.
    assert cc.condorcet_choice is not None
    assert duo.method_names[cc.condorcet_choice] == "SC3"
    # Even so the relation carries one circular triad among the other methods, so
    # no single order agrees with all the pairwise majorities.
    assert cc.n_circular_triads == 1
    assert cc.is_transitive is False
    # Ties under the floor leave the coefficient of consistence undefined.
    assert cc.coefficient_of_consistence is None
    assert len(cc.tied_pairs) > 0


def test_duo_ari_noise_floor_removes_most_cycles():
    _, with_floor = _duo_ari_transitivity(rope=0.01)
    _, no_floor = _duo_ari_transitivity(rope=0.0)
    assert with_floor.n_circular_triads < no_floor.n_circular_triads
