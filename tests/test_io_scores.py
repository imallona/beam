"""Tests for beam.load_scores, the registry-validated CSV loader."""

from __future__ import annotations

import dataclasses

import numpy as np
import pytest

import beam
from beam.io import Scores, UnknownMetricError, load_scores
from beam.mcda import run_from_registry


def _write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_load_scores_is_exposed_at_top_level():
    assert beam.load_scores is load_scores


def test_wide_layout_shape_and_labels(tmp_path):
    path = _write(
        tmp_path,
        "wide.csv",
        "tool,ari,runtime\nseurat,0.81,42.0\nsc3,0.74,310.5\nraceid,0.55,18.0\n",
    )
    scores = load_scores(path)
    assert scores.layout == "wide"
    assert not scores.is_tensor
    assert scores.tool_names == ("seurat", "sc3", "raceid")
    assert scores.metric_ids == ("ari", "runtime")
    assert scores.dataset_names is None
    assert scores.values.shape == (3, 2)
    np.testing.assert_allclose(scores.values[0], [0.81, 42.0])


def test_wide_missing_cells_become_nan(tmp_path):
    path = _write(tmp_path, "wide.csv", "tool,ari,runtime\nseurat,NA,42.0\nsc3,0.74,\n")
    scores = load_scores(path)
    assert np.isnan(scores.values[0, 0])
    assert np.isnan(scores.values[1, 1])


def test_long_layout_builds_tensor(tmp_path):
    path = _write(
        tmp_path,
        "long.csv",
        "tool,dataset,metric,score\n"
        "seurat,koh,ari,0.81\n"
        "seurat,koh,runtime,42.0\n"
        "sc3,koh,ari,0.74\n"
        "sc3,koh,runtime,310.5\n"
        "seurat,zhengmix,ari,0.66\n"
        "sc3,zhengmix,ari,0.70\n",
    )
    scores = load_scores(path)
    assert scores.layout == "long"
    assert scores.is_tensor
    assert scores.tool_names == ("seurat", "sc3")
    assert scores.dataset_names == ("koh", "zhengmix")
    assert scores.metric_ids == ("ari", "runtime")
    assert scores.values.shape == (2, 2, 2)
    # seurat on koh: ari 0.81, runtime 42.0
    np.testing.assert_allclose(scores.values[0, 0], [0.81, 42.0])
    # runtime on zhengmix was never given for either tool
    assert np.isnan(scores.values[0, 1, 1])
    assert np.isnan(scores.values[1, 1, 1])


def test_long_column_order_is_free(tmp_path):
    path = _write(
        tmp_path,
        "long.csv",
        "metric,score,tool,dataset\nari,0.81,seurat,koh\nruntime,42.0,seurat,koh\n",
    )
    scores = load_scores(path)
    assert scores.metric_ids == ("ari", "runtime")
    np.testing.assert_allclose(scores.values[0, 0], [0.81, 42.0])


def test_unknown_metric_raises_named_error_wide(tmp_path):
    path = _write(tmp_path, "wide.csv", "tool,ari,notametric\nseurat,0.8,1.0\n")
    with pytest.raises(UnknownMetricError, match="notametric"):
        load_scores(path)


def test_unknown_metric_raises_named_error_long(tmp_path):
    path = _write(
        tmp_path,
        "long.csv",
        "tool,dataset,metric,score\nseurat,koh,bogus,0.8\n",
    )
    with pytest.raises(UnknownMetricError, match="bogus"):
        load_scores(path)


def test_forced_long_on_wide_header_raises(tmp_path):
    path = _write(tmp_path, "wide.csv", "tool,ari,runtime\nseurat,0.8,42.0\n")
    with pytest.raises(ValueError, match="forced as long"):
        load_scores(path, layout="long")


def test_duplicate_long_row_raises(tmp_path):
    path = _write(
        tmp_path,
        "long.csv",
        "tool,dataset,metric,score\nseurat,koh,ari,0.8\nseurat,koh,ari,0.9\n",
    )
    with pytest.raises(ValueError, match="duplicates"):
        load_scores(path)


def test_ragged_wide_row_raises(tmp_path):
    path = _write(tmp_path, "wide.csv", "tool,ari,runtime\nseurat,0.8\n")
    with pytest.raises(ValueError, match="fields"):
        load_scores(path)


def test_empty_file_raises(tmp_path):
    path = _write(tmp_path, "empty.csv", "\n\n")
    with pytest.raises(ValueError, match="empty"):
        load_scores(path)


def test_blank_lines_are_skipped(tmp_path):
    path = _write(tmp_path, "wide.csv", "tool,ari\n\nseurat,0.8\n\nsc3,0.7\n")
    scores = load_scores(path)
    assert scores.tool_names == ("seurat", "sc3")


def test_loaded_scores_drive_run_from_registry(tmp_path):
    path = _write(
        tmp_path,
        "wide.csv",
        "tool,ari,runtime\nseurat,0.81,42.0\nsc3,0.74,310.5\nraceid,0.55,18.0\n",
    )
    scores = load_scores(path)
    result = run_from_registry(scores.values, scores.metric_ids, weights="equal", method="saw")
    assert result.ranks.shape == (3,)
    assert set(result.ranks.tolist()) == {1, 2, 3}


def test_scores_is_frozen():
    s = Scores(np.zeros((1, 1)), ("t",), ("ari",), None, "wide")
    with pytest.raises(dataclasses.FrozenInstanceError):
        s.layout = "long"  # type: ignore[misc]
