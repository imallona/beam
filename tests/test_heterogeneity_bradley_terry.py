"""Tests for the Bradley-Terry tree heterogeneity diagnostic.

The pairwise-comparison construction and the report dataclass are pure Python
and run everywhere. The tree fits need R with psychotree and are skipped when
that toolchain is absent.
"""

from __future__ import annotations

import numpy as np
import pytest

from beam.datasets import (
    load_duo2018,
    load_duo2018_features,
    load_openproblems,
    load_openproblems_svg_features,
)
from beam.heterogeneity import (
    BradleyTerryTreeReport,
    BTNode,
    bradley_terry_tree,
    bttree_available,
    paired_comparisons,
)

HAVE_R = bttree_available()
needs_r = pytest.mark.skipif(not HAVE_R, reason="Rscript with psychotree not available")


def test_bttree_available_returns_bool():
    assert isinstance(bttree_available(), bool)


def test_paired_comparisons_higher_is_better():
    # rows are methods, columns are datasets.
    matrix = np.array([[3.0, 1.0], [2.0, 2.0], [1.0, 3.0]])
    comparisons, pairs = paired_comparisons(matrix, "higher_is_better")
    assert pairs == [(0, 1), (0, 2), (1, 2)]
    # dataset 0: method 0 beats both; dataset 1: method 0 loses both.
    np.testing.assert_array_equal(comparisons, np.array([[1.0, 1.0, 1.0], [-1.0, -1.0, -1.0]]))


def test_paired_comparisons_polarity_flips_sign():
    matrix = np.array([[3.0, 1.0], [2.0, 2.0], [1.0, 3.0]])
    higher, _ = paired_comparisons(matrix, "higher_is_better")
    lower, _ = paired_comparisons(matrix, "lower_is_better")
    np.testing.assert_array_equal(lower, -higher)


def test_paired_comparisons_missing_and_tie():
    matrix = np.array([[np.nan, 5.0], [1.0, 5.0], [2.0, 9.0]])
    comparisons, _ = paired_comparisons(matrix, "higher_is_better")
    # dataset 0: method 0 missing, so its two comparisons are nan; (1,2) decided.
    assert np.isnan(comparisons[0, 0])
    assert np.isnan(comparisons[0, 1])
    assert comparisons[0, 2] == -1.0  # method 2 (score 2) beats method 1 (score 1)
    # dataset 1: methods 0 and 1 tie at 5; both lose to method 2 at 9.
    assert comparisons[1, 0] == 0.0
    assert comparisons[1, 1] == -1.0
    assert comparisons[1, 2] == -1.0


def test_paired_comparisons_validation():
    with pytest.raises(ValueError, match="polarity"):
        paired_comparisons(np.zeros((2, 2)), "bigger_is_better")
    with pytest.raises(ValueError, match="2D"):
        paired_comparisons(np.zeros((2, 2, 2)), "higher_is_better")
    with pytest.raises(ValueError, match="at least 2 methods"):
        paired_comparisons(np.zeros((1, 4)), "higher_is_better")


def test_tree_input_validation():
    matrix = np.zeros((3, 4))
    with pytest.raises(ValueError, match="method_names"):
        bradley_terry_tree(matrix, ["a", "b"], ["d0", "d1", "d2", "d3"], {"x": [1, 2, 3, 4]})
    with pytest.raises(ValueError, match="dataset_names"):
        bradley_terry_tree(matrix, ["a", "b", "c"], ["d0"], {"x": [1, 2, 3, 4]})
    with pytest.raises(ValueError, match="at least one dataset feature"):
        bradley_terry_tree(matrix, ["a", "b", "c"], ["d0", "d1", "d2", "d3"])
    with pytest.raises(ValueError, match="feature 'x'"):
        bradley_terry_tree(matrix, ["a", "b", "c"], ["d0", "d1", "d2", "d3"], {"x": [1, 2]})


def _manual_report(did_split: bool) -> BradleyTerryTreeReport:
    """A small hand-built report for testing the dataclass logic without R."""
    methods = ("m0", "m1", "m2")
    datasets = ("d0", "d1", "d2", "d3")
    global_worth = np.array([0.5, 0.3, 0.2])
    if not did_split:
        nodes = (BTNode(1, True, 4, None, None, None, global_worth, np.array([0.05, 0.05, 0.05])),)
        return BradleyTerryTreeReport(
            methods,
            datasets,
            nodes,
            (1, 1, 1, 1),
            global_worth,
            np.array([0.05, 0.05, 0.05]),
            False,
            ("regime",),
            5,
            0.05,
            (),
        )
    nodes = (
        BTNode(1, False, None, "regime", None, {"regime": 0.01}, None, None),
        BTNode(2, True, 2, None, None, None, np.array([0.6, 0.3, 0.1]), np.array([0.1, 0.1, 0.1])),
        BTNode(3, True, 2, None, None, None, np.array([0.1, 0.3, 0.6]), np.array([0.1, 0.1, 0.1])),
    )
    return BradleyTerryTreeReport(
        methods,
        datasets,
        nodes,
        (2, 2, 3, 3),
        global_worth,
        np.array([0.05, 0.05, 0.05]),
        True,
        ("regime",),
        5,
        0.05,
        (),
    )


