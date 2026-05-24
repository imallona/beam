"""Ground-truth checks on the canonical simulated scenarios.

Each test pins one qualitative property of one scenario kind so that a
regression in any single pipeline primitive (normalization, weighting,
aggregation, SMAA, weight perturbation, cross-dataset aggregation)
trips a documented assertion.
"""

from __future__ import annotations

import numpy as np
import pytest

from beam.cards import properties_for
from beam.mcda import (
    aggregate_across_datasets,
    run,
    run_from_registry,
    smaa,
    smallest_weight_perturbation,
)
from beam.scenarios import (
    Scenario,
    TransportationBenchmark,
    all_scenarios,
    chance_baseline_scenario,
    dominant_method_scenario,
    normalization_failure_scenarios,
    odd_dataset_scenario,
    outlier_runtime_scenario,
    random_scenario,
    tied_scenario,
    transportation_benchmark,
)


def _polarity(scenario: Scenario):
    return [p.polarity for p in properties_for(list(scenario.metric_ids))]


def _unguarded_minmax(scenario: Scenario):
    """Run a scenario forcing plain min-max on every column, the behaviour the
    card-driven defaults are meant to improve on."""
    bounds = [(p.range_lower, p.range_upper) for p in properties_for(list(scenario.metric_ids))]
    return run(
        scenario.scores,
        _polarity(scenario),
        normalization="min_max",
        bounds=bounds,
        metric_ids=list(scenario.metric_ids),
    )


def test_all_scenarios_returns_one_of_each_kind():
    kinds = {s.kind for s in all_scenarios()}
    assert kinds == {"no_signal", "dominant", "ties", "odd_dataset"}


def test_all_scenarios_metric_ids_resolve_in_registry():
    """Every metric id named by a scenario must load from the registry."""
    for s in all_scenarios():
        props = properties_for(list(s.metric_ids))
        assert [p.id for p in props] == list(s.metric_ids)


def test_dominant_takes_rank_one_under_run_from_registry():
    s = dominant_method_scenario(seed=0)
    out = run_from_registry(s.scores, s.metric_ids)
    assert out.ranks[s.expectation.expected_top_ranked] == 1


def test_dominant_takes_rank_one_under_topsis_too():
    s = dominant_method_scenario(seed=0)
    out = run_from_registry(s.scores, s.metric_ids, method="topsis")
    assert out.ranks[s.expectation.expected_top_ranked] == 1


def test_dominant_owns_smaa_confidence():
    s = dominant_method_scenario(seed=0)
    report = smaa(s.scores, _polarity(s), n_samples=300, method="saw", seed=0)
    assert report.confidence_factor[s.expectation.expected_top_ranked] == pytest.approx(1.0)


def test_dominant_is_not_fragile_under_weight_perturbation():
    s = dominant_method_scenario(seed=0)
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


def test_random_scenario_has_no_clear_top_performer():
    s = random_scenario(n_tools=5, seed=0)
    report = smaa(s.scores, _polarity(s), n_samples=400, method="saw", seed=0)
    assert report.confidence_factor.max() < s.expectation.smaa_top_confidence_atmost


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


def test_odd_dataset_pooled_top_is_global_top():
    s = odd_dataset_scenario(seed=0)
    out = run_from_registry(s.scores, s.metric_ids)
    assert out.ranks[s.expectation.expected_top_ranked] == 1


def test_odd_dataset_top_differs_from_pooled():
    """On the last (odd) dataset, the odd-dataset method is best on both metrics."""
    s = odd_dataset_scenario(seed=0)
    assert s.scores_per_dataset is not None
    odd_idx = s.scores_per_dataset.shape[1] - 1
    ari_per_tool = s.scores_per_dataset[:, odd_idx, 0]
    runtime_per_tool = s.scores_per_dataset[:, odd_idx, 1]
    assert ari_per_tool.argmax() != s.expectation.expected_top_ranked
    assert runtime_per_tool.argmin() != s.expectation.expected_top_ranked


