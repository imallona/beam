"""Tests for the card-versus-data consistency audit."""

import warnings

import numpy as np
import pytest

import beam
from beam.mcda import card_data_consistency


def _codes(report):
    return sorted(f.code for f in report.findings)


def test_clean_matrix_passes():
    scores = np.array([[0.4, 0.6], [0.9, 0.2], [0.7, 0.8]])
    report = card_data_consistency(
        scores,
        ["higher_is_better", "higher_is_better"],
        [(0.0, 1.0), (0.0, 1.0)],
        metric_ids=["ari", "nmi"],
    )
    assert report.ok
    assert report.findings == ()
    assert report.violations == ()
    assert report.notes == ()


def test_out_of_range_above_and_below():
    # metric 0 has a value above 1; metric 1 has a value below 0.
    scores = np.array([[1.5, 0.3], [0.4, -0.2], [0.6, 0.5]])
    report = card_data_consistency(
        scores,
        ["higher_is_better", "higher_is_better"],
        [(0.0, 1.0), (0.0, 1.0)],
        metric_ids=["acc", "nmi"],
    )
    assert not report.ok
    assert _codes(report) == ["out_of_range", "out_of_range"]
    acc = report.per_metric[0]
    assert acc.n_above_range == 1 and acc.n_below_range == 0
    nmi = report.per_metric[1]
    assert nmi.n_below_range == 1 and nmi.n_above_range == 0
    assert "acc" in report.violations[0].message


def test_unit_mismatch_whole_column_out_of_range():
    # the classic percent-versus-fraction bug: a [0,1] metric reported times 100.
    scores = np.array([[0.4, 40.0], [0.9, 90.0], [0.7, 70.0]])
    report = card_data_consistency(
        scores,
        ["higher_is_better", "higher_is_better"],
        [(0.0, 1.0), (0.0, 1.0)],
        metric_ids=["ari", "nmi"],
    )
    nmi = report.per_metric[1]
    assert nmi.n_above_range == 3
    assert [f.code for f in report.violations] == ["out_of_range"]


def test_open_bounds_skip_the_missing_side():
    # runtime declares a lower bound of 0 and no upper bound; large values pass.
    scores = np.array([[5.0], [2800.0], [120.0]])
    report = card_data_consistency(
        scores,
        ["lower_is_better"],
        [(0.0, None)],
        metric_ids=["runtime"],
    )
    assert report.ok
    # a value below the open-on-top lower bound is still caught.
    scores2 = np.array([[-1.0], [10.0]])
    report2 = card_data_consistency(
        scores2, ["lower_is_better"], [(0.0, None)], metric_ids=["runtime"]
    )
    assert _codes(report2) == ["out_of_range"]
    assert report2.per_metric[0].n_below_range == 1


def test_range_tolerance_absorbs_boundary_roundoff():
    scores = np.array([[1.0 + 1e-9], [0.5]])
    strict = card_data_consistency(scores, ["higher_is_better"], [(0.0, 1.0)])
    assert not strict.ok
    tol = card_data_consistency(scores, ["higher_is_better"], [(0.0, 1.0)], range_tol=1e-6)
    assert tol.ok


def test_malformed_range_is_a_violation():
    scores = np.array([[0.5], [0.6]])
    report = card_data_consistency(scores, ["higher_is_better"], [(1.0, 0.0)])
    assert "malformed_range" in _codes(report)
    assert report.violations[0].severity == "violation"


def test_baseline_outside_range_flagged_and_target_skips_baseline():
    scores = np.array([[0.4], [0.6]])
    report = card_data_consistency(
        scores,
        ["higher_is_better"],
        [(0.0, 1.0)],
        baselines=[2.0],
        metric_ids=["ari"],
    )
    assert [f.code for f in report.violations] == ["baseline_out_of_range"]

    # a target_value metric has no chance level, so a stray baseline is ignored.
    skipped = card_data_consistency(
        scores,
        ["target_value"],
        [(0.0, 1.0)],
        baselines=[2.0],
        metric_ids=["calibration_slope"],
    )
    assert skipped.ok


def test_target_outside_range_flagged():
    scores = np.array([[0.4], [0.6]])
    report = card_data_consistency(
        scores,
        ["target_value"],
        [(0.0, 1.0)],
        targets=[3.0],
        metric_ids=["calibration_slope"],
    )
    assert [f.code for f in report.violations] == ["target_out_of_range"]


