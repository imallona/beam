"""Tests for the Triantaphyllou-Sanchez weight perturbation primitive."""

import math

import numpy as np
import pytest

from beam.mcda import (
    PairPerturbation,
    WeightPerturbationReport,
    smallest_weight_perturbation,
)


def _toy_scores():
    """Three tools, two metrics; distinct composites under min-max + equal weights."""
    return np.array(
        [
            [0.9, 0.3],
            [0.7, 0.85],
            [0.5, 0.5],
        ]
    )


_TOY_POLARITY = ("higher_is_better", "higher_is_better")


def test_returns_weight_perturbation_report():
    out = smallest_weight_perturbation(_toy_scores(), _TOY_POLARITY)
    assert isinstance(out, WeightPerturbationReport)


def test_one_pair_per_ordered_pair_with_strict_inequality():
    """n_tools = 3 gives 3 ordered pairs (i above j); ties collapse."""
    out = smallest_weight_perturbation(_toy_scores(), _TOY_POLARITY)
    assert all(isinstance(p, PairPerturbation) for p in out.per_pair)
    pairs = {(p.higher, p.lower) for p in out.per_pair}
    assert len(pairs) == len(out.per_pair)
    for h, lo in pairs:
        assert out.base.ranks[h] < out.base.ranks[lo]


def test_delta_signs_match_direction_to_close_gap():
    """For each pair the candidate delta should bring the composites equal."""
    scores = _toy_scores()
    out = smallest_weight_perturbation(scores, _TOY_POLARITY)
    x = out.base.normalized
    w = out.base.weights.copy()
    for p in out.per_pair:
        if p.criterion == -1:
            continue
        w_perturbed = w.copy()
        w_perturbed[p.criterion] += p.delta
        new_composite = x @ w_perturbed
        np.testing.assert_allclose(new_composite[p.higher], new_composite[p.lower], atol=1e-9)


def test_top_rank_perturbation_uses_current_top_tool():
    out = smallest_weight_perturbation(_toy_scores(), _TOY_POLARITY)
    top_idx = int(np.argmin(out.base.ranks))
    if out.top_rank_perturbation is not None:
        assert out.top_rank_perturbation.higher == top_idx


def test_dominant_tool_has_no_finite_perturbation():
    """A strictly dominating tool cannot be displaced by any single-criterion change."""
    scores = np.array(
        [
            [0.9, 0.9],
            [0.5, 0.4],
            [0.1, 0.2],
        ]
    )
    out = smallest_weight_perturbation(scores, _TOY_POLARITY)
    top_idx = int(np.argmin(out.base.ranks))
    for p in out.per_pair:
        if p.higher == top_idx:
            assert p.criterion == -1
            assert math.isinf(p.absolute_delta)
    assert out.top_rank_perturbation is None
    assert out.top_rank_is_fragile is False


def test_fragility_flag_trips_under_threshold():
    """Two near-tied top tools should trip the fragility flag at threshold 0.5."""
    scores = np.array(
        [
            [0.90, 0.85],  # near-tied top
            [0.85, 0.90],
            [0.10, 0.05],  # clearly worst, breaks symmetry by leaving tools 0 and 1 distinct
        ]
    )
    out = smallest_weight_perturbation(
        scores, ("higher_is_better", "higher_is_better"), fragility_threshold=0.5
    )
    assert out.top_rank_is_fragile is True


def test_rejects_topsis():
    with pytest.raises(NotImplementedError, match="closed-form only for 'saw'"):
        smallest_weight_perturbation(_toy_scores(), _TOY_POLARITY, method="topsis")


def test_rejects_one_dimensional_scores():
    with pytest.raises(ValueError, match="2D"):
        smallest_weight_perturbation(np.array([0.5, 0.7]), ("higher_is_better",))


def test_per_pair_count_matches_n_ranked_pairs():
    """3 tools, distinct composites, give exactly 3 ordered above/below pairs."""
    scores = _toy_scores()
    out = smallest_weight_perturbation(scores, _TOY_POLARITY)
    assert len(out.per_pair) == 3