def test_odd_dataset_geometric_mean_used_for_runtime():
    """Pooled runtime for the best-overall method uses geometric mean across datasets."""
    s = odd_dataset_scenario(seed=0)
    tensor = s.scores_per_dataset
    pooled_runtime = aggregate_across_datasets(tensor[:, :, 1], rule="geometric_mean")
    np.testing.assert_allclose(s.scores[:, 1], pooled_runtime)


def test_odd_dataset_arithmetic_mean_used_for_ari():
    s = odd_dataset_scenario(seed=0)
    tensor = s.scores_per_dataset
    pooled_ari = aggregate_across_datasets(tensor[:, :, 0], rule="arithmetic_mean")
    np.testing.assert_allclose(s.scores[:, 0], pooled_ari)


def test_random_top_distribution_across_seeds_is_not_concentrated():
    """Across many seeds, no single method comes out on top more than 60% of the time."""
    n_trials = 50
    n_tools = 5
    tops = []
    for s_seed in range(n_trials):
        s = random_scenario(n_tools=n_tools, seed=s_seed)
        out = run_from_registry(s.scores, s.metric_ids)
        tops.append(int(np.argmin(out.ranks)))
    counts = np.bincount(tops, minlength=n_tools)
    assert counts.max() <= int(0.6 * n_trials)


def test_normalization_failure_scenarios_kinds():
    kinds = {s.kind for s in normalization_failure_scenarios()}
    assert kinds == {"minmax_heavy_tail", "minmax_chance_baseline"}


def test_outlier_runtime_flips_the_top_ranked():
    """Unguarded min-max ranks m1 first because the outlier hides the runtime
    ladder; the card default log_min_max ranks the genuinely fastest good
    method m0 first."""
    s = outlier_runtime_scenario()
    unguarded = _unguarded_minmax(s)
    guarded = run_from_registry(s.scores, s.metric_ids)
    assert int(np.argmin(unguarded.ranks)) == 1
    assert int(np.argmin(guarded.ranks)) == s.expectation.expected_top_ranked == 0


def test_outlier_runtime_minmax_collapses_the_ladder():
    """The four good methods are spread out under log_min_max but crushed
    together under min-max anchored on the outlier."""
    s = outlier_runtime_scenario()
    unguarded = _unguarded_minmax(s)
    guarded = run_from_registry(s.scores, s.metric_ids)
    good = slice(0, 4)
    minmax_spread = np.ptp(unguarded.normalized[good, 1])
    log_spread = np.ptp(guarded.normalized[good, 1])
    assert minmax_spread < 0.05
    assert log_spread > 0.25


def test_outlier_runtime_raises_the_guard_warnings():
    s = outlier_runtime_scenario()
    unguarded = _unguarded_minmax(s)
    assert any("heavy-tailed" in w for w in unguarded.warnings)
    assert any("empirical upper bound" in w for w in unguarded.warnings)
    # the card default uses log_min_max, so no min-max warning is raised
    guarded = run_from_registry(s.scores, s.metric_ids)
    assert guarded.warnings == ()


def test_chance_baseline_flips_a_pair():
    """Unguarded min-max ranks the chance method m0 above the modestly better
    m1; baseline_relative restores the correct order."""
    s = chance_baseline_scenario()
    unguarded = _unguarded_minmax(s)
    guarded = run_from_registry(s.scores, s.metric_ids)
    assert unguarded.ranks[0] < unguarded.ranks[1]
    assert guarded.ranks[1] < guarded.ranks[0]
    assert int(np.argmin(guarded.ranks)) == s.expectation.expected_top_ranked == 2


def test_chance_baseline_value_difference():
    """Min-max scores chance ARI at the column midpoint; baseline_relative at 0."""
    s = chance_baseline_scenario()
    unguarded = _unguarded_minmax(s)
    guarded = run_from_registry(s.scores, s.metric_ids)
    assert unguarded.normalized[0, 0] == pytest.approx(0.5)
    assert guarded.normalized[0, 0] == pytest.approx(0.0)


