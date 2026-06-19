"""Tests for the public beam.plot module."""

import numpy as np
import pytest
from matplotlib.figure import Figure

import beam
from beam import plot
from beam.datasets import load_duo2018
from beam.mcda import (
    aggregation_agreement,
    critical_difference,
    normalization_agreement,
    pairwise_superiority,
    pairwise_transitivity,
    rank_sensitivity,
    specification_curve,
)


def _tensor_run(sensitivity=True):
    duo = load_duo2018()
    metric_ids = ("ari", "runtime", "shannon_entropy_diff")
    tensor = duo.tensor(metric_ids)
    complete = duo.complete_methods(metric_ids)
    scores = beam.Scores(
        values=tensor[complete],
        tool_names=tuple(np.array(duo.method_names)[complete].tolist()),
        metric_ids=metric_ids,
        dataset_names=duo.dataset_names,
        layout="long",
    )
    return beam.rank(scores, weights="equal", method="saw", sensitivity=sensitivity)


def _wide_run():
    scores = beam.Scores(
        values=np.array([[0.9, 30.0], [0.7, 50.0], [0.5, 40.0], [0.6, 35.0]]),
        tool_names=("a", "b", "c", "d"),
        metric_ids=("ari", "runtime"),
        dataset_names=None,
        layout="wide",
    )
    return beam.rank(scores, sensitivity=True)


def test_ranking_and_normalized_scores_return_figures():
    run = _wide_run()
    assert isinstance(plot.ranking(run), Figure)
    assert isinstance(plot.normalized_scores(run), Figure)


def test_save_writes_a_file(tmp_path):
    run = _wide_run()
    out = tmp_path / "ranking.png"
    returned = plot.save(plot.ranking(run), str(out))
    assert returned == str(out)
    assert out.stat().st_size > 0


def test_effect_plots_return_figures():
    run = _tensor_run()
    for name in (
        "weighting_effect",
        "aggregation_effect",
        "normalization_effect",
        "dataset_effect",
    ):
        fig = getattr(plot, name)(run)
        assert isinstance(fig, Figure), name


def test_agreement_heatmaps_from_run_and_report():
    run = _wide_run()
    # From a run, the report is computed internally.
    assert isinstance(plot.aggregation_agreement(run), Figure)
    assert isinstance(plot.normalization_agreement(run), Figure)
    # From an explicit report.
    agg = aggregation_agreement(run.matrix, run.context.polarity)
    norm = normalization_agreement(run.matrix, run.context.polarity)
    assert isinstance(plot.aggregation_agreement(agg), Figure)
    assert isinstance(plot.normalization_agreement(norm), Figure)


def test_smaa_requires_sensitivity():
    run = _wide_run()
    assert isinstance(plot.smaa(run), Figure)
    off = beam.rank(run.scores, sensitivity=False)
    with pytest.raises(ValueError, match="no SMAA"):
        plot.smaa(off)


def test_dataset_plots_require_a_tensor():
    wide = _wide_run()
    with pytest.raises(ValueError, match="leave-one-dataset-out"):
        plot.dataset_effect(wide)
    with pytest.raises(ValueError, match="leave-one-dataset-out"):
        plot.dataset_stability(wide)
    run = _tensor_run()
    assert isinstance(plot.dataset_stability(run), Figure)


def test_rank_sensitivity_and_specification_curve_plots():
    run = _tensor_run(sensitivity=False)
    ctx = run.context
    rs = rank_sensitivity(
        run.scores.values,
        ctx.polarity,
        normalization=list(ctx.normalization),
        bounds=list(ctx.bounds),
        baselines=list(ctx.baselines),
        targets=list(ctx.targets),
        dataset_names=run.scores.dataset_names,
        tool_names=run.tool_names,
    )
    assert isinstance(plot.rank_sensitivity(rs), Figure)
    assert isinstance(plot.rank_sensitivity_by_tool(rs), Figure)
    assert isinstance(plot.specification_curve(specification_curve(rs)), Figure)


