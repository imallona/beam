"""Tests for beam.rank, RunResult, and the run manifest."""

from __future__ import annotations

import numpy as np
import pytest

import beam
from beam.api import rank
from beam.datasets import load_duo2018
from beam.manifest import reproducible_view


def _wide_csv(tmp_path):
    path = tmp_path / "scores.csv"
    path.write_text(
        "tool,ari,runtime\nseurat,0.81,42.0\nsc3,0.74,310.5\nraceid,0.55,18.0\n",
        encoding="utf-8",
    )
    return path


def test_rank_from_array_needs_metric_ids():
    with pytest.raises(ValueError, match="metric_ids"):
        rank(np.array([[0.8, 1.0], [0.7, 2.0]]))


def test_rank_from_array_produces_full_result():
    matrix = np.array([[0.9, 30.0], [0.7, 50.0], [0.5, 20.0]])
    result = rank(matrix, metric_ids=["ari", "runtime"], method="topsis")
    assert result.result.ranks.shape == (3,)
    assert set(result.result.ranks.tolist()) == {1, 2, 3}
    assert result.tool_names == ("tool_1", "tool_2", "tool_3")
    assert result.smaa is not None
    assert result.leave_one_out is not None
    assert result.perturbation is not None


def test_rank_without_sensitivity_skips_primitives():
    matrix = np.array([[0.9, 30.0], [0.7, 50.0]])
    result = rank(matrix, metric_ids=["ari", "runtime"], sensitivity=False)
    assert result.smaa is None
    assert result.leave_one_out is None
    assert result.perturbation is None
    assert result.manifest["sensitivity"]["enabled"] is False
    assert result.manifest["sensitivity"]["smaa"] is None


def test_rank_from_path_records_input_hash(tmp_path):
    path = _wide_csv(tmp_path)
    result = rank(path, sensitivity=False)
    assert result.manifest["input"]["path"] == str(path)
    assert len(result.manifest["input"]["sha256"]) == 64
    assert result.top_tool in result.tool_names


def test_rank_is_exposed_at_top_level():
    assert beam.rank is rank


def test_manifest_records_card_versions_and_normalization():
    matrix = np.array([[0.9, 30.0], [0.7, 50.0]])
    result = rank(matrix, metric_ids=["ari", "runtime"], method="topsis", sensitivity=False)
    metric_block = {m["id"]: m for m in result.manifest["metrics"]}
    assert metric_block["ari"]["version"]
    assert len(metric_block["ari"]["sha256"]) == 64
    norm = {n["metric"]: n["strategy"] for n in result.manifest["normalization"]}
    assert set(norm) == {"ari", "runtime"}
    assert result.manifest["aggregation"]["method"] == "topsis"
    assert "pymcdm" in result.manifest["software"]


def test_manifest_is_deterministic_apart_from_time_and_host(tmp_path):
    path = _wide_csv(tmp_path)
    a = rank(path, weights="entropy", method="topsis", seed=7)
    b = rank(path, weights="entropy", method="topsis", seed=7)
    assert reproducible_view(a.manifest) == reproducible_view(b.manifest)
    # The volatile keys are present but excluded from the comparison.
    assert "created_utc" in a.manifest
    assert "host" in a.manifest


def test_sensitivity_shares_normalization_with_ranking():
    # The SMAA base run and the headline ranking must use the same normalized
    # matrix, so their equal-weight rankings agree.
    matrix = np.array([[0.9, 30.0], [0.7, 50.0], [0.5, 20.0]])
    result = rank(matrix, metric_ids=["ari", "runtime"], weights="equal", method="saw")
    np.testing.assert_array_equal(result.smaa.base.ranks, result.result.ranks)
    np.testing.assert_allclose(result.smaa.base.normalized, result.result.normalized)


def test_rank_reduces_a_clean_tensor(tmp_path):
    path = tmp_path / "long.csv"
    path.write_text(
        "tool,dataset,metric,score\n"
        "a,d1,ari,0.8\na,d2,ari,0.6\n"
        "a,d1,runtime,10\na,d2,runtime,40\n"
        "b,d1,ari,0.5\nb,d2,ari,0.7\n"
        "b,d1,runtime,20\nb,d2,runtime,5\n",
        encoding="utf-8",
    )
    result = rank(path, sensitivity=False)
    assert result.matrix.shape == (2, 2)
    # runtime uses a geometric mean across datasets per its card.
    np.testing.assert_allclose(result.matrix[0, 1], np.sqrt(10 * 40))


def test_rank_refuses_tensor_with_an_all_missing_metric_row(tmp_path):
    path = tmp_path / "long.csv"
    path.write_text(
        "tool,dataset,metric,score\n"
        "a,d1,ari,0.8\na,d1,runtime,10\n"
        "b,d1,runtime,20\n",  # b never observed for ari
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="no observed dataset"):
        rank(path, sensitivity=False)


def test_rank_on_duo_matches_run_from_registry():
    duo = load_duo2018()
    # Use the three denser metrics and the methods complete across all datasets.
    metric_ids = ("ari", "runtime", "shannon_entropy_diff")
    tensor = duo.tensor(metric_ids)
    complete = duo.complete_methods(metric_ids)
    matrix_3d = tensor[complete]
    tool_names = tuple(np.array(duo.method_names)[complete].tolist())
    scores = beam.Scores(
        values=matrix_3d,
        tool_names=tool_names,
        metric_ids=metric_ids,
        dataset_names=duo.dataset_names,
        layout="long",
    )
    result = rank(scores, weights="entropy", method="topsis", sensitivity=False)
    assert result.matrix.shape == (int(complete.sum()), 3)
    assert set(result.result.ranks.tolist()) == set(range(1, int(complete.sum()) + 1))
