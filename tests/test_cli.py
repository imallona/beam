"""Tests for the beam command-line interface."""

from __future__ import annotations

import json

from beam.cli import main


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