def test_report_global_and_node_ranking():
    rep = _manual_report(did_split=True)
    assert rep.global_ranking() == ["m0", "m1", "m2"]
    assert rep.node_ranking(2)[0] == "m0"
    assert rep.node_ranking(3)[0] == "m2"
    assert rep.datasets_in_node(3) == ["d2", "d3"]


def test_report_reversed_leaves():
    rep = _manual_report(did_split=True)
    # leaf 3 is led by m2, not the global top m0; leaf 2 keeps m0.
    assert rep.reversed_leaves() == [3]
    assert len(rep.terminal_nodes) == 2
    assert len(rep.inner_nodes) == 1


def test_report_node_ranking_rejects_inner_node():
    rep = _manual_report(did_split=True)
    with pytest.raises(KeyError, match="not a terminal node"):
        rep.node_ranking(1)


def test_report_summary_split_mentions_reversal():
    rep = _manual_report(did_split=True)
    text = rep.summary()
    assert "splits" in text
    assert "regime" in text
    assert "m2" in text  # the reversed leaf's leader is surfaced


def test_report_summary_no_split_is_honest():
    rep = _manual_report(did_split=False)
    text = rep.summary()
    assert "no dataset feature" in text
    assert "m0" in text  # the flat ranking's leader


def _regime_matrix(seed: int):
    """16 datasets in two regimes that reverse the method ordering.

    Methods m0 and m2 swap dominance between the low and high regime; m1 sits
    in the middle. The added noise keeps the within-regime comparisons from
    being perfectly separable.
    """
    rng = np.random.default_rng(seed)
    n_low = n_high = 8
    means_low = np.array([1.0, 0.0, -1.0])
    means_high = np.array([-1.0, 0.0, 1.0])
    cols = []
    regime = []
    for _ in range(n_low):
        cols.append(means_low + rng.normal(0.0, 0.5, size=3))
        regime.append("low")
    for _ in range(n_high):
        cols.append(means_high + rng.normal(0.0, 0.5, size=3))
        regime.append("high")
    matrix = np.column_stack(cols)
    return matrix, regime


@needs_r
def test_tree_finds_regime_split():
    matrix, regime = _regime_matrix(seed=0)
    n_datasets = matrix.shape[1]
    datasets = [f"d{j}" for j in range(n_datasets)]
    rep = bradley_terry_tree(
        matrix,
        ["m0", "m1", "m2"],
        datasets,
        categorical_features={"regime": regime},
        polarity="higher_is_better",
        minsize=4,
    )
    assert rep.did_split
    assert len(rep.terminal_nodes) == 2
    # Each leaf is one regime; the leaders swap.
    leaders = set()
    for node in rep.terminal_nodes:
        members = rep.datasets_in_node(node.id)
        member_regimes = {regime[int(d[1:])] for d in members}
        assert len(member_regimes) == 1  # leaves are pure by regime
        leaders.add(rep.node_ranking(node.id)[0])
    assert leaders == {"m0", "m2"}
    assert rep.reversed_leaves()  # the pooled top does not hold everywhere


@needs_r
def test_tree_on_duo_ari_runs():
    duo = load_duo2018()
    features = load_duo2018_features()
    ari = duo.tensor(("ari",))[:, :, 0]
    numeric, categorical = features.aligned_to(duo.dataset_names)
    rep = bradley_terry_tree(
        ari,
        duo.method_names,
        duo.dataset_names,
        numeric_features=numeric,
        categorical_features=categorical,
        polarity="higher_is_better",
        minsize=4,
    )
    assert isinstance(rep, BradleyTerryTreeReport)
    assert len(rep.leaf_assignment) == 12
    assert rep.global_worth.shape == (14,)
    # SC3 and Seurat lead the ARI comparisons, consistent with findings 0001.
    assert rep.global_ranking()[0] in {"SC3", "Seurat"}
    # The summary is a non-empty plain-language paragraph either way.
    assert len(rep.summary()) > 0


@needs_r
def test_tree_splits_openproblems_svg():
    # The 50-dataset spatially-variable-genes task has enough datasets and real
    # feature variation for the tree to find a split, unlike the 12-dataset Duo.
    svg = load_openproblems("spatially_variable_genes")
    feats = load_openproblems_svg_features()
    matrix = svg.tensor(("correlation",))[:, :, 0]
    _, categorical = feats.aligned_to(svg.dataset_names)

    rep = bradley_terry_tree(
        matrix,
        svg.method_names,
        svg.dataset_names,
        categorical_features=categorical,
        polarity="higher_is_better",
        minsize=6,
    )
    assert rep.did_split
    assert len(rep.terminal_nodes) >= 2
    # spark_x leads the pooled ranking but not every leaf: the best method
    # depends on the spatial assay, which is the heterogeneity the tree exists
    # to surface.
    assert rep.global_ranking()[0] == "spark_x"
    assert rep.reversed_leaves()
    split_vars = {n.split_variable for n in rep.inner_nodes}
    assert "technology" in split_vars
