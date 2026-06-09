"""Tests for the bundled DeepCellSeek (Briefings 2025) annotation benchmark.

These checks pin the shape, method roster, the shared classical methods with the
GPTCelltype benchmark, and metric-card resolution of
``beam.datasets.load_deepcellseek``. Everything is deterministic.
"""

from __future__ import annotations

import numpy as np

from beam.datasets import load_deepcellseek, load_gptcelltype

CLASSICAL = ("CellMarker2.0", "SingleR", "ScType")


def test_shape_and_roster():
    d = load_deepcellseek()
    assert d.metric_ids == (
        "cell_type_annotation_agreement",
        "cell_type_annotation_full_match_rate",
    )
    assert d.scores.shape == (len(d.method_names), len(d.dataset_names), 2)
    assert len(d.method_names) == 14
    # the three classical annotators are present with the GPTCelltype labels
    for m in CLASSICAL:
        assert m in d.method_names
    # 11 LLM endpoints make up the rest
    assert len(set(d.method_names) - set(CLASSICAL)) == 11


def test_scores_complete_and_bounded():
    d = load_deepcellseek()
    assert np.all(np.isfinite(d.scores))
    assert d.scores.min() >= 0.0 and d.scores.max() <= 1.0


def test_llms_outrank_classical():
    d = load_deepcellseek()
    mean_agreement = dict(zip(d.method_names, np.nanmean(d.scores[:, :, 0], axis=1), strict=True))
    best_classical = max(mean_agreement[m] for m in CLASSICAL)
    llm_means = [mean_agreement[m] for m in d.method_names if m not in CLASSICAL]
    # every LLM endpoint outranks the best classical annotator on this benchmark
    assert min(llm_means) > best_classical


def test_full_match_rate_never_exceeds_mean_agreement():
    d = load_deepcellseek()
    agreement = d.scores[:, :, 0]
    full_rate = d.scores[:, :, 1]
    assert np.all(full_rate <= agreement + 1e-12)


def test_cell_type_filter():
    broad = load_deepcellseek("Broad Cell type")
    everything = load_deepcellseek("all")
    # "all" keeps at least as many datasets as the broad subset
    assert len(everything.dataset_names) >= len(broad.dataset_names)


def test_shares_classical_methods_with_gptcelltype():
    g = load_gptcelltype()
    d = load_deepcellseek()
    shared = set(g.method_names) & set(d.method_names)
    # the three classical annotators are the common methods for a cross-benchmark
    # comparison; the GPT endpoints differ by version (GPT-4/3.5 vs GPT-4o/5)
    assert set(CLASSICAL).issubset(shared)
