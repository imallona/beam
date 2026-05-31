"""Tests for the beam command-line interface."""

from __future__ import annotations

import json

import pytest

from beam.cli import main
from beam.heterogeneity import bttree_available, r_available


def _long_scores(tmp_path, name="long.csv", metrics=("ari",)):
    """Write a small long-format score file with a dataset axis."""
    rng_rows = {
        "ari": {
            "d1": {"seurat": 0.81, "sc3": 0.74, "raceid": 0.40},
            "d2": {"seurat": 0.78, "sc3": 0.71, "raceid": 0.45},
            "d3": {"seurat": 0.69, "sc3": 0.80, "raceid": 0.33},
            "d4": {"seurat": 0.84, "sc3": 0.66, "raceid": 0.51},
        },
        "nmi": {
            "d1": {"seurat": 0.79, "sc3": 0.70, "raceid": 0.42},
            "d2": {"seurat": 0.75, "sc3": 0.69, "raceid": 0.47},
            "d3": {"seurat": 0.66, "sc3": 0.77, "raceid": 0.35},
            "d4": {"seurat": 0.82, "sc3": 0.63, "raceid": 0.49},
        },
    }
    path = tmp_path / name
    lines = ["tool,dataset,metric,score"]
    for metric in metrics:
        for dataset, per_tool in rng_rows[metric].items():
            for tool, score in per_tool.items():
                lines.append(f"{tool},{dataset},{metric},{score}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _features(tmp_path, name="features.csv"):
    path = tmp_path / name
    path.write_text(
        "dataset,n_cells,kind\nd1,500,real\nd2,800,real\nd3,1200,sim\nd4,300,sim\n",
        encoding="utf-8",
    )
    return path


def _scores(tmp_path):
    path = tmp_path / "scores.csv"
    path.write_text(
        "tool,ari,runtime\nseurat,0.81,42.0\nsc3,0.74,310.5\nraceid,0.55,18.0\n",
        encoding="utf-8",
    )
    return path


def test_no_command_prints_help_and_errors(capsys):
    assert main([]) == 2
    assert "usage" in capsys.readouterr().err.lower()


def test_validate_ok(tmp_path, capsys):
    code = main(["validate", str(_scores(tmp_path))])
    out = capsys.readouterr().out
    assert code == 0
    assert out.startswith("ok:")
    assert "3 tools" in out


def test_validate_unknown_metric_errors(tmp_path, capsys):
    path = tmp_path / "bad.csv"
    path.write_text("tool,ari,notreal\nx,0.5,1.0\n", encoding="utf-8")
    code = main(["validate", str(path)])
    assert code == 2
    assert "beam: error:" in capsys.readouterr().err


def test_validate_metrics_subset(tmp_path, capsys):
    code = main(["validate", str(_scores(tmp_path)), "--metrics", "ari"])
    assert code == 0
    assert "1 metrics (ari)" in capsys.readouterr().out


def test_rank_to_stdout_is_json(tmp_path, capsys):
    code = main(["rank", str(_scores(tmp_path)), "--no-sensitivity"])
    assert code == 0
    record = json.loads(capsys.readouterr().out)
    assert record["params"]["method"] == "saw"
    assert len(record["ranking"]) == 3
    assert record["ranking"][0]["rank"] == 1


def test_rank_writes_record_report_and_manifest(tmp_path):
    scores = _scores(tmp_path)
    out = tmp_path / "result.json"
    report = tmp_path / "report.html"
    manifest = tmp_path / "manifest.json"
    code = main(
        [
            "rank",
            str(scores),
            "--weights",
            "entropy",
            "--method",
            "topsis",
            "--out",
            str(out),
            "--report",
            str(report),
            "--manifest",
            str(manifest),
        ]
    )
    assert code == 0
    assert out.exists() and report.exists() and manifest.exists()
    assert report.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")


def test_report_from_record_renders_html(tmp_path, capsys):
    scores = _scores(tmp_path)
    record = tmp_path / "result.json"
    main(["rank", str(scores), "--no-sensitivity", "--out", str(record)])
    report = tmp_path / "report.html"
    code = main(["report", str(record), "--out", str(report)])
    assert code == 0
    assert report.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")


def test_metric_show(capsys):
    code = main(["metric", "show", "ari"])
    out = capsys.readouterr().out
    assert code == 0
    assert "id: ari" in out
    assert "polarity: higher_is_better" in out


def test_metric_show_unknown_errors(capsys):
    code = main(["metric", "show", "nosuchmetric"])
    assert code == 2
    assert "beam: error:" in capsys.readouterr().err


def test_run_config_via_cli(tmp_path, capsys):
    scores = _scores(tmp_path)
    cfg = tmp_path / "beam.yaml"
    cfg.write_text(
        f"inputs:\n  scores: {scores.name}\naggregation:\n  method: topsis\n",
        encoding="utf-8",
    )
    code = main(["run", str(cfg)])
    assert code == 0
    assert "ranks first" in capsys.readouterr().out


def test_heterogeneity_wide_input_errors(tmp_path, capsys):
    # A wide tool by metric file has no dataset axis to decompose.
    code = main(["heterogeneity", str(_scores(tmp_path))])
    assert code == 2
    assert "dataset axis" in capsys.readouterr().err


def test_heterogeneity_requires_metric_when_several(tmp_path, capsys):
    scores = _long_scores(tmp_path, metrics=("ari", "nmi"))
    code = main(["heterogeneity", str(scores)])
    assert code == 2
    assert "--metric" in capsys.readouterr().err


def test_heterogeneity_reports_missing_r_toolchain(tmp_path, capsys, monkeypatch):
    # With the R toolchain absent the command must fail cleanly, not crash.
    monkeypatch.setattr("beam.heterogeneity.r_available", lambda: False)
    scores = _long_scores(tmp_path)
    code = main(["heterogeneity", str(scores), "--model", "mixed-effects"])
    assert code == 2
    err = capsys.readouterr().err
    assert "not available" in err
    assert "envs/heterogeneity.yml" in err


def test_heterogeneity_tree_requires_features(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr("beam.heterogeneity.bttree_available", lambda: True)
    scores = _long_scores(tmp_path)
    code = main(["heterogeneity", str(scores), "--model", "bradley-terry-tree"])
    assert code == 2
    assert "--features" in capsys.readouterr().err


def test_heterogeneity_mixed_effects_writes_report(tmp_path, capsys):
    if not r_available():
        pytest.skip("Rscript with lme4 not available")
    scores = _long_scores(tmp_path)
    out = tmp_path / "het.json"
    code = main(["heterogeneity", str(scores), "--model", "mixed-effects", "--out", str(out)])
    assert code == 0
    assert "mixed-effects on ari" in capsys.readouterr().out
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["model"] == "mixed-effects"
    assert report["metric"] == "ari"
    assert 0.0 <= report["icc_dataset"] <= 1.0
    assert len(report["method_effects"]) == 3


def test_heterogeneity_bradley_terry_tree_runs(tmp_path, capsys):
    if not bttree_available():
        pytest.skip("Rscript with psychotree not available")
    scores = _long_scores(tmp_path)
    features = _features(tmp_path)
    out = tmp_path / "tree.json"
    code = main(
        [
            "heterogeneity",
            str(scores),
            "--model",
            "bradley-terry-tree",
            "--features",
            str(features),
            "--out",
            str(out),
        ]
    )
    assert code == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["model"] == "bradley-terry-tree"
    assert set(report["feature_names"]) == {"n_cells", "kind"}
    assert report["leaf_assignment"].keys() == {"d1", "d2", "d3", "d4"}