def test_empirical_bound_makes_runtime_unstable_under_minmax():
    """Adding the outlier changes the normalized runtime of a shared method
    under min-max, the instability the empirical-bound warning flags."""
    s = outlier_runtime_scenario()
    bounds = [(0.0, None)]
    full = run(s.scores[:, 1:2], ["lower_is_better"], normalization="min_max", bounds=bounds)
    without_outlier = run(
        s.scores[:4, 1:2], ["lower_is_better"], normalization="min_max", bounds=bounds
    )
    # m0's normalized runtime swings widely when the method set changes
    assert abs(full.normalized[0, 0] - without_outlier.normalized[0, 0]) > 0.1


def test_transportation_benchmark_shape_and_metrics():
    b = transportation_benchmark()
    assert isinstance(b, TransportationBenchmark)
    assert b.scores.shape == (len(b.mode_names), len(b.terrain_names), len(b.metric_names))
    assert b.metric_names == ("speed", "cost", "co2")
    assert b.polarity == ("higher_is_better", "lower_is_better", "lower_is_better")


def test_transportation_infeasible_cells_are_nan():
    b = transportation_benchmark()
    feas = b.feasible()
    m = b.mode_names.index
    t = b.terrain_names.index
    assert not feas[m("boat"), t("mud")]  # a boat does not run off-road
    assert not feas[m("plane"), t("urban_hop")]  # a small plane does not do urban hops
    assert feas[m("boat"), t("open_water")]
    assert feas[m("plane"), t("long_distance")]
    assert not feas[m("trail_running"), t("open_water")]  # trail running cannot cross water
    assert feas[m("trail_running"), t("mud")]
    assert not feas[m("e_bike"), t("open_water")]  # an e-bike cannot cross water
    assert feas[m("e_bike"), t("flat_road")]
    assert feas[m("kayak"), t("open_water")]  # a kayak is a water mode
    assert not feas[m("kayak"), t("flat_road")]  # a kayak does not run on dry land


def test_transportation_no_mode_runs_on_every_terrain():
    """The point of the example: a single global ranking is not well defined."""
    b = transportation_benchmark()
    assert not b.feasible().all(axis=1).any()


def test_transportation_fastest_mode_per_terrain():
    b = transportation_benchmark()
    speed = b.metric("speed")
    fastest = {
        b.terrain_names[t]: b.mode_names[int(np.nanargmax(speed[:, t]))]
        for t in range(len(b.terrain_names))
    }
    assert fastest["flat_road"] == "train"
    assert fastest["mud"] == "motorcycle"
    assert fastest["uphill"] == "motorcycle"
    assert fastest["open_water"] == "boat"
    assert fastest["long_distance"] == "plane"
    assert fastest["urban_hop"] == "train"


def test_transportation_trail_running_crosses_over_road_running():
    """Trail running is slower than road running on the flat road but faster on
    mud and uphill: the within-terrain crossover the example illustrates."""
    b = transportation_benchmark()
    speed = b.metric("speed")
    m = b.mode_names.index
    t = b.terrain_names.index
    road = m("running")
    trail = m("trail_running")
    assert speed[trail, t("flat_road")] < speed[road, t("flat_road")]
    assert speed[trail, t("mud")] > speed[road, t("mud")]
    assert speed[trail, t("uphill")] > speed[road, t("uphill")]


def test_transportation_e_bike_crosses_over_bicycle():
    """An e-bike is faster than a bicycle on the flat road and the urban hop but
    slower uphill, a second within-terrain crossover among the light modes."""
    b = transportation_benchmark()
    speed = b.metric("speed")
    m = b.mode_names.index
    t = b.terrain_names.index
    bike = m("bicycle")
    ebike = m("e_bike")
    assert speed[ebike, t("flat_road")] > speed[bike, t("flat_road")]
    assert speed[ebike, t("urban_hop")] > speed[bike, t("urban_hop")]
    assert speed[ebike, t("uphill")] < speed[bike, t("uphill")]


