"""Tests for beam.mcda.bayesian_sign_comparison.

The closed-form posterior mean and the prior handling are checked analytically.
The Monte Carlo region probabilities are checked against their qualitative limits
and, when baycomp is importable, against that reference implementation.
"""

from __future__ import annotations

import numpy as np
import pytest

from beam.mcda import bayesian_sign_comparison, pairwise_superiority


def _superiority(scores, rope=0.0, names=None):
    return pairwise_superiority(scores, "higher_is_better", rope=rope, method_names=names)


def test_posterior_mean_is_dirichlet_mean():
    # Method 0 wins 3 datasets, method 1 wins 1, none equivalent (rope 0).
    scores = np.array([[0.9, 0.9, 0.9, 0.1], [0.1, 0.1, 0.1, 0.9]])
    report = bayesian_sign_comparison(_superiority(scores), prior_strength=1.0)
    pair = report.per_pair[0]
    # counts (a_better, equivalent, b_better) = (3, 0, 1); prior [0, 1, 0]; alpha = [3, 1, 1].
    assert pair.mean_a_better == pytest.approx(3 / 5)
    assert pair.mean_equivalent == pytest.approx(1 / 5)
    assert pair.mean_b_better == pytest.approx(1 / 5)


def test_probabilities_sum_to_one_per_pair():
    scores = np.array([[0.9, 0.8, 0.6, 0.7], [0.5, 0.6, 0.55, 0.5], [0.2, 0.3, 0.1, 0.25]])
    report = bayesian_sign_comparison(_superiority(scores), seed=1)
    for pair in report.per_pair:
        assert pair.p_a_better + pair.p_equivalent + pair.p_b_better == pytest.approx(1.0)


def test_off_diagonal_probabilities_complete_to_one():
    scores = np.array([[0.9, 0.8, 0.6, 0.7], [0.5, 0.6, 0.55, 0.5], [0.2, 0.3, 0.1, 0.25]])
    report = bayesian_sign_comparison(_superiority(scores), seed=1)
    n = scores.shape[0]
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            total = (
                report.probability_better[i, j]
                + report.probability_better[j, i]
                + report.probability_equivalent[i, j]
            )
            assert total == pytest.approx(1.0)


def test_overwhelming_evidence_reaches_a_decision():
    rng = np.random.default_rng(0)
    n_datasets = 60
    a = rng.uniform(0.7, 0.9, n_datasets)
    b = rng.uniform(0.1, 0.3, n_datasets)
    report = bayesian_sign_comparison(_superiority(np.vstack([a, b])), seed=0)
    pair = report.per_pair[0]
    assert pair.p_a_better > 0.99
    assert pair.decision == "a_better"
    assert report.order[0] == 0


def test_equivalence_when_all_within_rope():
    # All pairwise differences sit inside the rope, so every dataset is a tie.
    scores = np.array([[0.50, 0.51, 0.49, 0.50], [0.50, 0.50, 0.50, 0.51]])
    report = bayesian_sign_comparison(_superiority(scores, rope=0.05), seed=0)
    pair = report.per_pair[0]
    assert pair.equivalent == pair.n_compared
    assert pair.p_equivalent > 0.99
    assert pair.decision == "equivalent"


def test_swapping_methods_swaps_direction():
    # The closed-form means are exactly symmetric under relabelling; the sampled
    # probabilities match up to Monte Carlo noise.
    scores = np.array([[0.9, 0.8, 0.7, 0.85], [0.2, 0.3, 0.1, 0.25]])
    forward = bayesian_sign_comparison(_superiority(scores), seed=3).per_pair[0]
    swapped = bayesian_sign_comparison(_superiority(scores[::-1]), seed=3).per_pair[0]
    assert forward.mean_a_better == pytest.approx(swapped.mean_b_better)
    assert forward.mean_b_better == pytest.approx(swapped.mean_a_better)
    assert forward.mean_equivalent == pytest.approx(swapped.mean_equivalent)
    assert forward.p_a_better == pytest.approx(swapped.p_b_better, abs=0.01)
    assert forward.p_equivalent == pytest.approx(swapped.p_equivalent, abs=0.01)


def test_same_seed_reproduces():
    scores = np.array([[0.9, 0.4, 0.6, 0.7], [0.5, 0.6, 0.55, 0.5], [0.2, 0.7, 0.1, 0.25]])
    sup = _superiority(scores)
    first = bayesian_sign_comparison(sup, seed=7)
    second = bayesian_sign_comparison(sup, seed=7)
    np.testing.assert_array_equal(first.probability_better, second.probability_better)


def test_uniform_prior_has_no_zero_region():
    # Method 0 wins every dataset; under the uniform prior the losing region keeps
    # a small posterior mean rather than collapsing to zero.
    scores = np.array([[0.9, 0.9, 0.9, 0.9], [0.1, 0.1, 0.1, 0.1]])
    report = bayesian_sign_comparison(
        _superiority(scores), prior_strength=1.0, prior_placement="uniform"
    )
    pair = report.per_pair[0]
    # counts (4, 0, 0); prior [1/3, 1/3, 1/3]; alpha = [4.333, 0.333, 0.333].
    assert pair.mean_b_better == pytest.approx((1 / 3) / 5)
    assert pair.mean_b_better > 0.0


def test_invalid_arguments():
    sup = _superiority(np.array([[0.9, 0.8, 0.7], [0.2, 0.1, 0.3]]))
    with pytest.raises(ValueError):
        bayesian_sign_comparison(sup, prior_strength=-1.0)
    with pytest.raises(ValueError):
        bayesian_sign_comparison(sup, prior_placement="nope")
    with pytest.raises(ValueError):
        bayesian_sign_comparison(sup, decision_threshold=1.5)


def test_matches_baycomp_when_available():
    """Regression against the reference implementation (Benavoli et al., baycomp).

    Skipped when baycomp is not installed, in the same way the R-gated tests skip
    when the R toolchain is absent. The prior is matched explicitly (one
    pseudo-observation on the rope) so the comparison does not depend on either
    library's default.
    """
    baycomp = pytest.importorskip("baycomp")
    rng = np.random.default_rng(11)
    a = rng.uniform(0.4, 0.9, 30)
    b = rng.uniform(0.3, 0.8, 30)
    rope = 0.05

    sup = pairwise_superiority(np.vstack([a, b]), "higher_is_better", rope=rope)
    beam_report = bayesian_sign_comparison(
        sup, prior_strength=1.0, prior_placement="rope", n_samples=200000, seed=0
    )
    pair = beam_report.per_pair[0]

    # baycomp.SignTest.probs returns (p_left, p_rope, p_right) with the prior on the
    # rope by default; left is the first input (a) better, right is b better.
    p_left, p_rope, p_right = baycomp.SignTest.probs(a, b, rope=rope)
    assert pair.p_a_better == pytest.approx(p_left, abs=0.02)
    assert pair.p_equivalent == pytest.approx(p_rope, abs=0.02)
    assert pair.p_b_better == pytest.approx(p_right, abs=0.02)
