"""Tests for the funky heatmap figure (no R needed)."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import numpy as np

import beam
from beam.reporting import funky_heatmap, funky_heatmap_from_run


def test_funky_heatmap_panels_and_order():
    # three methods, four metrics; method b is best, a middle, c worst.
    normalized = np.array([[0.5, 0.5, 0.5, 0.5], [0.9, 0.9, 0.9, 0.9], [0.1, 0.1, 0.1, 0.1]])
    composite = np.array([0.5, 0.9, 0.1])
    ranks = np.array([2, 1, 3])
    methods = ("a", "b", "c")
    metrics = ("m1", "m2", "m3", "m4")

    # without robustness arrays: two panels (heatmap + overall bar).
    fig = funky_heatmap(normalized, methods, metrics, composite, ranks)
    assert len(fig.axes) == 2
    # rows are ordered best first: b, a, c.
    ax_heat = fig.axes[0]
    assert [t.get_text() for t in ax_heat.get_yticklabels()] == ["b", "a", "c"]

    # glyph + composite + leave-one-dataset-out span = three panels.
    fig3 = funky_heatmap(
        normalized,
        methods,
        metrics,
        composite,
        ranks,
        metric_groups=("g1", "g1", "g2", "g2"),
        rank_low=np.array([2, 1, 3]),
        rank_high=np.array([3, 2, 3]),
    )
    assert len(fig3.axes) == 3

    # worth panel and SMAA panel each add a panel; SMAA adds a colorbar axis too.
    fig_all = funky_heatmap(
        normalized,
        methods,
        metrics,
        composite,
        ranks,
        rank_low=np.array([2, 1, 3]),
        rank_high=np.array([3, 2, 3]),
        worth=np.array([0.3, 0.5, 0.2]),
        worth_ci=np.array([0.05, 0.05, 0.05]),
        consensus_low=np.array([2, 1, 3]),
        consensus_high=np.array([2, 1, 3]),
        cliques=(("a", "b"),),
        smaa_acceptability=np.eye(3),
    )
    # glyph, composite, worth, lodo, consensus, smaa panels plus the SMAA colorbar.
    assert len(fig_all.axes) == 7


def test_smaa_colorbar_orientation_matches_bars():
    # The stacked bars colour rank 1 (best) with the bright end of viridis, so the
    # colorbar legend must use the reversed colormap to read the same way. A straight
    # colormap on the legend would put rank 1 at the dark end and invert the reading.
    n = 3
    normalized = np.full((n, 4), 0.5)
    composite = np.array([0.9, 0.5, 0.1])
    ranks = np.array([1, 2, 3])
    fig = funky_heatmap(
        normalized,
        ("a", "b", "c"),
        ("m1", "m2", "m3", "m4"),
        composite,
        ranks,
        smaa_acceptability=np.eye(n),
    )

    smaa_ax = next(ax for ax in fig.axes if ax.get_xlabel().startswith("SMAA rank acceptability"))
    cbar_ax = next(ax for ax in fig.axes if ax.get_ylabel() == "rank (1 best)")

    bright = matplotlib.colormaps["viridis"](1.0)
    bar_colors = [patch.get_facecolor() for patch in smaa_ax.patches]
    assert any(np.allclose(c[:3], bright[:3], atol=1e-6) for c in bar_colors)

    # The colorbar solids must use the reversed colormap so rank value 1 renders
    # with the same bright colour the rank-1 bars use, not the dark end.
    solids = next(a for a in cbar_ax.collections if type(a).__name__ == "QuadMesh")
    assert solids.cmap.name == "viridis_r"
    assert np.allclose(solids.cmap(solids.norm(1.0))[:3], bright[:3], atol=1e-6)
    # The axis is flipped so rank 1 sits at the top (ylim runs high to low).
    ylim = cbar_ax.get_ylim()
    assert ylim[0] > ylim[1]


def test_funky_heatmap_from_run_assembles_panels():
    # a small tensor with two datasets so leave-one-dataset-out runs.
    rng = np.random.default_rng(0)
    tensor = rng.random((4, 2, 3))
    scores = beam.Scores(
        values=tensor,
        tool_names=("w", "x", "y", "z"),
        metric_ids=("ari", "nmi", "runtime"),
        dataset_names=("d0", "d1"),
        layout="long",
    )
    run = beam.rank(scores, weights="equal", method="saw")
    assert run.leave_one_dataset_out is not None and run.smaa is not None
    fig = funky_heatmap_from_run(run, metric_groups=("bio", "bio", "cost"))
    # glyph, composite, leave-one-dataset-out, aggregation consensus, SMAA, plus
    # the SMAA colorbar axis.
    assert len(fig.axes) == 6
