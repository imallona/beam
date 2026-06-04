"""Tests for the convergent/discriminant metric-validity diagnostic."""

import numpy as np
import pytest

from beam.cards import polarities_for
from beam.datasets import load_openproblems
from beam.mcda import MetricValidityReport, metric_validity


def _two_construct_scores(rng, n=60, noise=0.1):
    """Two latent constructs, two metrics each, all higher_is_better."""
    bio = rng.normal(size=(n, 1))
    batch = rng.normal(size=(n, 1))
    scores = np.hstack(
        [
            bio + rng.normal(0, noise, (n, 1)),
            bio + rng.normal(0, noise, (n, 1)),
            batch + rng.normal(0, noise, (n, 1)),
            batch + rng.normal(0, noise, (n, 1)),
        ]
    )
    polarity = ["higher_is_better"] * 4
    groups = ["bio", "bio", "batch", "batch"]
    return scores, polarity, groups


def test_clean_two_construct_passes_discriminant():
    rng = np.random.default_rng(0)
    scores, polarity, groups = _two_construct_scores(rng)
    report = metric_validity(scores, polarity, groups, metric_ids=["a", "b", "c", "d"])

    assert isinstance(report, MetricValidityReport)
    assert report.discriminant_ok
    assert report.mean_convergent > report.mean_discriminant
    assert report.convergent_by_group["bio"] > 0.8
    assert report.convergent_by_group["batch"] > 0.8
    # Independent constructs correlate near zero across groups.
    assert abs(report.mean_discriminant) < 0.4
    assert report.n_observations == 60
    # Symmetric matrix, unit diagonal.
    assert np.allclose(report.correlation, report.correlation.T, equal_nan=True)
    assert np.allclose(np.diag(report.correlation), 1.0)


def test_redundant_pair_flagged():
    rng = np.random.default_rng(1)
    base = rng.normal(size=(80, 1))
    other = rng.normal(size=(80, 1))
    scores = np.hstack(
        [
            base,
            base + rng.normal(0, 0.001, (80, 1)),  # near-duplicate of metric 0
            other,
            other + rng.normal(0, 0.5, (80, 1)),
        ]
    )
    report = metric_validity(
        scores,
        ["higher_is_better"] * 4,
        ["g1", "g1", "g2", "g2"],
        metric_ids=["x0", "x1", "x2", "x3"],
    )
    redundant_names = {(a, b) for a, b, _ in report.redundant_pairs}
    assert ("x0", "x1") in redundant_names
    assert all(r >= 0.9 for _, _, r in report.redundant_pairs)


def test_crossloading_metric_flagged():
    # metric labelled "bio" actually tracks the batch construct.
    rng = np.random.default_rng(2)
    bio = rng.normal(size=(80, 1))
    batch = rng.normal(size=(80, 1))
    scores = np.hstack(
        [
            bio + rng.normal(0, 0.1, (80, 1)),
            bio + rng.normal(0, 0.1, (80, 1)),
            batch + rng.normal(0, 0.1, (80, 1)),
            batch + rng.normal(0, 0.1, (80, 1)),
            batch + rng.normal(0, 0.1, (80, 1)),  # mislabelled as bio below
        ]
    )
    groups = ["bio", "bio", "batch", "batch", "bio"]
    report = metric_validity(
        scores,
        ["higher_is_better"] * 5,
        groups,
        metric_ids=["b0", "b1", "k0", "k1", "mislabelled"],
    )
    flagged = {name for name, *_ in report.crossloading_metrics}
    assert "mislabelled" in flagged
    for name, group, within, between, nearest in report.crossloading_metrics:
        assert between > within
        if name == "mislabelled":
            assert group == "bio"
            assert nearest == "batch"


def test_polarity_orientation_makes_opposite_metrics_converge():
    # A lower_is_better metric is the negation of a higher_is_better metric of
    # the same construct; after orientation they must correlate positively.
    rng = np.random.default_rng(3)
    signal = rng.normal(size=(60, 1))
    other = rng.normal(size=(60, 1))
    scores = np.hstack(
        [
            signal + rng.normal(0, 0.05, (60, 1)),
            -signal + rng.normal(0, 0.05, (60, 1)),  # lower_is_better
            other,
            other + rng.normal(0, 0.3, (60, 1)),
        ]
    )
    report = metric_validity(
        scores,
        ["higher_is_better", "lower_is_better", "higher_is_better", "higher_is_better"],
        ["g1", "g1", "g2", "g2"],
    )
    assert report.correlation[0, 1] > 0.9
    assert report.convergent_by_group["g1"] > 0.9


