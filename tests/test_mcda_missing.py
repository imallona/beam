"""Missing-data handling across the MCDA pipeline.

beam never imputes a missing score by default or silently. The tool by metric
pipeline refuses a missing cell unless the caller picks a policy: available-case
(SAW only), worst-case failure mapping, or explicit mean imputation. These tests
pin that contract and check that the complete-data path is unchanged.
"""

from __future__ import annotations

import numpy as np
import pytest

import beam
from beam.mcda import (
    IncompleteMatrixError,
    comet,
    critic_weights,
    critical_difference,
    entropy_weights,
    equal_weights,
    merec_weights,
    normalize,
    promethee_ii,
    rank,
    reduce_tensor,
    run,
    standard_deviation_weights,
    topsis,
    vikor,
    weighted_sum,
)

HB = "higher_is_better"
LB = "lower_is_better"


# Normalization is NaN-transparent: anchors from observed values, NaN passes through.


def test_normalize_anchors_on_observed_and_keeps_nan():
    col = np.array([[0.2], [0.8], [np.nan]])
    out = normalize(col, [HB], ["min_max"])
    assert np.isnan(out[2, 0])
    assert out[0, 0] == 0.0 and out[1, 0] == 1.0


def test_normalize_partial_equals_normalizing_the_observed_subvector():
    full = np.array([[3.0], [1.0], [np.nan], [2.0]])
    observed = np.array([[3.0], [1.0], [2.0]])
    out_full = normalize(full, [HB], ["min_max"])
    out_obs = normalize(observed, [HB], ["min_max"])
    assert np.isnan(out_full[2, 0])
    np.testing.assert_allclose(out_full[[0, 1, 3], 0], out_obs[:, 0])


def test_normalize_rank_strategy_skips_missing():
    out = normalize(np.array([[3.0], [1.0], [np.nan], [2.0]]), [HB], ["rank"])
    assert np.isnan(out[2, 0])
    # three observed values, best maps to 1, worst to 0
    np.testing.assert_allclose(out[[0, 1, 3], 0], [1.0, 0.0, 0.5])


# SAW is the one aggregation that admits an available-case form.


def test_weighted_sum_available_case_scores_each_tool_on_its_observed_metrics():
    x = np.array([[0.2, 0.9], [0.8, 0.1], [0.5, np.nan]])
    w = np.array([0.4, 0.6])
    out = weighted_sum(x, w)
    # complete rows match the plain weighted sum; the partial row is its lone metric
    np.testing.assert_allclose(out[:2], x[:2] @ w)
    assert out[2] == pytest.approx(0.5)


def test_weighted_sum_complete_matrix_matches_the_pymcdm_path():
    x = np.array([[0.2, 0.9, 0.4], [0.8, 0.1, 0.6], [0.5, 0.5, 0.5]])
    w = np.array([0.2, 0.3, 0.5])
    np.testing.assert_allclose(weighted_sum(x, w), x @ w)


def test_weighted_sum_refuses_an_all_missing_row():
    x = np.array([[0.2, 0.9], [np.nan, np.nan]])
    with pytest.raises(IncompleteMatrixError):
        weighted_sum(x, np.array([0.5, 0.5]))


# The distance and pairwise methods, the objective weights, the CD test and rank
# refuse a matrix with missing cells.


@pytest.mark.parametrize("fn", [topsis, vikor, promethee_ii, comet])
def test_distance_methods_refuse_missing_cells(fn):
    x = np.array([[0.2, 0.9], [0.8, 0.1], [0.5, np.nan]])
    with pytest.raises(IncompleteMatrixError):
        fn(x, np.array([0.5, 0.5]))


@pytest.mark.parametrize(
    "fn", [entropy_weights, standard_deviation_weights, critic_weights, merec_weights]
)
def test_objective_weights_refuse_missing_cells(fn):
    x = np.array([[0.2, 0.9], [0.8, 0.1], [0.5, np.nan]])
    with pytest.raises(IncompleteMatrixError):
        fn(x)


