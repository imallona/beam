"""Tests for the chance-baseline and noise-floor reference-level checks."""

import math

import numpy as np
import pytest

import beam
from beam.mcda import beats_random_baseline, noise_floor_separation


def test_beats_random_baseline_counts_and_direction():
    # metric 0 higher_is_better, baseline 0; metric 1 lower_is_better, baseline 10.
    scores = np.array(
        [
            [0.5, 5.0],
            [-0.1, 12.0],
            [0.0, 8.0],
        ]
    )
    report = beats_random_baseline(
        scores,
        polarity=["higher_is_better", "lower_is_better"],
        baselines=[0.0, 10.0],
        metric_ids=["ari", "runtime"],
    )
    assert report.active
    assert len(report.per_metric) == 2

    ari = report.per_metric[0]
    assert ari.metric == "ari"
    assert ari.n_observed == 3
    # 0.5 > 0 beats; -0.1 and 0.0 do not (strict).
    assert ari.n_beating == 1
    assert math.isclose(ari.fraction_beating, 1 / 3)

    runtime = report.per_metric[1]
    # 5 < 10 and 8 < 10 beat; 12 does not.
    assert runtime.n_beating == 2

    # tool 1 beats neither metric.
    assert report.tools_never_beating == (1,)


def test_beats_random_baseline_skips_undeclared_and_target():
    scores = np.array([[0.5, 1.0, 9.0], [0.1, 2.0, 11.0]])
    report = beats_random_baseline(
        scores,
        polarity=["higher_is_better", "target_value", "lower_is_better"],
        baselines=[0.0, 1.0, None],
    )
    # Only metric 0 has a usable baseline: target_value and the None are skipped.
    assert len(report.per_metric) == 1
    assert report.per_metric[0].metric is None


def test_beats_random_baseline_ignores_nan_for_observed_count():
    scores = np.array([[0.5, 5.0], [-0.1, np.nan]])
    report = beats_random_baseline(
        scores,
        polarity=["higher_is_better", "lower_is_better"],
        baselines=[0.0, 10.0],
    )
    runtime = report.per_metric[1]
    assert runtime.n_observed == 1
    assert runtime.n_beating == 1
    # tool 1 has an observed score only on metric 1 (NaN there means unobserved),
    # and it does not beat metric 0, so it never beats chance.
    assert report.tools_never_beating == (1,)


def test_beats_random_baseline_inactive_without_baselines():
    scores = np.array([[0.5], [0.1]])
    report = beats_random_baseline(scores, polarity=["higher_is_better"], baselines=[None])
    assert not report.active
    assert report.tools_never_beating == ()


def test_noise_floor_separation_flags_close_pair():
    scores = np.array([[0.50], [0.505], [0.80]])
    report = noise_floor_separation(scores, noise_floors=[0.01], ranks=[2, 3, 1])
    assert report.active
    # pair (0, 1) differs by 0.005 < 0.01, the others differ by far more.
    assert report.indistinguishable_pairs == ((0, 1),)
    pair01 = next(p for p in report.per_pair if (p.a, p.b) == (0, 1))
    assert not pair01.separated
    assert pair01.comparable
    assert math.isclose(pair01.max_ratio, 0.5)
    # the two best-ranked tools are 2 and 0, separated above the floor.
    assert report.top_pair == (2, 0)
    assert not report.top_pair_indistinguishable


def test_noise_floor_separation_flags_top_pair_within_noise():
    scores = np.array([[0.50], [0.505], [0.80]])
    # ranks make the two close tools the top two.
    report = noise_floor_separation(scores, noise_floors=[0.01], ranks=[1, 2, 3])
    assert report.top_pair == (0, 1)
    assert report.top_pair_indistinguishable


def test_noise_floor_separation_unobserved_pair_not_indistinguishable():
    scores = np.array([[0.5], [np.nan]])
    report = noise_floor_separation(scores, noise_floors=[0.01])
    pair = report.per_pair[0]
    assert not pair.comparable
    assert not pair.separated
    assert report.indistinguishable_pairs == ()


def test_noise_floor_separation_inactive_without_floors():
    scores = np.array([[0.5], [0.1]])
    report = noise_floor_separation(scores, noise_floors=[None], ranks=[1, 2])
    assert not report.active
    assert report.per_pair == ()
    assert report.top_pair == (0, 1)
    assert not report.top_pair_indistinguishable


def test_rank_attaches_reference_level_reports():
    # ari declares both a chance baseline (0) and a noise floor (0.01); runtime
    # declares neither, so only ari drives the reference-level checks.
    scores = np.array(
        [
            [0.80, 10.0],
            [0.805, 20.0],
            [-0.10, 5.0],
        ]
    )
    result = beam.rank(
        scores,
        metric_ids=["ari", "runtime"],
        tool_names=["a", "b", "c"],
        sensitivity=False,
    )
    rb = result.random_baseline
    assert rb is not None and rb.active
    assert len(rb.per_metric) == 1
    assert rb.per_metric[0].metric == "ari"
    # tool c has ari -0.1, below chance, and runtime carries no baseline.
    assert "c" in [result.tool_names[i] for i in rb.tools_never_beating]

    nf = result.noise_floor
    assert nf is not None and nf.active
    # tools a and b differ by 0.005 on ari, below the 0.01 floor.
    assert (0, 1) in nf.indistinguishable_pairs


def test_noise_floor_separation_rejects_wrong_length():
    with pytest.raises(ValueError):
        noise_floor_separation(np.array([[0.5, 0.2]]), noise_floors=[0.01])
