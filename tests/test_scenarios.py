"""Ground-truth checks on the canonical simulated scenarios.

Each test pins one qualitative property of one scenario kind so that a
regression in any single pipeline primitive (normalisation, weighting,
aggregation, SMAA, weight perturbation, cross-dataset aggregation)
trips a documented assertion.
"""

from __future__ import annotations

import numpy as np
import pytest

from beam.cards import properties_for
from beam.mcda import (
    aggregate_across_datasets,
    run_from_registry,
    smaa,
    smallest_weight_perturbation,
)
from beam.scenarios import (
    Scenario,
    all_scenarios,
    clear_winner_scenario,
    odd_dataset_scenario,
    random_scenario,
    tied_scenario,
)


def _polarity(scenario: Scenario):
    return [p.polarity for p in properties_for(list(scenario.metric_ids))]


def test_all_scenarios_returns_one_of_each_kind():
    kinds = {s.kind for s in all_scenarios()}
    assert kinds == {"no_signal", "clear_winner", "ties", "odd_dataset"}


def test_all_scenarios_metric_ids_resolve_in_registry():
    """Every metric id named by a scenario must load from the registry."""
    for s in all_scenarios():
        props = properties_for(list(s.metric_ids))
        assert [p.id for p in props] == list(s.metric_ids)


def test_clear_winner_takes_rank_one_under_run_from_registry():
    s = clear_winner_scenario(seed=0)
    out = run_from_registry(s.scores, s.metric_ids)
    assert out.ranks[s.expectation.expected_winner] == 1


def test_clear_winner_takes_rank_one_under_topsis_too():
    s = clear_winner_scenario(seed=0)
    out = run_from_registry(s.scores, s.metric_ids, method="topsis")
    assert out.ranks[s.expectation.expected_winner] == 1


def test_clear_winner_owns_smaa_confidence():
    s = clear_winner_scenario(seed=0)
    report = smaa(s.scores, _polarity(s), n_samples=300, method="saw", seed=0)
    assert report.confidence_factor[s.expectation.expected_winner] == pytest.approx(1.0)


def test_clear_winner_is_not_fragile_under_weight_perturbation():
    s = clear_winner_scenario(seed=0)
    out = smallest_weight_perturbation(s.scores, _polarity(s), weights="equal", method="saw")
    assert out.top_rank_is_fragile is False
    assert out.top_rank_perturbation is None


def test_tied_pair_shares_rank():
    s = tied_scenario(seed=0)
    out = run_from_registry(s.scores, s.metric_ids)
    a, b = s.expectation.tied_pair
    assert out.ranks[a] == out.ranks[b]


def test_tied_pair_shares_rank_under_every_smaa_sample():
    """If two tools have identical scores, every weight vector ranks them together."""
    s = tied_scenario(seed=0)
    report = smaa(s.scores, _polarity(s), n_samples=200, method="saw", seed=0)
    a, b = s.expectation.tied_pair
    np.testing.assert_array_equal(report.sampled_ranks[:, a], report.sampled_ranks[:, b])


def test_random_scenario_has_no_dominant_winner():
    s = random_scenario(n_tools=5, seed=0)
    report = smaa(s.scores, _polarity(s), n_samples=400, method="saw", seed=0)
    assert report.confidence_factor.max() < s.expectation.smaa_winner_confidence_atmost


def test_random_scenario_top_rank_is_fragile():
    s = random_scenario(n_tools=5, seed=0)
    out = smallest_weight_perturbation(
        s.scores,
        _polarity(s),
        weights="equal",
        method="saw",
        fragility_threshold=0.5,
    )
    assert out.top_rank_is_fragile is True


def test_odd_dataset_pooled_winner_is_global_winner():
    s = odd_dataset_scenario(seed=0)
    out = run_from_registry(s.scores, s.metric_ids)
    assert out.ranks[s.expectation.expected_winner] == 1


def test_odd_dataset_winner_differs_from_pooled():
    """On the last (odd) dataset, the odd-dataset winner takes top rank on both metrics."""
    s = odd_dataset_scenario(seed=0)
    assert s.scores_per_dataset is not None
    odd_idx = s.scores_per_dataset.shape[1] - 1
    ari_per_tool = s.scores_per_dataset[:, odd_idx, 0]
    runtime_per_tool = s.scores_per_dataset[:, odd_idx, 1]
    assert ari_per_tool.argmax() != s.expectation.expected_winner
    assert runtime_per_tool.argmin() != s.expectation.expected_winner


def test_odd_dataset_geometric_mean_used_for_runtime():
    """The pooled runtime column for the global winner reflects geometric mean across datasets."""
    s = odd_dataset_scenario(seed=0)
    tensor = s.scores_per_dataset
    pooled_runtime = aggregate_across_datasets(tensor[:, :, 1], rule="geometric_mean")
    np.testing.assert_allclose(s.scores[:, 1], pooled_runtime)


def test_odd_dataset_arithmetic_mean_used_for_ari():
    s = odd_dataset_scenario(seed=0)
    tensor = s.scores_per_dataset
    pooled_ari = aggregate_across_datasets(tensor[:, :, 0], rule="arithmetic_mean")
    np.testing.assert_allclose(s.scores[:, 0], pooled_ari)


def test_random_winner_distribution_across_seeds_is_not_concentrated():
    """Across many seeds, no single method should win more than 60 percent of the time."""
    n_trials = 50
    n_tools = 5
    winners = []
    for s_seed in range(n_trials):
        s = random_scenario(n_tools=n_tools, seed=s_seed)
        out = run_from_registry(s.scores, s.metric_ids)
        winners.append(int(np.argmin(out.ranks)))
    counts = np.bincount(winners, minlength=n_tools)
    assert counts.max() <= int(0.6 * n_trials)
