"""Tests for the combined metric-set diagnostics entry point."""

import numpy as np
import pytest

from beam.mcda import (
    MetricDiagnosticsReport,
    MetricDimensionalityReport,
    MetricReliabilityReport,
    MetricValidityReport,
    metric_diagnostics,
)


def _two_groups(rng, n=80, noise=0.12):
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


def test_runs_all_three_diagnostics():
    rng = np.random.default_rng(0)
    scores, polarity, groups = _two_groups(rng)
    report = metric_diagnostics(scores, polarity, groups, metric_ids=["a", "b", "c", "d"])

    assert isinstance(report, MetricDiagnosticsReport)
    assert isinstance(report.validity, MetricValidityReport)
    assert isinstance(report.reliability, MetricReliabilityReport)
    assert isinstance(report.dimensionality, MetricDimensionalityReport)


def test_three_reports_rest_on_the_same_numbers():
    # The three diagnostics share one correlation engine, so their numbers line
    # up: reliability's mean within-group correlation is validity's
    # convergent_by_group, and all three see the same observations and group sizes.
    rng = np.random.default_rng(1)
    scores, polarity, groups = _two_groups(rng)
    report = metric_diagnostics(scores, polarity, groups)

    for g in ("bio", "batch"):
        assert report.reliability.mean_inter_item_by_group[g] == pytest.approx(
            report.validity.convergent_by_group[g]
        )
    assert report.reliability.k_by_group == report.dimensionality.k_by_group
    assert report.validity.n_observations == report.reliability.n_observations
    assert report.reliability.n_observations == report.dimensionality.n_observations


def test_single_construct_skips_validity():
    # Convergent and discriminant evidence need two groups; reliability and
    # dimensionality do not, so a one-construct call still returns those two.
    rng = np.random.default_rng(2)
    factor = rng.normal(size=(80, 1))
    scores = np.hstack([factor + rng.normal(0, 0.12, (80, 1)) for _ in range(4)])
    report = metric_diagnostics(scores, ["higher_is_better"] * 4, ["g"] * 4)

    assert report.validity is None
    assert report.reliability.alpha_by_group["g"] > 0.8
    assert "g" in report.dimensionality.unidimensional_groups


def test_thresholds_thread_through():
    rng = np.random.default_rng(3)
    scores, polarity, groups = _two_groups(rng)
    lenient = metric_diagnostics(scores, polarity, groups)
    assert lenient.reliability.low_reliability_groups == ()

    ceiling = max(lenient.reliability.alpha_by_group.values()) + 0.001
    strict = metric_diagnostics(scores, polarity, groups, alpha_threshold=ceiling)
    assert {g for g, _ in strict.reliability.low_reliability_groups} == {"bio", "batch"}


def test_validation_error_propagates():
    scores = np.zeros((10, 3))
    with pytest.raises(ValueError, match="two or more metrics"):
        metric_diagnostics(scores, ["higher_is_better"] * 3, ["g", "h", "i"])