def test_nonpositive_noise_floor_is_a_violation():
    scores = np.array([[0.2], [0.8]])
    report = card_data_consistency(
        scores, ["higher_is_better"], [(0.0, 1.0)], noise_floors=[0.0]
    )
    assert [f.code for f in report.violations] == ["nonpositive_noise_floor"]


def test_noise_floor_exceeds_spread_is_a_note():
    # spread is 0.05, floor 0.2: the metric separates no pair of tools.
    scores = np.array([[0.50], [0.55], [0.52]])
    report = card_data_consistency(
        scores, ["higher_is_better"], [(0.0, 1.0)], noise_floors=[0.2], metric_ids=["m"]
    )
    assert report.ok  # a note, not a violation
    assert [f.code for f in report.notes] == ["noise_floor_exceeds_spread"]


def test_degenerate_and_no_observations_are_notes():
    scores = np.array([[0.5, np.nan], [0.5, np.nan], [0.5, np.nan]])
    report = card_data_consistency(
        scores,
        ["higher_is_better", "higher_is_better"],
        [(0.0, 1.0), (0.0, 1.0)],
        metric_ids=["constant", "absent"],
    )
    assert report.ok
    assert _codes(report) == ["degenerate", "no_observations"]
    assert report.per_metric[0].observed_min == report.per_metric[0].observed_max


def test_nan_cells_excluded_from_statistics():
    scores = np.array([[0.4, np.nan], [np.nan, 0.6], [0.7, 0.8]])
    report = card_data_consistency(
        scores, ["higher_is_better", "higher_is_better"], [(0.0, 1.0), (0.0, 1.0)]
    )
    assert report.per_metric[0].n_observed == 2
    assert report.per_metric[1].n_observed == 2
    assert report.ok


def test_shape_and_length_validation():
    with pytest.raises(ValueError, match="2D"):
        card_data_consistency(np.zeros((2, 2, 2)), ["higher_is_better"], [(0.0, 1.0)])
    with pytest.raises(ValueError, match="polarity"):
        card_data_consistency(np.zeros((2, 2)), ["higher_is_better"], [(0.0, 1.0), (0.0, 1.0)])
    with pytest.raises(ValueError, match="bounds"):
        card_data_consistency(
            np.zeros((2, 2)), ["higher_is_better", "higher_is_better"], [(0.0, 1.0)]
        )
    with pytest.raises(ValueError, match="baselines"):
        card_data_consistency(
            np.zeros((2, 2)),
            ["higher_is_better", "higher_is_better"],
            [(0.0, 1.0), (0.0, 1.0)],
            baselines=[0.0],
        )
    with pytest.raises(ValueError, match="range_tol"):
        card_data_consistency(np.zeros((2, 1)), ["higher_is_better"], [(0.0, 1.0)], range_tol=-1.0)


def test_rank_attaches_card_consistency():
    scores = np.array([[0.4, 0.6], [0.9, 0.2], [0.7, 0.8]])
    result = beam.rank(
        scores, metric_ids=["ari", "nmi"], tool_names=["a", "b", "c"], sensitivity=False
    )
    assert result.card_consistency is not None
    assert result.card_consistency.ok


def test_openproblems_clean_and_unit_mismatch_regression():
    # the bundled OpenProblems batch integration scores pass the audit cleanly,
    # and reporting one [0,1] metric times 100 (a percent-versus-fraction bug) is
    # caught as an out-of-range violation naming the metric.
    from beam import datasets
    from beam.mcda import registry_context

    op = datasets.load_openproblems("batch_integration")
    ids = list(op.metric_ids)
    ctx = registry_context(ids, "saw")
    with warnings.catch_warnings():
        # a method unobserved on a metric across every dataset reduces to NaN.
        warnings.simplefilter("ignore", RuntimeWarning)
        matrix = np.nanmean(np.asarray(op.tensor(), float), axis=1)

    clean = card_data_consistency(
        matrix,
        ctx.polarity,
        ctx.bounds,
        baselines=ctx.baselines,
        targets=ctx.targets,
        noise_floors=ctx.noise_floors,
        metric_ids=ids,
    )
    assert clean.ok
    assert clean.findings == ()

    j = ids.index("nmi")
    bug = matrix.copy()
    bug[:, j] *= 100.0
    report = card_data_consistency(
        bug,
        ctx.polarity,
        ctx.bounds,
        baselines=ctx.baselines,
        targets=ctx.targets,
        noise_floors=ctx.noise_floors,
        metric_ids=ids,
    )
    assert [f.code for f in report.violations] == ["out_of_range"]
    assert report.violations[0].metric == "nmi"
    nmi = report.per_metric[j]
    assert nmi.n_above_range == nmi.n_observed
