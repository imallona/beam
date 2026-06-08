"""Tests for the pairwise probability-of-superiority comparison."""

import numpy as np
import pytest

from beam.mcda import pairwise_superiority


def test_total_outperformance():
    # method 0 outperforms 1 outperforms 2 on every dataset.
    scores = np.array([[0.9, 0.8, 0.7], [0.5, 0.6, 0.4], [0.2, 0.1, 0.3]])
    report = pairwise_superiority(scores, "higher_is_better", method_names=["a", "b", "c"])
    assert list(report.order) == [0, 1, 2]
    assert report.probability_superior[0, 1] == 1.0
    assert report.probability_superior[1, 0] == 0.0
    assert report.standing[0] == 1.0
    assert report.standing[2] == 0.0


def test_probabilities_and_equivalences_sum_to_one():
    rng = np.random.default_rng(0)
    scores = rng.normal(size=(4, 10))
    report = pairwise_superiority(scores, "higher_is_better")
    for p in report.per_pair:
        assert p.a_outperforms + p.equivalent + p.b_outperforms == p.n_compared
        assert p.p_superior_a + p.p_equivalent + p.p_superior_b == pytest.approx(1.0)


def test_lower_is_better_flips_the_direction():
    scores = np.array([[1.0, 2.0], [5.0, 6.0]])
    hi = pairwise_superiority(scores, "higher_is_better")
    lo = pairwise_superiority(scores, "lower_is_better")
    assert hi.probability_superior[0, 1] == 0.0
    assert lo.probability_superior[0, 1] == 1.0


def test_rope_turns_small_differences_into_equivalences():
    # method 0 scores 0.005 higher on every dataset; under a 0.01 ROPE these are equivalent.
    scores = np.array([[0.505, 0.605, 0.705], [0.500, 0.600, 0.700]])
    strict = pairwise_superiority(scores, "higher_is_better", rope=0.0)
    assert strict.per_pair[0].a_outperforms == 3
    roped = pairwise_superiority(scores, "higher_is_better", rope=0.01)
    pair = roped.per_pair[0]
    assert pair.equivalent == 3
    assert pair.a_outperforms == 0
    assert pair.p_equivalent == 1.0


def test_sign_test_flags_indistinguishable_pair():
    # an even split gives a non-significant sign test, so the pair is
    # listed as not distinguishable.
    scores = np.array([[1.0, 0.0, 1.0, 0.0], [0.0, 1.0, 0.0, 1.0]])
    report = pairwise_superiority(scores, "higher_is_better")
    assert report.per_pair[0].a_outperforms == 2
    assert report.per_pair[0].b_outperforms == 2
    assert report.per_pair[0].sign_pvalue == 1.0
    assert report.equivalent_pairs == ((0, 1),)


def test_sign_test_significant_when_one_method_always_outperforms():
    scores = np.array([[1.0, 1.0, 1.0, 1.0, 1.0, 1.0], [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]])
    report = pairwise_superiority(scores, "higher_is_better", alpha=0.05)
    assert report.per_pair[0].sign_pvalue < 0.05
    assert report.equivalent_pairs == ()


def test_pairwise_complete_over_datasets():
    # a missing cell drops only the datasets where a method is unobserved.
    scores = np.array([[0.9, np.nan, 0.7], [0.5, 0.6, 0.4]])
    report = pairwise_superiority(scores, "higher_is_better")
    assert report.per_pair[0].n_compared == 2


def test_validation():
    with pytest.raises(ValueError, match="2D"):
        pairwise_superiority(np.zeros((2, 2, 2)), "higher_is_better")
    with pytest.raises(ValueError, match="two methods"):
        pairwise_superiority(np.zeros((1, 3)), "higher_is_better")
    with pytest.raises(ValueError, match="two datasets"):
        pairwise_superiority(np.zeros((3, 1)), "higher_is_better")
    with pytest.raises(ValueError, match="polarity"):
        pairwise_superiority(np.zeros((2, 2)), "target_value")
    with pytest.raises(ValueError, match="rope"):
        pairwise_superiority(np.zeros((2, 2)), "higher_is_better", rope=-1.0)
    with pytest.raises(ValueError, match="method_names"):
        pairwise_superiority(np.zeros((2, 2)), "higher_is_better", method_names=["only_one"])


def test_duo_ari_most_pairs_equivalent_under_noise_floor():
    # with the ARI noise floor as the ROPE, most Duo method pairs are not
    # distinguishable, matching the critical-difference reading.
    from beam import datasets
    from beam.cards import properties_for

    duo = datasets.load_duo2018()
    ari = np.asarray(duo.tensor(("ari",)), float)[:, :, 0]
    floor = properties_for(["ari"])[0].noise_floor
    report = pairwise_superiority(
        ari, "higher_is_better", rope=floor or 0.0, method_names=list(duo.method_names)
    )
    assert len(report.equivalent_pairs) > len(report.per_pair) // 2
    # SC3 has the highest standing, matching the other Duo diagnostics.
    assert duo.method_names[report.order[0]] == "SC3"
