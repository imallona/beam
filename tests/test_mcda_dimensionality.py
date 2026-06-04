"""Tests for the dimensionality diagnostic (factors per metric group)."""

import numpy as np
import pytest

from beam.cards import polarities_for
from beam.datasets import load_openproblems
from beam.mcda import MetricDimensionalityReport, metric_dimensionality
from beam.mcda.metric_validity import _oriented, _pairwise_spearman


def _one_factor(rng, k=4, n=80, noise=0.15):
    """k metrics that are noisy readings of one latent factor, higher_is_better."""
    factor = rng.normal(size=(n, 1))
    scores = np.hstack([factor + rng.normal(0, noise, (n, 1)) for _ in range(k)])
    return scores, ["higher_is_better"] * k, ["g"] * k


def test_one_factor_group_is_unidimensional():
    rng = np.random.default_rng(0)
    scores, polarity, groups = _one_factor(rng)
    report = metric_dimensionality(scores, polarity, groups, metric_ids=["a", "b", "c", "d"])

    assert isinstance(report, MetricDimensionalityReport)
    assert report.k_by_group["g"] == 4
    assert report.parallel_components_by_group["g"] == 1
    assert report.unidimensional_groups == ("g",)
    assert report.multidimensional_groups == ()
    assert report.pc1_explained_by_group["g"] > 0.8
    assert report.n_observations == 80


def test_eigenvalues_match_numpy_and_sum_to_k():
    # The reported eigenvalues must be the eigenvalues of the same within-group
    # correlation block the shared engine produces, and they sum to k (the trace
    # of a correlation matrix), so pc1_explained = lambda_1 / k.
    rng = np.random.default_rng(1)
    scores, polarity, groups = _one_factor(rng, k=5, n=100)
    report = metric_dimensionality(scores, polarity, groups)

    corr, _ = _pairwise_spearman(_oriented(scores, polarity), 3)
    expected = np.sort(np.linalg.eigvalsh(corr))[::-1]
    assert report.eigenvalues_by_group["g"] == pytest.approx(tuple(expected))
    assert sum(report.eigenvalues_by_group["g"]) == pytest.approx(5.0)
    assert report.pc1_explained_by_group["g"] == pytest.approx(expected[0] / 5)


def test_two_factor_group_is_multidimensional():
    # One group built from two independent latent factors carries two components.
    rng = np.random.default_rng(7)
    f1 = rng.normal(size=(120, 1))
    f2 = rng.normal(size=(120, 1))
    scores = np.hstack(
        [
            f1 + rng.normal(0, 0.1, (120, 1)),
            f1 + rng.normal(0, 0.1, (120, 1)),
            f2 + rng.normal(0, 0.1, (120, 1)),
            f2 + rng.normal(0, 0.1, (120, 1)),
        ]
    )
    report = metric_dimensionality(scores, ["higher_is_better"] * 4, ["g"] * 4)
    assert report.parallel_components_by_group["g"] == 2
    assert ("g", 2) in report.multidimensional_groups
    assert report.unidimensional_groups == ()


def test_independent_metrics_carry_no_real_factor():
    # Metrics that share no signal have a flat eigenvalue profile: the first
    # component explains close to 1/k and parallel analysis keeps at most one.
    rng = np.random.default_rng(2)
    scores = rng.normal(size=(150, 4))
    report = metric_dimensionality(scores, ["higher_is_better"] * 4, ["g"] * 4)
    assert report.pc1_explained_by_group["g"] < 0.45
    assert report.parallel_components_by_group["g"] <= 1


def test_kaiser_keeps_at_least_as_many_as_parallel():
    # Kaiser counts every eigenvalue above one; parallel analysis raises the bar
    # to the chance level, so it never keeps more components than Kaiser.
    rng = np.random.default_rng(5)
    f1 = rng.normal(size=(90, 1))
    scores = np.hstack(
        [f1 + rng.normal(0, 0.2, (90, 1)) for _ in range(3)] + [rng.normal(size=(90, 2))]
    )
    report = metric_dimensionality(scores, ["higher_is_better"] * 5, ["g"] * 5)
    assert report.kaiser_components_by_group["g"] >= report.parallel_components_by_group["g"]


