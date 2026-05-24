"""Tests for COMET aggregation.

Parity is checked against pymcdm. COMET takes an expert function that ranks
characteristic objects, and beam uses the weighted sum of an object's
coordinates as that expert. To compare like with like, the pymcdm oracle is
configured with the same characteristic values and a custom expert that
applies the same weighted-sum rule, so any difference would come from the
COMET machinery (characteristic objects, summed judgement, preference, fuzzy
interpolation) rather than from a different expert. With the expert held
identical, beam reproduces pymcdm exactly.

pymcdm is a test-only dependency. It must never be imported from beam itself.
"""

import numpy as np
import pytest
from pymcdm.methods import COMET as PymcdmCOMET

from beam.mcda.comet import comet


def _weighted_sum_expert(weights: np.ndarray):
    """Build a pymcdm expert function matching beam's weighted-sum rule.

    The expert returns the Summed Judgement vector, the row sums of the
    Matrix of Expert Judgement, where object i beats j when its weighted sum
    is larger. The MEJ is returned as None because pymcdm rebuilds it from the
    summed judgement when asked.
    """

    def expert(characteristic_objects: np.ndarray):
        weighted_sums = characteristic_objects @ weights
        difference = weighted_sums[:, None] - weighted_sums[None, :]
        mej = np.where(difference > 0, 1.0, np.where(difference < 0, 0.0, 0.5))
        return mej.sum(axis=1), None

    return expert


def _pymcdm_comet(matrix, weights, characteristic_values):
    cvalues = [np.asarray(values, dtype=float) for values in characteristic_values]
    body = PymcdmCOMET(cvalues, _weighted_sum_expert(np.asarray(weights, dtype=float)))
    return body(np.asarray(matrix, dtype=float))


def test_comet_matches_pymcdm_two_endpoints():
    """Default endpoint characteristic values reproduce pymcdm exactly."""
    rng = np.random.default_rng(0)
    for _ in range(50):
        n_tools = int(rng.integers(2, 9))
        n_metrics = int(rng.integers(2, 5))
        matrix = rng.random((n_tools, n_metrics))
        weights = rng.random(n_metrics)
        weights = weights / weights.sum()
        cvalues = [[0.0, 1.0]] * n_metrics
        mine = comet(matrix, weights)
        reference = _pymcdm_comet(matrix, weights, cvalues)
        np.testing.assert_allclose(mine, reference, atol=1e-12)


def test_comet_matches_pymcdm_three_values():
    """Three characteristic values per criterion also reproduce pymcdm exactly."""
    rng = np.random.default_rng(1)
    for _ in range(50):
        n_tools = int(rng.integers(2, 9))
        n_metrics = int(rng.integers(2, 4))
        matrix = rng.random((n_tools, n_metrics))
        weights = rng.random(n_metrics)
        weights = weights / weights.sum()
        cvalues = [[0.0, 0.5, 1.0]] * n_metrics
        mine = comet(matrix, weights, cvalues)
        reference = _pymcdm_comet(matrix, weights, cvalues)
        np.testing.assert_allclose(mine, reference, atol=1e-12)


def test_comet_rank_vector_matches_pymcdm():
    """The full rank vector agrees with pymcdm under mixed characteristic values."""
    rng = np.random.default_rng(2)
    for _ in range(30):
        n_tools = int(rng.integers(3, 10))
        n_metrics = int(rng.integers(2, 4))
        matrix = rng.random((n_tools, n_metrics))
        weights = rng.random(n_metrics)
        weights = weights / weights.sum()
        cvalues = [[0.0, 0.5, 1.0] if rng.random() < 0.5 else [0.0, 1.0] for _ in range(n_metrics)]
        mine_order = np.argsort(-comet(matrix, weights, cvalues), kind="stable")
        reference_order = np.argsort(-_pymcdm_comet(matrix, weights, cvalues), kind="stable")
        np.testing.assert_array_equal(mine_order, reference_order)