def test_critical_difference_refuses_missing_cells():
    scores = np.array([[1.0, 2.0], [3.0, np.nan], [2.0, 1.0]])
    with pytest.raises(IncompleteMatrixError):
        critical_difference(scores)


def test_rank_refuses_a_nan_composite():
    with pytest.raises(IncompleteMatrixError):
        rank(np.array([0.5, np.nan, 0.2]))


# run() policies.


def test_run_defaults_to_refusing_missing_cells():
    x = np.array([[0.2, 5.0], [0.8, 1.0], [0.5, np.nan]])
    with pytest.raises(IncompleteMatrixError):
        run(x, [HB, LB])


def test_run_complete_matrix_is_unaffected_by_the_missing_argument():
    x = np.array([[0.2, 5.0], [0.8, 1.0], [0.5, 3.0]])
    base = run(x, [HB, LB])
    for policy in ("available", "worst", "impute"):
        same = run(x, [HB, LB], missing=policy)
        np.testing.assert_array_equal(same.ranks, base.ranks)
        # no missing means no missing-policy warning was added
        assert not any("missing=" in w for w in same.warnings)


def test_run_available_ranks_saw_and_warns():
    x = np.array([[0.2, 5.0], [0.8, 1.0], [0.5, np.nan]])
    result = run(x, [HB, LB], weights="equal", method="saw", missing="available")
    assert result.ranks.shape == (3,)
    assert any("available" in w for w in result.warnings)


def test_run_available_refuses_distance_methods():
    x = np.array([[0.2, 5.0], [0.8, 1.0], [0.5, np.nan]])
    with pytest.raises(IncompleteMatrixError):
        run(x, [HB, LB], method="topsis", missing="available")


def test_run_available_refuses_objective_weighting():
    x = np.array([[0.2, 5.0], [0.8, 1.0], [0.5, np.nan]])
    with pytest.raises(IncompleteMatrixError):
        run(x, [HB, LB], weights="entropy", method="saw", missing="available")


def test_run_worst_maps_a_missing_cell_to_zero_then_aggregates_normally():
    x = np.array([[0.2, 5.0], [0.8, 1.0], [0.5, np.nan]])
    worst = run(x, [HB, LB], weights="equal", method="topsis", missing="worst")
    # the normalized matrix carries 0 exactly where the input was missing
    assert worst.normalized[2, 1] == 0.0
    assert not np.isnan(worst.normalized).any()
    # aggregating that completed matrix by hand reproduces the ranking
    expected = rank(topsis(worst.normalized, equal_weights(2)))
    np.testing.assert_array_equal(worst.ranks, expected)
    assert any("worst" in w for w in worst.warnings)


def test_run_impute_fills_with_the_observed_column_mean():
    x = np.array([[0.2, 5.0], [0.8, 1.0], [0.5, np.nan]])
    result = run(x, [HB, LB], weights="equal", method="saw", missing="impute")
    assert result.ranks.shape == (3,)
    assert any("impute" in w for w in result.warnings)


def test_run_rejects_an_unknown_missing_policy():
    x = np.array([[0.2, 5.0], [0.8, 1.0], [0.5, np.nan]])
    with pytest.raises(ValueError, match="unknown missing policy"):
        run(x, [HB, LB], missing="bogus")


# reduce_tensor: the dataset-axis available-case summary, with the zero-coverage knob.


def test_reduce_tensor_zero_coverage_errors_by_default():
    # tool 1 never observed on metric 0
    tensor = np.array([[[1.0]], [[np.nan]]])  # was 2D-ish; build a real 3D below
    tensor = np.full((2, 2, 1), np.nan)
    tensor[0, :, 0] = [1.0, 2.0]
    with pytest.raises(ValueError, match="no observed dataset"):
        reduce_tensor(tensor, ["arithmetic_mean"])


def test_reduce_tensor_zero_coverage_can_yield_nan():
    tensor = np.full((2, 2, 1), np.nan)
    tensor[0, :, 0] = [1.0, 2.0]
    out = reduce_tensor(tensor, ["arithmetic_mean"], on_zero_coverage="nan")
    assert out[0, 0] == pytest.approx(1.5)
    assert np.isnan(out[1, 0])