def test_rank_sensitivity_by_tool_handles_fixed_rank_tool():
    """A tool that never moves is drawn without a stacked bar, not crashed on."""
    rs = rank_sensitivity(
        np.array([[0.95, 0.95], [0.7, 0.5], [0.3, 0.6], [0.1, 0.1]]),
        ["higher_is_better", "higher_is_better"],
        tool_names=("dominant", "b", "c", "worst"),
    )
    assert isinstance(plot.rank_sensitivity_by_tool(rs), Figure)


def test_critical_difference_and_dominance_plots():
    run = _tensor_run(sensitivity=False)
    # A complete tool by dataset matrix on one metric for the per-dataset tests.
    matrix = run.scores.values[:, 0, :]  # tools by datasets on ari
    cd = critical_difference(matrix, tool_names=run.tool_names)
    assert isinstance(plot.critical_difference(cd), Figure)
    sup = pairwise_superiority(matrix, "higher_is_better", method_names=run.tool_names)
    trans = pairwise_transitivity(sup)
    assert isinstance(plot.pairwise_majority(trans), Figure)


def test_funky_heatmap_normalization_panel_adds_an_axis():
    run = _tensor_run()
    base = plot.funky_heatmap(run, show_normalization_consensus=False)
    more = plot.funky_heatmap(run, show_normalization_consensus=True)
    assert len(more.axes) == len(base.axes) + 1


def test_canonical_and_band_critical_difference():
    run = _tensor_run(sensitivity=False)
    matrix = run.scores.values[:, 0, :]
    cd = critical_difference(matrix, tool_names=run.tool_names)
    assert isinstance(plot.critical_difference(cd), Figure)
    assert isinstance(plot.critical_difference_band(cd), Figure)


def test_rank_and_score_heatmaps_and_bump():
    ranks = np.array([[1, 2, 1], [2, 1, 3], [3, 3, 2]])
    assert isinstance(
        plot.rank_heatmap(ranks, ["a", "b", "c"], ["c1", "c2", "c3"], col_label="config"), Figure
    )
    vals = np.array([[10.0, np.nan, 5.0], [3.0, 4.0, 9.0], [1.0, 2.0, np.nan]])
    fig = plot.score_heatmap(
        vals, ["a", "b", "c"], ["d1", "d2", "d3"], log=True, highlight_best_per_col=True
    )
    assert isinstance(fig, Figure)
    assert isinstance(
        plot.rank_bump(("a", "b", "c"), ("x", "y"), np.array([[1, 2], [2, 1], [3, 3]])), Figure
    )


def test_model_effects_and_variance_components_from_a_report():
    from beam.heterogeneity.mixed_effects import MixedEffectsReport

    me = MixedEffectsReport(
        method_names=("a", "b", "c"),
        method_effects=np.array([0.8, 0.6, 0.3]),
        method_effect_se=np.array([0.05, 0.06, 0.04]),
        variance_components={"dataset": 0.7, "dataset:method": 0.1, "Residual": 0.2},
        residuals=np.zeros(3),
        residual_methods=("a", "b", "c"),
        residual_datasets=("d", "d", "d"),
        formula="score ~ method + (1|dataset)",
        formula_kind="main",
        has_replicates=False,
        singular=False,
        n_obs=3,
        n_methods=3,
        n_datasets=1,
        loglik=0.0,
        aic=0.0,
        warnings=(),
    )
    assert isinstance(plot.model_effects(me), Figure)
    assert isinstance(plot.variance_components(me), Figure)


def test_bradley_terry_leaves_from_a_report():
    from beam.heterogeneity.bradley_terry import BradleyTerryTreeReport, BTNode

    node = BTNode(
        id=0,
        terminal=True,
        n=3,
        split_variable=None,
        split_breakpoint=None,
        p_values=None,
        worth=np.array([0.5, 0.3, 0.2]),
        worth_se=np.array([0.1, 0.1, 0.1]),
    )
    bt = BradleyTerryTreeReport(
        method_names=("a", "b", "c"),
        dataset_names=("d1", "d2", "d3"),
        nodes=(node,),
        leaf_assignment=(0, 0, 0),
        global_worth=np.array([0.5, 0.3, 0.2]),
        global_worth_se=np.array([0.1, 0.1, 0.1]),
        did_split=False,
        feature_names=(),
        minsize=2,
        alpha=0.05,
        warnings=(),
    )
    assert isinstance(plot.bradley_terry_leaves(bt), Figure)
