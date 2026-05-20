"""Tests for the MCDA facade: beam.mcda.run."""

import numpy as np
import pytest

from beam.cards import Registry
from beam.mcda import (
    Result,
    equal_weights,
    min_max_normalize,
    rank,
    run,
    weighted_sum,
)


def _toy_scores():
    return np.array(
        [
            [0.85, 120.0],
            [0.70, 30.0],
            [0.60, 90.0],
        ]
    )


_TOY_POLARITY = ["higher_is_better", "lower_is_better"]


def test_run_returns_result_with_all_fields():
    result = run(_toy_scores(), _TOY_POLARITY)
    assert isinstance(result, Result)
    assert result.scores.shape == (3, 2)
    assert result.normalised.shape == (3, 2)
    assert result.weights.shape == (2,)
    assert result.composite.shape == (3,)
    assert result.ranks.shape == (3,)
    assert result.method == "saw"
    assert result.weighting == "equal"


def test_run_default_uses_equal_weights():
    result = run(_toy_scores(), _TOY_POLARITY)
    np.testing.assert_allclose(result.weights, [0.5, 0.5])


def test_run_with_entropy_weights():
    result = run(_toy_scores(), _TOY_POLARITY, weights="entropy")
    np.testing.assert_allclose(result.weights.sum(), 1.0)
    assert (result.weights >= 0).all()
    assert result.weighting == "entropy"


def test_run_with_topsis_method():
    result = run(_toy_scores(), _TOY_POLARITY, method="topsis")
    assert result.method == "topsis"
    assert (result.composite >= 0).all()
    assert (result.composite <= 1).all()


def test_run_with_user_supplied_weights():
    result = run(_toy_scores(), _TOY_POLARITY, weights=[0.8, 0.2])
    np.testing.assert_allclose(result.weights, [0.8, 0.2])
    assert result.weighting == "user-supplied"


def test_run_combined_entropy_topsis():
    """Smoke test for the combination we will use in the vignette."""
    result = run(_toy_scores(), _TOY_POLARITY, weights="entropy", method="topsis")
    assert result.method == "topsis"
    assert result.weighting == "entropy"
    assert sorted(result.ranks) == [1, 2, 3]


def test_run_rejects_unknown_weighting():
    with pytest.raises(ValueError, match="unknown weighting"):
        run(_toy_scores(), _TOY_POLARITY, weights="nonsense")


def test_run_rejects_unknown_method():
    with pytest.raises(ValueError, match="unknown method"):
        run(_toy_scores(), _TOY_POLARITY, method="bogus")


def test_run_rejects_wrong_polarity_length():
    with pytest.raises(ValueError, match="polarity"):
        run(np.array([[1.0, 2.0]]), ["higher_is_better"])


def test_run_rejects_one_dimensional_scores():
    with pytest.raises(ValueError, match="2D"):
        run(np.array([1.0, 2.0]), ["higher_is_better"])


def test_run_user_weights_wrong_length_raises():
    with pytest.raises(ValueError, match="shape"):
        run(_toy_scores(), _TOY_POLARITY, weights=[0.5, 0.3, 0.2])


def test_run_user_weights_negative_raises():
    with pytest.raises(ValueError, match="non-negative"):
        run(_toy_scores(), _TOY_POLARITY, weights=[-0.5, 0.5])


def test_run_end_to_end_with_registry():
    """Compose the facade with the cards registry. The canonical use case."""
    reg = Registry()
    metric_ids = ["ari", "runtime"]
    polarity = [reg.get(mid).polarity for mid in metric_ids]
    result = run(_toy_scores(), polarity, weights="entropy", method="topsis")
    assert result.ranks.shape == (3,)
    assert sorted(result.ranks) == [1, 2, 3]


def test_run_saw_matches_hand_call_to_primitives():
    """The facade with equal/saw must match the manual four-function pipeline."""
    scores = _toy_scores()
    expected_norm = min_max_normalize(scores, _TOY_POLARITY)
    expected_w = equal_weights(scores.shape[1])
    expected_composite = weighted_sum(expected_norm, expected_w)
    expected_ranks = rank(expected_composite)

    result = run(scores, _TOY_POLARITY)
    np.testing.assert_allclose(result.normalised, expected_norm)
    np.testing.assert_allclose(result.weights, expected_w)
    np.testing.assert_allclose(result.composite, expected_composite)
    np.testing.assert_array_equal(result.ranks, expected_ranks)


def test_run_result_records_user_polarity_as_tuple():
    result = run(_toy_scores(), _TOY_POLARITY)
    assert result.polarity == tuple(_TOY_POLARITY)
    assert isinstance(result.polarity, tuple)
