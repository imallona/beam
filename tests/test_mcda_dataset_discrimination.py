"""Tests for the dataset-discrimination and difficulty-concordance diagnostics."""

import numpy as np
import pytest

from beam.mcda import (
    DatasetDiscriminationReport,
    DifficultyConcordanceReport,
    dataset_discrimination,
    difficulty_concordance,
)

HB = "higher_is_better"
LB = "lower_is_better"


def _spread_apart_vs_tied():
    """Two datasets: one separates the methods, one ties them.

    Three methods, two metrics, all higher_is_better. Dataset 0 spreads the
    methods (0.1, 0.5, 0.9 on both metrics); dataset 1 ties them (0.5 each).
    """
    scores = np.array(
        [
            [[0.1, 0.1], [0.5, 0.5]],  # method 0
            [[0.5, 0.5], [0.5, 0.5]],  # method 1
            [[0.9, 0.9], [0.5, 0.5]],  # method 2
        ]
    )
    polarity = [HB, HB]
    return scores, polarity


def test_separating_dataset_has_higher_spread():
    scores, polarity = _spread_apart_vs_tied()
    report = dataset_discrimination(scores, polarity, dataset_ids=["spread", "tied"])

    assert isinstance(report, DatasetDiscriminationReport)
    assert report.spread[0] > report.spread[1]
    assert report.spread[1] == pytest.approx(0.0, abs=1e-9)
    assert report.most_discriminating == "spread"
    assert report.least_discriminating == "tied"
    # The separating dataset is first in the spread order.
    assert report.order[0] == 0


def test_agreeing_metrics_give_high_kendall_w():
    # Two metrics ranking three methods identically -> W = 1.
    scores = np.array(
        [
            [[0.1, 0.2]],
            [[0.5, 0.6]],
            [[0.9, 0.8]],
        ]
    )
    report = dataset_discrimination(scores, [HB, HB], dataset_ids=["d"])
    assert report.kendall_w[0] == pytest.approx(1.0)
    assert report.n_methods_used[0] == 3
    assert report.n_metrics_used[0] == 2


def test_disagreeing_metrics_give_low_kendall_w():
    # Two metrics with opposite orderings -> minimal concordance.
    scores = np.array(
        [
            [[0.1, 0.9]],
            [[0.5, 0.5]],
            [[0.9, 0.1]],
        ]
    )
    report = dataset_discrimination(scores, [HB, HB], dataset_ids=["d"])
    assert report.kendall_w[0] == pytest.approx(0.0, abs=1e-9)


def test_polarity_orientation():
    # A lower_is_better second metric that, once oriented, agrees with the first.
    scores = np.array(
        [
            [[0.1, 0.9]],
            [[0.5, 0.5]],
            [[0.9, 0.1]],
        ]
    )
    report = dataset_discrimination(scores, [HB, LB], dataset_ids=["d"])
    assert report.kendall_w[0] == pytest.approx(1.0)


def test_missing_cells_not_imputed():
    scores, polarity = _spread_apart_vs_tied()
    scores[0, 0, 0] = np.nan  # drop one cell of the separating dataset
    report = dataset_discrimination(scores, polarity, dataset_ids=["spread", "tied"])
    # Still computed from the available cells, no crash, spread finite.
    assert np.isfinite(report.spread[0])


def test_too_few_methods_gives_nan_w():
    scores = np.array([[[0.1, 0.2]], [[0.9, 0.8]]])  # two methods
    report = dataset_discrimination(scores, [HB, HB], dataset_ids=["d"], min_methods=3)
    assert np.isnan(report.kendall_w[0])
    # Spread is still defined for two methods.
    assert np.isfinite(report.spread[0])


def test_constant_metric_dropped_from_pool():
    # A metric constant across every cell carries no separation; the spread comes
    # from the informative metric alone.
    scores = np.array(
        [
            [[0.1, 0.5], [0.5, 0.5]],
            [[0.9, 0.5], [0.5, 0.5]],
        ]
    )
    report = dataset_discrimination(scores, [HB, HB], dataset_ids=["a", "b"])
    assert report.spread[0] > report.spread[1]


def test_discrimination_input_validation():
    with pytest.raises(ValueError):
        dataset_discrimination(np.zeros((3, 4)), [HB])  # 2D
    with pytest.raises(ValueError):
        dataset_discrimination(np.zeros((2, 2, 3)), [HB])  # polarity len


def test_difficulty_concordance_shared_vs_specific():
    # Family A and B agree on which datasets are easy/hard -> high concordance.
    rng = np.random.default_rng(0)
    base = np.array([0.2, 0.4, 0.6, 0.8])  # per-dataset difficulty, shared
    scores = np.zeros((4, 4, 1))
    for m in range(4):
        scores[m, :, 0] = base + rng.normal(0, 0.01, 4)
    families = ["A", "A", "B", "B"]
    report = difficulty_concordance(
        scores, [HB], families, dataset_ids=list("wxyz"), min_pairwise=3
    )
    assert isinstance(report, DifficultyConcordanceReport)
    assert report.family_names == ("A", "B")
    assert report.concordance[0, 1] > 0.9
    assert report.mean_pairwise_concordance > 0.9


def test_difficulty_concordance_family_specific():
    # Family A finds dataset order easy->hard; family B the reverse -> negative.
    scores = np.zeros((4, 4, 1))
    a_profile = np.array([0.2, 0.4, 0.6, 0.8])
    for m in (0, 1):
        scores[m, :, 0] = a_profile
    for m in (2, 3):
        scores[m, :, 0] = a_profile[::-1]
    families = ["A", "A", "B", "B"]
    report = difficulty_concordance(scores, [HB], families, dataset_ids=list("wxyz"))
    assert report.concordance[0, 1] < 0


def test_difficulty_concordance_needs_two_families():
    with pytest.raises(ValueError):
        difficulty_concordance(np.zeros((2, 4, 1)), [HB], ["A", "A"])
