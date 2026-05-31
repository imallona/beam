"""Tests for the declarative beam.yaml runner."""

from __future__ import annotations

import csv

import pytest

from beam.config import load_config, run_config


def _scores_csv(tmp_path):
    path = tmp_path / "scores.csv"
    path.write_text(
        "tool,ari,runtime,nmi\nseurat,0.81,42.0,0.78\nsc3,0.74,310.5,0.71\nraceid,0.55,18.0,0.50\n",
        encoding="utf-8",
    )
    return path


def _write_config(tmp_path, body):
    path = tmp_path / "beam.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def test_load_config_requires_input_scores(tmp_path):
    path = _write_config(tmp_path, "weighting:\n  method: equal\n")
    with pytest.raises(ValueError, match=r"inputs\.scores"):
        load_config(path)


def test_run_config_writes_all_outputs(tmp_path):
    _scores_csv(tmp_path)
    cfg = _write_config(
        tmp_path,
        "inputs:\n"
        "  scores: scores.csv\n"
        "weighting:\n  method: entropy\n"
        "aggregation:\n  method: topsis\n"
        "sensitivity:\n  smaa: {n: 64, seed: 1}\n"
        "outputs:\n"
        "  report: report.html\n"
        "  manifest: manifest.json\n"
        "  scores_normalized: norm.csv\n",
    )
    result = run_config(cfg)
    assert (tmp_path / "report.html").exists()
    assert (tmp_path / "manifest.json").exists()
    assert (tmp_path / "norm.csv").exists()
    assert result.smaa is not None
    assert result.smaa.n_samples == 64
    assert result.manifest["aggregation"]["method"] == "topsis"


def test_run_config_without_sensitivity_block(tmp_path):
    _scores_csv(tmp_path)
    cfg = _write_config(tmp_path, "inputs:\n  scores: scores.csv\n")
    result = run_config(cfg)
    assert result.smaa is None
    assert result.result.method == "saw"
    assert result.result.weighting == "equal"


def test_run_config_selects_and_reorders_metrics(tmp_path):
    _scores_csv(tmp_path)
    cfg = _write_config(
        tmp_path,
        "inputs:\n  scores: scores.csv\nmetrics:\n  - id: runtime\n  - id: ari\n",
    )
    result = run_config(cfg)
    assert result.metric_ids == ("runtime", "ari")


def test_run_config_rejects_unknown_metric_selection(tmp_path):
    _scores_csv(tmp_path)
    cfg = _write_config(
        tmp_path,
        "inputs:\n  scores: scores.csv\nmetrics:\n  - id: silhouette\n",
    )
    with pytest.raises(ValueError, match="not present"):
        run_config(cfg)


def test_run_config_honors_a_valid_version_pin(tmp_path):
    _scores_csv(tmp_path)
    cfg = _write_config(
        tmp_path,
        "inputs:\n  scores: scores.csv\nmetrics:\n  - id: ari\n    version: v1\n  - id: runtime\n",
    )
    result = run_config(cfg)
    versions = {m["id"]: m["version"] for m in result.manifest["metrics"]}
    assert versions["ari"] == "v1"
    assert versions["runtime"] == "v1"


def test_run_config_rejects_an_unknown_version_pin(tmp_path):
    _scores_csv(tmp_path)
    cfg = _write_config(
        tmp_path,
        "inputs:\n  scores: scores.csv\nmetrics:\n  - id: ari\n    version: v2\n",
    )
    with pytest.raises(ValueError, match=r"pins metric 'ari' at version 'v2'"):
        run_config(cfg)


def test_normalized_csv_has_tool_and_metric_headers(tmp_path):
    _scores_csv(tmp_path)
    cfg = _write_config(
        tmp_path,
        "inputs:\n  scores: scores.csv\noutputs:\n  scores_normalized: norm.csv\n",
    )
    run_config(cfg)
    with (tmp_path / "norm.csv").open() as handle:
        rows = list(csv.reader(handle))
    assert rows[0] == ["tool", "ari", "runtime", "nmi"]
    assert rows[1][0] == "seurat"
    assert len(rows) == 4