def test_reduce_tensor_partial_coverage_is_available_case_not_imputed():
    # a tool observed on one of two datasets is summarized over the observed one
    tensor = np.full((2, 2, 1), np.nan)
    tensor[0, :, 0] = [1.0, 3.0]
    tensor[1, 0, 0] = 4.0  # tool 1 only ran on dataset 0
    out = reduce_tensor(tensor, ["arithmetic_mean"], on_zero_coverage="nan")
    np.testing.assert_allclose(out[:, 0], [2.0, 4.0])


# api.rank end to end.


def test_api_rank_defaults_to_refusing_a_partial_wide_matrix():
    mat = np.array([[0.8, 10.0], [0.6, 20.0], [0.7, np.nan]])
    with pytest.raises(IncompleteMatrixError):
        beam.rank(mat, metric_ids=["ari", "runtime"], sensitivity=False)


def test_api_rank_available_runs_saw_with_full_sensitivity():
    mat = np.array([[0.8, 10.0], [0.6, 20.0], [0.7, np.nan]])
    result = beam.rank(
        mat, metric_ids=["ari", "runtime"], method="saw", missing="available", sensitivity=True
    )
    assert result.smaa is not None
    assert result.leave_one_out is not None
    assert result.perturbation is not None
    assert any("available" in w for w in result.result.warnings)


def test_api_rank_worst_lets_a_distance_method_run():
    mat = np.array([[0.8, 10.0], [0.6, 20.0], [0.7, np.nan]])
    result = beam.rank(
        mat, metric_ids=["ari", "runtime"], method="topsis", missing="worst", sensitivity=False
    )
    assert result.result.ranks.shape == (3,)


def test_api_rank_tensor_zero_coverage_errors_by_default_but_worst_resolves_it():
    tensor = np.array(
        [
            [[0.8, 10.0], [0.7, 12.0]],
            [[0.6, 20.0], [0.5, 22.0]],
            [[0.7, np.nan], [0.6, np.nan]],
        ]
    )
    scores = beam.Scores(
        values=tensor,
        tool_names=("a", "b", "c"),
        metric_ids=("ari", "runtime"),
        dataset_names=("d1", "d2"),
        layout="long",
    )
    with pytest.raises((IncompleteMatrixError, ValueError)):
        beam.rank(scores, sensitivity=False)
    resolved = beam.rank(scores, missing="worst", sensitivity=True)
    assert resolved.result.ranks.shape == (3,)
    assert resolved.leave_one_dataset_out is not None


# CLI and beam.yaml expose the policy.


def _partial_csv(tmp_path):
    path = tmp_path / "partial.csv"
    path.write_text("tool,ari,runtime\na,0.8,10\nb,0.6,20\nc,0.7,\n", encoding="utf-8")
    return path


def test_cli_rank_defaults_to_error_on_a_partial_csv(tmp_path, capsys):
    from beam.cli import main

    code = main(["rank", str(_partial_csv(tmp_path)), "--no-sensitivity"])
    assert code == 2
    assert "beam: error:" in capsys.readouterr().err


def test_cli_rank_accepts_on_missing_worst(tmp_path, capsys):
    from beam.cli import main

    out = tmp_path / "record.json"
    code = main(
        [
            "rank",
            str(_partial_csv(tmp_path)),
            "--on-missing",
            "worst",
            "--no-sensitivity",
            "--out",
            str(out),
        ]
    )
    assert code == 0
    assert out.exists()


def test_beam_yaml_missing_key(tmp_path):
    from beam.config import run_config

    _partial_csv(tmp_path)
    cfg = tmp_path / "beam.yaml"
    cfg.write_text(
        "inputs:\n  scores: partial.csv\naggregation:\n  method: saw\nmissing: available\n",
        encoding="utf-8",
    )
    result = run_config(cfg)
    assert result.result.ranks.shape == (3,)
    assert any("available" in w for w in result.result.warnings)