def test_pairwise_complete_with_nan():
    rng = np.random.default_rng(4)
    scores, polarity, groups = _two_construct_scores(rng, n=50)
    scores[:10, 0] = np.nan  # metric 0 unobserved on 10 rows
    report = metric_validity(scores, polarity, groups)
    # Coverage between metric 0 and any other is at most 40.
    assert report.coverage[0, 1] == 40
    assert report.coverage[2, 3] == 50
    assert np.isfinite(report.correlation[0, 1])
    assert report.discriminant_ok


def test_min_pairwise_yields_nan():
    scores = np.array(
        [
            [1.0, 2.0, np.nan, 4.0],
            [2.0, 1.0, np.nan, 3.0],
            [np.nan, np.nan, 5.0, 2.0],
            [np.nan, np.nan, 6.0, 1.0],
        ]
    )
    report = metric_validity(
        scores,
        ["higher_is_better"] * 4,
        ["g1", "g1", "g2", "g2"],
        min_pairwise=3,
    )
    # metrics 0 and 2 never co-occur; correlation is nan, coverage 0.
    assert report.coverage[0, 2] == 0
    assert np.isnan(report.correlation[0, 2])


def test_tensor_input_reshapes_to_observations():
    rng = np.random.default_rng(5)
    tensor = rng.normal(size=(7, 5, 4))  # 7 methods, 5 datasets, 4 metrics
    report = metric_validity(
        tensor,
        ["higher_is_better"] * 4,
        ["g1", "g1", "g2", "g2"],
    )
    assert report.n_observations == 35


def test_validation_errors():
    scores = np.zeros((10, 3))
    with pytest.raises(ValueError, match="polarity has"):
        metric_validity(scores, ["higher_is_better"] * 2, ["g", "g", "h"])
    with pytest.raises(ValueError, match="groups has"):
        metric_validity(scores, ["higher_is_better"] * 3, ["g", "h"])
    with pytest.raises(ValueError, match="monotone polarity"):
        metric_validity(
            scores, ["higher_is_better", "lower_is_better", "target_value"], ["g", "g", "h"]
        )
    with pytest.raises(ValueError, match="two distinct groups"):
        metric_validity(scores, ["higher_is_better"] * 3, ["g", "g", "g"])
    with pytest.raises(ValueError, match="two or more metrics"):
        metric_validity(scores, ["higher_is_better"] * 3, ["g", "h", "i"])
    with pytest.raises(ValueError, match="metric_ids has"):
        metric_validity(scores, ["higher_is_better"] * 3, ["g", "g", "h"], metric_ids=["a", "b"])


_BIO = {
    "ari",
    "nmi",
    "asw_label",
    "isolated_label_f1",
    "isolated_label_asw",
    "cell_cycle_conservation",
    "hvg_overlap",
    "clisi",
}


def test_openproblems_bio_batch_validity_regression():
    # Regression on the OpenProblems batch_integration scores: the scIB
    # bio/batch grouping is separable but weak.
    op = load_openproblems("batch_integration")
    metrics = [m for m in op.metric_ids if m != "hvg_overlap"]
    tensor = op.tensor(tuple(metrics))
    keep = (~np.isnan(tensor).all(axis=1)).all(axis=1)
    tensor = tensor[keep]
    groups = ["bio" if m in _BIO else "batch" for m in metrics]

    report = metric_validity(tensor, polarities_for(metrics), groups, metric_ids=metrics)

    assert report.n_observations == 84
    assert report.discriminant_ok
    assert report.mean_convergent == pytest.approx(0.383, abs=0.01)
    assert report.mean_discriminant == pytest.approx(0.297, abs=0.01)
    assert report.convergent_by_group["bio"] > report.convergent_by_group["batch"]
    assert report.redundant_pairs == ()

    leaning = {name: nearest for name, _, _, _, nearest in report.crossloading_metrics}
    assert leaning["graph_connectivity"] == "bio"
    assert leaning["kbet"] == "bio"
