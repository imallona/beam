"""Tests for the bundled M4 forecasting results loader."""

from __future__ import annotations

import numpy as np

import beam
from beam.cards import properties_for
from beam.datasets import M4Forecasting, load_m4


def test_load_returns_dataclass_with_expected_shape():
    m4 = load_m4()
    assert isinstance(m4, M4Forecasting)
    assert len(m4.method_names) == 25
    assert m4.frequency_names == ("Yearly", "Quarterly", "Monthly", "Weekly", "Daily", "Hourly")
    assert m4.metric_ids == ("smape", "mase")
    assert m4.scores.shape == (25, 6, 2)


def test_tensor_is_dense_and_finite():
    m4 = load_m4()
    assert np.isfinite(m4.scores).all()


def test_winner_reproduces_published_overall_figures():
    """Series-count-weighted overall sMAPE/MASE for the winner match the M4 paper."""
    m4 = load_m4()
    smape = m4.tensor(("smape",))[:, :, 0]
    mase = m4.tensor(("mase",))[:, :, 0]
    weights = m4.n_series / m4.n_series.sum()
    winner = m4.method_names.index("Smyl")
    overall_smape = float(smape[winner] @ weights)
    overall_mase = float(mase[winner] @ weights)
    assert abs(overall_smape - 11.374) < 0.01
    assert abs(overall_mase - 1.536) < 0.01


def test_metric_ids_resolve_against_the_registry():
    m4 = load_m4()
    props = properties_for(list(m4.metric_ids))
    assert [p.polarity for p in props] == ["lower_is_better", "lower_is_better"]


def test_tensor_selects_and_orders_metrics():
    m4 = load_m4()
    only_mase = m4.tensor(("mase",))
    assert only_mase.shape == (25, 6, 1)
    np.testing.assert_array_equal(only_mase[:, :, 0], m4.scores[:, :, 1])


def test_runs_through_rank_with_leave_one_dataset_out():
    m4 = load_m4()
    scores = beam.Scores(
        values=m4.tensor(),
        tool_names=m4.method_names,
        metric_ids=m4.metric_ids,
        dataset_names=m4.frequency_names,
        layout="long",
    )
    result = beam.rank(scores, weights="equal", method="saw")
    assert set(result.result.ranks.tolist()) == set(range(1, 26))
    assert result.leave_one_dataset_out is not None
    assert len(result.leave_one_dataset_out.evaluated_datasets) == 6