def test_comet_dominant_alternative_ranks_first():
    """A tool that beats every other on every metric gets the top preference.

    Hand check: the dominant row sits at the all-ones corner, which is the
    single best characteristic object (preference 1), so its score is 1.
    """
    normalized = np.array(
        [
            [1.0, 1.0],
            [0.4, 0.7],
            [0.2, 0.1],
        ]
    )
    weights = np.array([0.5, 0.5])
    scores = comet(normalized, weights)
    assert np.argmax(scores) == 0
    np.testing.assert_allclose(scores[0], 1.0, atol=1e-12)


def test_comet_dominated_corner_scores_zero():
    """The all-zeros corner is the worst characteristic object, preference 0."""
    normalized = np.array(
        [
            [0.0, 0.0],
            [0.6, 0.3],
        ]
    )
    weights = np.array([0.5, 0.5])
    scores = comet(normalized, weights)
    np.testing.assert_allclose(scores[0], 0.0, atol=1e-12)


def test_comet_is_rank_reversal_free():
    """Removing a dominated alternative does not reorder the survivors.

    This is the defining property of COMET. The local model is fit on the
    fixed grid of characteristic objects, so the preference of any alternative
    does not depend on which other alternatives are present.
    """
    rng = np.random.default_rng(3)
    weights = np.array([0.45, 0.55])
    full = rng.random((6, 2))
    survivors = full[:-1]
    cvalues = [[0.0, 0.5, 1.0], [0.0, 1.0]]

    scores_full = comet(full, weights, cvalues)
    scores_survivors = comet(survivors, weights, cvalues)

    order_full = np.argsort(-scores_full[:-1], kind="stable")
    order_survivors = np.argsort(-scores_survivors, kind="stable")
    np.testing.assert_array_equal(order_full, order_survivors)
    np.testing.assert_allclose(scores_full[:-1], scores_survivors, atol=1e-12)


def test_comet_weight_tilt_picks_the_specialist():
    """Putting most weight on metric 0 favours the tool best on metric 0."""
    normalized = np.array(
        [
            [0.9, 0.1],
            [0.1, 0.9],
        ]
    )
    scores = comet(normalized, np.array([0.9, 0.1]))
    assert scores[0] > scores[1]
    scores = comet(normalized, np.array([0.1, 0.9]))
    assert scores[1] > scores[0]


def test_comet_output_in_unit_interval():
    """Preference values stay in [0, 1] for any [0, 1] input."""
    rng = np.random.default_rng(4)
    for _ in range(50):
        n_tools = int(rng.integers(2, 10))
        n_metrics = int(rng.integers(2, 6))
        normalized = rng.random((n_tools, n_metrics))
        weights = rng.random(n_metrics)
        weights = weights / weights.sum()
        scores = comet(normalized, weights)
        assert scores.shape == (n_tools,)
        assert (scores >= -1e-12).all()
        assert (scores <= 1 + 1e-12).all()


def test_comet_rejects_one_dimensional_matrix():
    with pytest.raises(ValueError, match="2D"):
        comet(np.array([1.0, 2.0]), np.array([0.5, 0.5]))


def test_comet_rejects_two_dimensional_weights():
    with pytest.raises(ValueError, match="1D"):
        comet(np.array([[1.0, 2.0]]), np.array([[0.5, 0.5]]))


def test_comet_rejects_mismatched_weights():
    with pytest.raises(ValueError, match="does not match"):
        comet(np.array([[1.0, 2.0]]), np.array([0.5]))


def test_comet_rejects_negative_weights():
    with pytest.raises(ValueError, match="non-negative"):
        comet(np.array([[1.0], [0.5]]), np.array([-0.5]))


def test_comet_rejects_wrong_number_of_characteristic_value_sets():
    with pytest.raises(ValueError, match="one per"):
        comet(np.array([[0.5, 0.5]]), np.array([0.5, 0.5]), [[0.0, 1.0]])


def test_comet_rejects_non_increasing_characteristic_values():
    with pytest.raises(ValueError, match="strictly increasing"):
        comet(
            np.array([[0.5, 0.5]]),
            np.array([0.5, 0.5]),
            [[0.0, 1.0], [1.0, 1.0]],
        )


def test_comet_rejects_too_few_characteristic_values():
    with pytest.raises(ValueError, match="at least 2"):
        comet(np.array([[0.5, 0.5]]), np.array([0.5, 0.5]), [[0.5], [0.0, 1.0]])
