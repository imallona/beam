"""Tests for the internal-consistency reliability diagnostic (Cronbach's alpha)."""

import numpy as np
import pytest

from beam.cards import polarities_for
from beam.datasets import load_openproblems
from beam.mcda import MetricReliabilityReport, metric_reliability


def _one_factor(rng, k=4, n=80, noise=0.15):
    """k metrics that are noisy readings of one latent factor, higher_is_better."""
    factor = rng.normal(size=(n, 1))
    scores = np.hstack([factor + rng.normal(0, noise, (n, 1)) for _ in range(k)])
    return scores, ["higher_is_better"] * k, ["g"] * k


def test_one_factor_group_is_reliable():
    rng = np.random.default_rng(0)
    scores, polarity, groups = _one_factor(rng)
    report = metric_reliability(scores, polarity, groups, metric_ids=["a", "b", "c", "d"])

    assert isinstance(report, MetricReliabilityReport)
    assert report.k_by_group["g"] == 4
    assert report.alpha_by_group["g"] > 0.85
    assert report.low_reliability_groups == ()
    assert report.n_observations == 80


def test_alpha_matches_standardized_formula():
    # alpha must equal k * r_bar / (1 + (k - 1) * r_bar) exactly.
    rng = np.random.default_rng(1)
    scores, polarity, groups = _one_factor(rng, k=3)
    report = metric_reliability(scores, polarity, groups)
    k = report.k_by_group["g"]
    r_bar = report.mean_inter_item_by_group["g"]
    expected = k * r_bar / (1 + (k - 1) * r_bar)
    assert report.alpha_by_group["g"] == pytest.approx(expected)


def test_independent_metrics_have_low_alpha():
    # Metrics that share no signal correlate near zero, so alpha is near zero and
    # the group is flagged below the default 0.7 cutoff.
    rng = np.random.default_rng(2)
    scores = rng.normal(size=(120, 4))
    report = metric_reliability(scores, ["higher_is_better"] * 4, ["g"] * 4)
    assert report.alpha_by_group["g"] < 0.3
    assert ("g", report.alpha_by_group["g"]) in report.low_reliability_groups


def test_alpha_if_dropped_finds_the_pulling_metric():
    # Three metrics share a factor; a fourth in the same group is pure noise.
    # Dropping the noise metric should raise the group's alpha.
    rng = np.random.default_rng(3)
    factor = rng.normal(size=(100, 1))
    scores = np.hstack(
        [
            factor + rng.normal(0, 0.1, (100, 1)),
            factor + rng.normal(0, 0.1, (100, 1)),
            factor + rng.normal(0, 0.1, (100, 1)),
            rng.normal(size=(100, 1)),  # noise, mislabelled into the group
        ]
    )
    report = metric_reliability(
        scores,
        ["higher_is_better"] * 4,
        ["g"] * 4,
        metric_ids=["s0", "s1", "s2", "noise"],
    )
    dropped = {name: alpha for name, _, alpha in report.alpha_if_dropped}
    assert dropped["noise"] > report.alpha_by_group["g"]
    # Dropping a good metric should not raise alpha.
    assert dropped["s0"] < report.alpha_by_group["g"]


def test_orientation_makes_opposite_metric_contribute():
    # A lower_is_better metric is the negation of the factor; once oriented it
    # joins the group rather than dragging alpha down.
    rng = np.random.default_rng(4)
    factor = rng.normal(size=(80, 1))
    scores = np.hstack(
        [
            factor + rng.normal(0, 0.05, (80, 1)),
            factor + rng.normal(0, 0.05, (80, 1)),
            -factor + rng.normal(0, 0.05, (80, 1)),  # lower_is_better
        ]
    )
    report = metric_reliability(
        scores,
        ["higher_is_better", "higher_is_better", "lower_is_better"],
        ["g", "g", "g"],
    )
    assert report.alpha_by_group["g"] > 0.9


def test_group_of_two_has_no_drop_entries():
    rng = np.random.default_rng(5)
    factor = rng.normal(size=(60, 1))
    scores = np.hstack(
        [
            factor + rng.normal(0, 0.1, (60, 1)),
            factor + rng.normal(0, 0.1, (60, 1)),
            rng.normal(size=(60, 1)),
        ]
    )
    report = metric_reliability(
        scores,
        ["higher_is_better"] * 3,
        ["pair", "pair", "solo"],
        metric_ids=["a", "b", "c"],
    )
    # The two-metric group has an alpha but no alpha-if-dropped rows; the
    # singleton group has neither.
    assert "pair" in report.alpha_by_group
    assert "solo" not in report.alpha_by_group
    assert report.alpha_if_dropped == ()


def test_pairwise_complete_with_nan():
    rng = np.random.default_rng(6)
    scores, polarity, groups = _one_factor(rng, k=3, n=70)
    scores[:15, 0] = np.nan
    report = metric_reliability(scores, polarity, groups)
    assert np.isfinite(report.alpha_by_group["g"])
    assert report.n_observations == 70


def test_tensor_input_reshapes_to_observations():
    rng = np.random.default_rng(7)
    factor = rng.normal(size=(6, 5, 1))
    tensor = np.concatenate([factor + rng.normal(0, 0.1, (6, 5, 1)) for _ in range(3)], axis=2)
    report = metric_reliability(tensor, ["higher_is_better"] * 3, ["g"] * 3)
    assert report.n_observations == 30
    assert report.alpha_by_group["g"] > 0.85


def test_validation_errors():
    scores = np.zeros((10, 3))
    with pytest.raises(ValueError, match="polarity has"):
        metric_reliability(scores, ["higher_is_better"] * 2, ["g", "g", "g"])
    with pytest.raises(ValueError, match="groups has"):
        metric_reliability(scores, ["higher_is_better"] * 3, ["g", "g"])
    with pytest.raises(ValueError, match="monotone polarity"):
        metric_reliability(
            scores, ["higher_is_better", "higher_is_better", "target_value"], ["g", "g", "g"]
        )
    with pytest.raises(ValueError, match="two or more metrics"):
        metric_reliability(scores, ["higher_is_better"] * 3, ["g", "h", "i"])
    with pytest.raises(ValueError, match="metric_ids has"):
        metric_reliability(scores, ["higher_is_better"] * 3, ["g", "g", "g"], metric_ids=["a", "b"])


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


def test_openproblems_bio_batch_reliability_regression():
    # Pins findings 0009: the bio group reads as one reliable scale, the batch
    # group does not at the conventional 0.7 cutoff, on the OpenProblems
    # batch_integration scores. Same setup as the metric_validity regression.
    op = load_openproblems("batch_integration")
    metrics = [m for m in op.metric_ids if m != "hvg_overlap"]
    tensor = op.tensor(tuple(metrics))
    keep = (~np.isnan(tensor).all(axis=1)).all(axis=1)
    tensor = tensor[keep]
    groups = ["bio" if m in _BIO else "batch" for m in metrics]

    report = metric_reliability(tensor, polarities_for(metrics), groups, metric_ids=metrics)

    assert report.n_observations == 84
    assert report.k_by_group == {"bio": 7, "batch": 5}
    assert report.alpha_by_group["bio"] == pytest.approx(0.851, abs=0.01)
    assert report.alpha_by_group["batch"] == pytest.approx(0.618, abs=0.01)
    assert report.low_reliability_groups == (("batch", report.alpha_by_group["batch"]),)

    # pcr is the only batch metric whose removal raises the batch group's alpha.
    raises_batch = {
        name
        for name, g, a in report.alpha_if_dropped
        if g == "batch" and a > report.alpha_by_group["batch"]
    }
    assert "pcr" in raises_batch
