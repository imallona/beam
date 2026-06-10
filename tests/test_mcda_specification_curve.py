"""Tests for the specification curve over the analyst's choices."""

import numpy as np
import pytest

from beam.mcda import rank_sensitivity, specification_curve


def test_matrix_specification_count():
    scores = np.array([[0.9, 30.0], [0.7, 50.0], [0.5, 40.0], [0.3, 70.0]])
    rs = rank_sensitivity(scores, ["higher_is_better", "lower_is_better"])
    sc = specification_curve(rs)
    assert sc.factors == ("weighting", "aggregation")
    assert sc.dataset_names is None
    assert sc.n_specifications == len(rs.weightings) * len(rs.methods)
    assert len(sc.specifications) == sc.n_specifications
    assert len(sc.curve_order) == sc.n_specifications


def test_each_specification_is_a_full_ordering():
    scores = np.array([[0.9, 30.0], [0.7, 50.0], [0.5, 40.0], [0.3, 70.0]])
    sc = specification_curve(rank_sensitivity(scores, ["higher_is_better", "lower_is_better"]))
    n_tools = scores.shape[0]
    for spec in sc.specifications:
        assert sorted(spec.ordering) == list(range(n_tools))
        assert len(spec.ranks) == n_tools
        # the top tool holds the smallest rank in the spec.
        assert spec.ranks[spec.top_tool] == min(spec.ranks)
        assert spec.ordering[0] == spec.top_tool


def test_most_frequent_top_fraction_matches_rank_sensitivity_headline():
    # the most-frequent-first tool and its fraction reproduce the rank_sensitivity headline.
    d0 = np.array([[0.9, 0.9], [0.5, 0.5], [0.1, 0.1]])
    d1 = np.array([[0.8, 0.8], [0.4, 0.4], [0.2, 0.2]])
    tensor = np.stack([d0, d1], axis=1)
    rs = rank_sensitivity(tensor, ["higher_is_better", "higher_is_better"])
    sc = specification_curve(rs)
    assert sc.most_frequent_top_tool == rs.headline_tool
    assert sc.most_frequent_top_fraction == pytest.approx(rs.headline_top_fraction)


def test_stable_ranking_is_unanimous():
    # one tool dominates on every metric, so every specification agrees.
    scores = np.array([[0.9, 0.9], [0.5, 0.5], [0.1, 0.1]])
    sc = specification_curve(rank_sensitivity(scores, ["higher_is_better", "higher_is_better"]))
    assert sc.most_frequent_top_fraction == pytest.approx(1.0)
    assert sc.n_distinct_top_tools == 1
    assert sc.modal_order_fraction == pytest.approx(1.0)
    assert sc.modal_order == (0, 1, 2)


def test_disagreeing_datasets_split_the_top():
    # two datasets order the tools oppositely, so the top tool flips with the dataset.
    d0 = np.array([[0.9, 0.9], [0.5, 0.5], [0.1, 0.1]])
    d1 = np.array([[0.1, 0.1], [0.5, 0.5], [0.9, 0.9]])
    tensor = np.stack([d0, d1], axis=1)
    rs = rank_sensitivity(tensor, ["higher_is_better", "higher_is_better"])
    sc = specification_curve(rs)
    assert sc.factors == ("weighting", "aggregation", "dataset")
    assert sc.n_distinct_top_tools == 2
    assert sc.most_frequent_top_fraction < 1.0


def test_curve_order_is_sorted_by_most_frequent_top_rank():
    d0 = np.array([[0.9, 0.9], [0.5, 0.5], [0.1, 0.1]])
    d1 = np.array([[0.1, 0.1], [0.5, 0.5], [0.9, 0.9]])
    tensor = np.stack([d0, d1], axis=1)
    sc = specification_curve(rank_sensitivity(tensor, ["higher_is_better", "higher_is_better"]))
    dom = sc.most_frequent_top_tool
    dom_ranks = [sc.specifications[i].ranks[dom] for i in sc.curve_order]
    assert dom_ranks == sorted(dom_ranks)


def test_tool_names_carry_through():
    scores = np.array([[0.9, 30.0], [0.7, 50.0], [0.5, 40.0]])
    rs = rank_sensitivity(
        scores,
        ["higher_is_better", "lower_is_better"],
        tool_names=["a", "b", "c"],
    )
    sc = specification_curve(rs)
    assert sc.tool_names == ("a", "b", "c")
