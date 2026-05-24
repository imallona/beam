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


def test_rejects_unknown_method():
    with pytest.raises(ValueError, match="unknown method"):
        smallest_weight_perturbation(_toy_scores(), _TOY_POLARITY, method="not_a_method")


@pytest.mark.parametrize("method", ["topsis", "vikor", "promethee_ii", "comet"])
def test_numeric_path_runs_on_non_linear_methods(method):
    """The numeric path returns a report for each non-linear aggregation."""
    out = smallest_weight_perturbation(_toy_scores(), _TOY_POLARITY, method=method)
    assert isinstance(out, WeightPerturbationReport)
    assert len(out.per_pair) == 3


def _seeded_matrices():
    rng = np.random.default_rng(0)
    return [rng.random((4, 3)) for _ in range(5)]


def test_numeric_path_agrees_with_closed_form_on_saw():
    """On SAW the numeric search must recover the exact closed-form delta.

    The numeric path is validated against the exact answer: for every pair with
    a feasible flip the closed-form delta and a numeric re-solve on the SAW
    aggregation must agree within the bisection tolerance.
    """
    from beam.mcda.aggregate import weighted_sum
    from beam.mcda.perturbation import _smallest_flip_delta

    polarity = ("higher_is_better", "higher_is_better", "higher_is_better")
    for scores in _seeded_matrices():
        out = smallest_weight_perturbation(scores, polarity, method="saw")
        x = out.base.normalized
        w = out.base.weights
        for p in out.per_pair:
            if p.criterion == -1:
                continue
            if abs(p.delta) > 1.0:
                # The closed form has no range cap; only compare deltas that
                # fall inside the numeric search range.
                continue
            numeric_delta = _smallest_flip_delta(
                x,
                w,
                weighted_sum,
                p.higher,
                p.lower,
                p.criterion,
                search_range=1.0,
                tolerance=1e-9,
            )
            assert numeric_delta is not None
            assert numeric_delta == pytest.approx(p.delta, abs=1e-6)


@pytest.mark.parametrize("method", ["vikor", "promethee_ii"])
def test_numeric_path_finds_flip_on_near_tie(method):
    """The top two tools have a small feasible single-weight flip.

    The top two tools split the criteria (tool 0 leads on criteria 0 and 1,
    tool 1 leads on criterion 2), so shifting weight onto criterion 2 flips
    their order. Tool 2 is far worse and cannot be dislodged.
    """
    scores = np.array(
        [
            [0.80, 0.80, 0.10],
            [0.70, 0.70, 0.95],
            [0.10, 0.05, 0.02],
        ]
    )
    out = smallest_weight_perturbation(scores, ("higher_is_better",) * 3, method=method)
    ranks = out.base.ranks
    top_idx = int(np.where(ranks == 1)[0][0])
    second_idx = int(np.where(ranks == 2)[0][0])
    near_tie = next(p for p in out.per_pair if p.higher == top_idx and p.lower == second_idx)
    assert near_tie.criterion != -1
    assert math.isfinite(near_tie.absolute_delta)
    assert near_tie.absolute_delta < 0.5


@pytest.mark.parametrize("method", ["vikor", "promethee_ii"])
def test_numeric_path_reports_no_flip_for_dominant_tool(method):
    """A strictly dominating tool cannot be displaced by a single-weight change."""
    scores = np.array(
        [
            [0.9, 0.9],
            [0.5, 0.4],
            [0.1, 0.2],
        ]
    )
    out = smallest_weight_perturbation(
        scores, ("higher_is_better", "higher_is_better"), method=method
    )
    top_idx = int(np.argmin(out.base.ranks))
    for p in out.per_pair:
        if p.higher == top_idx:
            assert p.criterion == -1
            assert math.isinf(p.absolute_delta)
    assert out.top_rank_perturbation is None
    assert out.top_rank_is_fragile is False


@pytest.mark.parametrize("method", ["vikor", "promethee_ii"])
def test_numeric_report_fields_stay_consistent(method):
    """most_fragile_pair, top_rank_perturbation and the fragility flag agree with per_pair."""
    out = smallest_weight_perturbation(_toy_scores(), _TOY_POLARITY, method=method)
    feasible = [p for p in out.per_pair if p.criterion != -1]
    if feasible:
        smallest = min(feasible, key=lambda p: p.absolute_delta)
        assert out.most_fragile_pair.absolute_delta == pytest.approx(smallest.absolute_delta)
    top_idx = int(np.argmin(out.base.ranks))
    if out.top_rank_perturbation is not None:
        assert out.top_rank_perturbation.higher == top_idx
        expected = out.top_rank_perturbation.absolute_delta < 0.05
        assert out.top_rank_is_fragile == expected
    else:
        assert out.top_rank_is_fragile is False


def test_rejects_one_dimensional_scores():
    with pytest.raises(ValueError, match="2D"):
        smallest_weight_perturbation(np.array([0.5, 0.7]), ("higher_is_better",))


def test_per_pair_count_matches_n_ranked_pairs():
    """3 tools, distinct composites, give exactly 3 ordered above/below pairs."""
    scores = _toy_scores()
    out = smallest_weight_perturbation(scores, _TOY_POLARITY)
    assert len(out.per_pair) == 3