def test_transportation_kayak_outranks_boat_on_cost_and_co2():
    """The kayak is slower than the motorboat on open water but cheaper and zero
    CO2, so it outranks the boat on cost and CO2 while losing on speed."""
    b = transportation_benchmark()
    m = b.mode_names.index
    t = b.terrain_names.index
    speed = b.metric("speed")
    cost = b.metric("cost")
    co2 = b.metric("co2")
    kayak = m("kayak")
    boat = m("boat")
    water = t("open_water")
    assert speed[kayak, water] < speed[boat, water]
    assert cost[kayak, water] < cost[boat, water]
    assert co2[kayak, water] < co2[boat, water]


def test_transportation_single_terrain_mcda_runs():
    """On long distance every mode is feasible, so the MCDA pipeline runs there."""
    b = transportation_benchmark()
    lt = b.terrain_names.index("long_distance")
    out = run(
        b.scores[:, lt, :],
        b.polarity,
        normalization=list(b.normalization),
        method="saw",
        metric_ids=list(b.metric_names),
    )
    assert out.ranks.shape == (len(b.mode_names),)
    assert set(out.ranks.tolist()) == set(range(1, len(b.mode_names) + 1))


def test_transportation_feasible_submatrix_drops_nan_rows():
    """The submatrix on a terrain keeps only the feasible modes and is NaN-free."""
    b = transportation_benchmark()
    names, sub = b.feasible_submatrix("open_water")
    assert names == ("kayak", "boat", "plane")
    assert sub.shape == (3, len(b.metric_names))
    assert not np.isnan(sub).any()


def test_transportation_feasible_submatrix_full_on_long_distance():
    """Every mode is feasible on long distance, so the submatrix keeps all rows."""
    b = transportation_benchmark()
    names, sub = b.feasible_submatrix("long_distance")
    assert names == b.mode_names
    assert sub.shape == (len(b.mode_names), len(b.metric_names))
    assert not np.isnan(sub).any()


def test_transportation_feasible_submatrix_runs_through_mcda():
    """The dropped-NaN submatrix is directly consumable by run()."""
    b = transportation_benchmark()
    names, sub = b.feasible_submatrix("open_water")
    out = run(
        sub,
        b.polarity,
        normalization=list(b.normalization),
        method="saw",
        metric_ids=list(b.metric_names),
    )
    assert out.ranks.shape == (len(names),)
    assert set(out.ranks.tolist()) == set(range(1, len(names) + 1))


def test_transportation_feasible_submatrix_rejects_unknown_terrain():
    b = transportation_benchmark()
    with pytest.raises(ValueError, match="unknown terrain"):
        b.feasible_submatrix("space")


def test_transportation_common_feasible_block_ground_modes():
    """The four ground modes share five terrains; open water is excluded."""
    b = transportation_benchmark()
    block_modes = ("foot", "running", "bicycle", "motorcycle")
    terrains, block = b.common_feasible_block(block_modes)
    assert set(terrains) == {"flat_road", "mud", "uphill", "long_distance", "urban_hop"}
    assert "open_water" not in terrains
    assert block.shape == (len(block_modes), len(terrains))
    assert not np.isnan(block).any()


def test_transportation_common_feasible_block_rejects_unknown_mode():
    b = transportation_benchmark()
    with pytest.raises(ValueError, match="unknown mode"):
        b.common_feasible_block(("foot", "rocket"))


def test_transportation_common_feasible_block_water_and_land_share_only_long_distance():
    """A boat and a land mode overlap only on long distance, the one terrain both run on."""
    b = transportation_benchmark()
    terrains, block = b.common_feasible_block(("boat", "train"))
    assert terrains == ("long_distance",)
    assert block.shape == (2, 1)