def test_seed_makes_the_report_reproduce():
    rng = np.random.default_rng(3)
    scores, polarity, groups = _one_factor(rng, k=4, n=90)
    a = metric_dimensionality(scores, polarity, groups, seed=11)
    b = metric_dimensionality(scores, polarity, groups, seed=11)
    assert a.parallel_components_by_group == b.parallel_components_by_group
    assert a.eigenvalues_by_group == b.eigenvalues_by_group


def test_group_with_incomplete_correlations_is_undefined():
    # Two metrics in a group never share an observation, so their correlation is
    # NaN and the within-group block cannot be decomposed.
    scores = np.array(
        [
            [1.0, np.nan, 1.0],
            [2.0, np.nan, 2.0],
            [3.0, np.nan, 3.0],
            [np.nan, 1.0, 2.0],
            [np.nan, 2.0, 1.0],
            [np.nan, 3.0, 3.0],
        ]
    )
    report = metric_dimensionality(scores, ["higher_is_better"] * 3, ["g", "g", "h"])
    reasons = dict(report.undefined_groups)
    assert "g" in reasons
    assert "g" not in report.k_by_group


def test_too_few_observations_is_undefined():
    scores = np.array([[1.0, 2.0, 3.0], [3.0, 1.0, 2.0]])
    report = metric_dimensionality(scores, ["higher_is_better"] * 3, ["g"] * 3)
    reasons = dict(report.undefined_groups)
    assert "g" in reasons
    assert "g" not in report.eigenvalues_by_group


def test_validation_errors():
    scores = np.zeros((10, 3))
    with pytest.raises(ValueError, match="scores must be"):
        metric_dimensionality(np.zeros((2, 2, 2, 2)), ["higher_is_better"] * 2, ["g", "g"])
    with pytest.raises(ValueError, match="polarity has"):
        metric_dimensionality(scores, ["higher_is_better"] * 2, ["g", "g", "g"])
    with pytest.raises(ValueError, match="groups has"):
        metric_dimensionality(scores, ["higher_is_better"] * 3, ["g", "g"])
    with pytest.raises(ValueError, match="monotone polarity"):
        metric_dimensionality(
            scores, ["higher_is_better", "higher_is_better", "target_value"], ["g", "g", "g"]
        )
    with pytest.raises(ValueError, match="two or more metrics"):
        metric_dimensionality(scores, ["higher_is_better"] * 3, ["g", "h", "i"])
    with pytest.raises(ValueError, match="metric_ids has"):
        metric_dimensionality(scores, ["higher_is_better"] * 3, ["g"] * 3, metric_ids=["a", "b"])


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


def test_openproblems_bio_batch_dimensionality_regression():
    # Regression on the OpenProblems batch_integration scores. Same grouping the
    # validity and reliability regressions use. Dimensionality dissociates from
    # reliability: the biological group has a high alpha but carries two factors
    # (the alpha is partly a size effect), while the low-alpha batch group is one
    # factor that its metrics simply track weakly.
    op = load_openproblems("batch_integration")
    metrics = [m for m in op.metric_ids if m != "hvg_overlap"]
    tensor = op.tensor(tuple(metrics))
    keep = (~np.isnan(tensor).all(axis=1)).all(axis=1)
    tensor = tensor[keep]
    groups = ["bio" if m in _BIO else "batch" for m in metrics]

    report = metric_dimensionality(tensor, polarities_for(metrics), groups, metric_ids=metrics)

    assert report.n_observations == 84
    assert report.k_by_group == {"bio": 7, "batch": 5}
    assert report.undefined_groups == ()
    assert sum(report.eigenvalues_by_group["bio"]) == pytest.approx(7.0)
    assert report.pc1_explained_by_group["bio"] == pytest.approx(0.5436, abs=1e-3)
    assert report.pc1_explained_by_group["batch"] == pytest.approx(0.4220, abs=1e-3)
    assert report.kaiser_components_by_group == {"bio": 2, "batch": 2}
    assert report.parallel_components_by_group == {"bio": 2, "batch": 1}
    assert report.unidimensional_groups == ("batch",)
    assert report.multidimensional_groups == (("bio", 2),)
