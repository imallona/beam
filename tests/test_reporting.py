"""Tests for the HTML report and the recommendation narrative."""

from __future__ import annotations

import subprocess
import sys

import numpy as np

import beam
from beam.api import rank
from beam.datasets import load_duo2018
from beam.reporting import write_report
from beam.reporting.narrative import recommendation


def _toy_result(method="saw", sensitivity=True):
    matrix = np.array([[0.9, 30.0], [0.7, 50.0], [0.5, 20.0]])
    return rank(matrix, metric_ids=["ari", "runtime"], method=method, sensitivity=sensitivity)


def test_report_is_exposed_at_top_level():
    assert beam.report is write_report


def test_importing_beam_does_not_override_the_matplotlib_backend():
    # The report figures must not force a backend (no matplotlib.use), or
    # importing beam would break inline plotting in the Quarto vignettes. Run
    # in a subprocess so the check starts from a clean matplotlib state.
    script = (
        "import matplotlib; matplotlib.use('svg');"
        "import beam; from beam.reporting import figures; import numpy as np;"
        "figures.ranking_figure(('a','b','c'), np.array([0.6,0.4,0.5]), np.array([1,3,2]));"
        "b = matplotlib.get_backend().lower();"
        "assert b == 'svg', b; print('ok')"
    )
    proc = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert "ok" in proc.stdout


def test_write_report_produces_self_contained_html(tmp_path):
    result = _toy_result()
    out = tmp_path / "report.html"
    write_report(result, out)
    html = out.read_text(encoding="utf-8")
    assert html.startswith("<!DOCTYPE html>")
    # Figures are embedded, not linked.
    assert "data:image/png;base64," in html
    assert 'src="http' not in html
    assert result.top_tool in html


def test_report_without_sensitivity_omits_those_sections(tmp_path):
    result = _toy_result(sensitivity=False)
    out = tmp_path / "report.html"
    write_report(result, out)
    html = out.read_text(encoding="utf-8")
    assert "SMAA weight sampling" not in html
    assert "Leave one metric out" not in html


def test_report_includes_sensitivity_sections(tmp_path):
    result = _toy_result(sensitivity=True)
    out = tmp_path / "report.html"
    write_report(result, out)
    html = out.read_text(encoding="utf-8")
    assert "SMAA weight sampling" in html
    assert "Leave one metric out" in html
    assert "Smallest weight perturbation" in html


def test_recommendation_text_follows_style_rules():
    text = recommendation(_toy_result())
    assert "ranks first" in text
    # The project forbids winner/wins phrasing, em dashes, and bold markers.
    lowered = text.lower()
    assert "winner" not in lowered
    assert "wins" not in lowered
    assert "best" not in lowered
    assert "worst" not in lowered
    assert "\u2014" not in text  # em dash
    assert "\u2013" not in text  # en dash
    assert "**" not in text
    # The claim is tied to the metric set and the weighting.
    assert "ari" in text and "runtime" in text


def test_report_draws_critical_difference_for_multidataset(tmp_path):
    duo = load_duo2018()
    metric_ids = ("ari", "runtime", "shannon_entropy_diff")
    tensor = duo.tensor(metric_ids)
    complete = duo.complete_methods(metric_ids)
    scores = beam.Scores(
        values=tensor[complete],
        tool_names=tuple(np.array(duo.method_names)[complete].tolist()),
        metric_ids=metric_ids,
        dataset_names=duo.dataset_names,
        layout="long",
    )
    result = rank(scores, weights="entropy", method="topsis", sensitivity=False)
    out = tmp_path / "duo.html"
    write_report(result, out)
    html = out.read_text(encoding="utf-8")
    assert "Critical difference across datasets" in html
    assert "Friedman test p-value" in html


def test_single_dataset_report_has_no_cd_section(tmp_path):
    result = _toy_result(sensitivity=False)
    out = tmp_path / "report.html"
    write_report(result, out)
    html = out.read_text(encoding="utf-8")
    assert "Critical difference across datasets" not in html


def test_report_includes_leave_one_dataset_out_for_tensor(tmp_path):
    duo = load_duo2018()
    metric_ids = ("ari", "runtime", "shannon_entropy_diff")
    tensor = duo.tensor(metric_ids)
    complete = duo.complete_methods(metric_ids)
    scores = beam.Scores(
        values=tensor[complete],
        tool_names=tuple(np.array(duo.method_names)[complete].tolist()),
        metric_ids=metric_ids,
        dataset_names=duo.dataset_names,
        layout="long",
    )
    result = rank(scores, weights="equal", method="saw")
    assert result.leave_one_dataset_out is not None
    out = tmp_path / "duo.html"
    write_report(result, out)
    html = out.read_text(encoding="utf-8")
    assert "Leave one dataset out" in html
    assert "leave-one-dataset-out runs" in html


def test_single_dataset_report_has_no_lodo_section(tmp_path):
    result = _toy_result(sensitivity=True)
    out = tmp_path / "report.html"
    write_report(result, out)
    html = out.read_text(encoding="utf-8")
    assert "Leave one dataset out" not in html


def test_ground_truth_tool_is_labelled(tmp_path):
    result = _toy_result(sensitivity=False)
    out = tmp_path / "report.html"
    # Should not raise when a documented-first tool is named.
    write_report(result, out, ground_truth_tool=result.top_tool)
    assert out.exists()


def test_report_includes_funky_heatmap_by_default(tmp_path):
    result = _toy_result(sensitivity=True)
    out = tmp_path / "report.html"
    write_report(result, out)
    html = out.read_text(encoding="utf-8")
    assert "Robustness at a glance" in html
    assert "funky heatmap with rank-robustness" in html


def test_funky_heatmap_can_be_disabled(tmp_path):
    result = _toy_result(sensitivity=True)
    out = tmp_path / "report.html"
    write_report(result, out, funky_heatmap=False)
    html = out.read_text(encoding="utf-8")
    assert "Robustness at a glance" not in html
    # The aggregation-agreement sentence is a sensitivity result, not part of
    # the glyph table, so it still appears when the figure is turned off.
    assert "Aggregation agreement" in html


def test_report_reports_aggregation_agreement(tmp_path):
    result = _toy_result(sensitivity=True)
    out = tmp_path / "report.html"
    write_report(result, out)
    html = out.read_text(encoding="utf-8")
    assert "Aggregation agreement" in html
    assert "Kendall tau-b" in html
