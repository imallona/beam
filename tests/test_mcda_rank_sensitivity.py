"""Tests for the rank-sensitivity variance decomposition."""

import warnings

import numpy as np
import pytest

from beam.mcda import rank_sensitivity
from beam.mcda.rank_sensitivity import _prune_to_complete_grid, _variance_shares


def test_variance_shares_decomposition_identity():
    # a balanced 3x4 table: main effects plus interaction recover the total.
    rng = np.random.default_rng(0)
    table = rng.normal(size=(3, 4))
    ss_total, ss_main, ss_interaction = _variance_shares(table)
    assert ss_total == pytest.approx(sum(ss_main) + ss_interaction)
    assert ss_interaction >= -1e-9


def test_variance_shares_pure_row_effect():
    # rows differ, columns identical: all variance is the first factor, no
    # interaction.
    table = np.array([[1.0, 1.0, 1.0], [5.0, 5.0, 5.0]])
    ss_total, ss_main, ss_interaction = _variance_shares(table)
    assert ss_main[0] == pytest.approx(ss_total)
    assert ss_main[1] == pytest.approx(0.0)
    assert ss_interaction == pytest.approx(0.0)


def test_variance_shares_pure_interaction():
    # additive main effects are zero but the cells vary: a pure interaction.
    table = np.array([[1.0, -1.0], [-1.0, 1.0]])
    ss_total, ss_main, ss_interaction = _variance_shares(table)
    assert ss_main[0] == pytest.approx(0.0)
    assert ss_main[1] == pytest.approx(0.0)
    assert ss_interaction == pytest.approx(ss_total)


def test_matrix_two_factors():
    scores = np.array([[0.9, 30.0], [0.7, 50.0], [0.5, 40.0], [0.3, 70.0]])
    report = rank_sensitivity(scores, ["higher_is_better", "lower_is_better"])
    assert report.factors == ("weighting", "aggregation")
    assert report.dataset_share is None
    assert report.dataset_names is None
    total = sum(report.factor_shares.values()) + report.interaction_share
    assert total == pytest.approx(1.0)
    assert report.ranks.shape[0] == 4
    assert report.most_influential_factor in ("weighting", "aggregation", "interaction")


def test_tensor_adds_dataset_factor():
    # two datasets that order the tools oppositely: the dataset should carry the
    # variance, not the weighting or the aggregation.
    d0 = np.array([[0.9, 0.9], [0.5, 0.5], [0.1, 0.1]])
    d1 = np.array([[0.1, 0.1], [0.5, 0.5], [0.9, 0.9]])
    tensor = np.stack([d0, d1], axis=1)  # (3 tools, 2 datasets, 2 metrics)
    report = rank_sensitivity(
        tensor,
        ["higher_is_better", "higher_is_better"],
        dataset_names=["d0", "d1"],
    )
    assert report.factors == ("weighting", "aggregation", "dataset")
    assert report.dataset_names == ("d0", "d1")
    assert report.ranks.ndim == 4
    total = sum(report.factor_shares.values()) + report.interaction_share
    assert total == pytest.approx(1.0)
    # the dataset flips the order, so it dominates the variance.
    assert report.dataset_share > 0.9
    assert report.most_influential_factor == "dataset"
    assert report.headline_rank_by_dataset is not None
    assert report.headline_rank_by_dataset.shape == (2,)


def test_tensor_no_dataset_effect_when_datasets_agree():
    # identical datasets carry no dataset variance; any rank movement is the
    # modeling choice or its interaction.
    slice_ = np.array([[0.9, 10.0], [0.6, 40.0], [0.2, 80.0], [0.4, 30.0]])
    tensor = np.stack([slice_, slice_], axis=1)
    report = rank_sensitivity(tensor, ["higher_is_better", "lower_is_better"])
    assert report.dataset_share == pytest.approx(0.0, abs=1e-9)


def test_per_tool_shares_sum_to_one_or_nan():
    scores = np.array([[0.9, 30.0], [0.7, 50.0], [0.5, 40.0], [0.3, 70.0]])
    report = rank_sensitivity(scores, ["higher_is_better", "lower_is_better"])
    for tool in report.per_tool:
        total = sum(tool.factor_shares.values()) + tool.interaction_share
        if np.isnan(total):
            assert tool.rank_span == 0
        else:
            assert total == pytest.approx(1.0)
            assert tool.rank_min <= tool.modal_rank <= tool.rank_max


def test_constant_rank_tool_has_nan_shares():
    # tool 0 dominates every metric, so it is rank 1 in every combination.
    scores = np.array([[1.0, 1.0], [0.5, 0.4], [0.2, 0.3], [0.1, 0.05]])
    report = rank_sensitivity(scores, ["higher_is_better", "higher_is_better"])
    top = report.per_tool[0]
    assert top.rank_span == 0
    assert np.isnan(top.interaction_share)


def test_prune_drops_the_worst_level():
    # a 3x3 grid where one whole row failed: that row is dropped, grid stays full.
    success = np.ones((3, 3), dtype=bool)
    success[1, :] = False
    kept = _prune_to_complete_grid(success)
    assert kept[0] == [0, 2]
    assert kept[1] == [0, 1, 2]


def test_too_few_levels_raises():
    # one metric and two tools: every aggregation gives the same trivial order, but
    # a single explicit aggregation leaves no second level to compare.
    scores = np.array([[0.9], [0.1]])
    with pytest.raises(ValueError, match="at least two"):
        rank_sensitivity(scores, ["higher_is_better"], methods=["saw"])


def test_shape_and_length_validation():
    with pytest.raises(ValueError, match=r"2D .* or 3D"):
        rank_sensitivity(np.zeros((2, 2, 2, 2)), ["higher_is_better"])
    with pytest.raises(ValueError, match="polarity"):
        rank_sensitivity(np.zeros((3, 2)), ["higher_is_better"])
    with pytest.raises(ValueError, match="tool_names"):
        rank_sensitivity(
            np.array([[0.9, 0.1], [0.5, 0.5], [0.2, 0.8]]),
            ["higher_is_better", "higher_is_better"],
            tool_names=["a", "b"],
        )


def test_m4_dataset_dominates_regression():
    # the dataset (forecasting frequency) carries almost all the rank variance on
    # M4, far more than the weighting or aggregation choice; the headline method
    # leads on some frequencies and trails on others.
    from beam import datasets
    from beam.mcda import registry_context

    m4 = datasets.load_m4()
    ids = list(m4.metric_ids)
    ctx = registry_context(ids, "saw")
    tensor = np.asarray(m4.tensor(), float)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        report = rank_sensitivity(
            tensor,
            ctx.polarity,
            normalization=list(ctx.normalization),
            bounds=list(ctx.bounds),
            baselines=list(ctx.baselines),
            targets=list(ctx.targets),
            tool_names=list(m4.method_names),
            dataset_names=list(m4.frequency_names),
        )
    assert report.factors == ("weighting", "aggregation", "dataset")
    assert report.dataset_share > 0.8
    assert report.dataset_share > report.weighting_share
    assert report.dataset_share > report.aggregation_share
    assert report.most_influential_factor == "dataset"
    assert report.headline_rank_span >= 1
