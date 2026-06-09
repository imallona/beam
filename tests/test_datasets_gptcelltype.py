"""Tests for the bundled GPTCelltype (Hou and Ji 2024) annotation benchmark.

These checks pin the shape, method order, coverage, feature columns and
metric-card resolution of ``beam.datasets.load_gptcelltype``, and confirm the
tensor runs through ``beam.rank``. Everything is deterministic: the data is read
from the bundled CSV with no randomness.
"""

from __future__ import annotations

import numpy as np

import beam
from beam.cards import properties_for
from beam.datasets import load_gptcelltype

EXPECTED_METHODS = (
    "GPT-4",
    "GPT-4-mar2023",
    "GPT-3.5",
    "CellMarker2.0",
    "SingleR",
    "ScType",
)
EXPECTED_METRICS = (
    "cell_type_annotation_agreement",
    "cell_type_annotation_full_match_rate",
)


def test_shape_and_labels():
    g = load_gptcelltype()
    assert g.method_names == EXPECTED_METHODS
    assert g.metric_ids == EXPECTED_METRICS
    assert g.polarity == ("higher_is_better", "higher_is_better")
    assert len(g.dataset_names) == 54
    assert g.scores.shape == (6, 54, 2)


def test_coverage_is_partial():
    g = load_gptcelltype()
    covered = {m: int(np.sum(~np.isnan(g.scores[i, :, 0]))) for i, m in enumerate(g.method_names)}
    # GPT-4, GPT-3.5 and CellMarker2.0 were run on every dataset.
    assert covered["GPT-4"] == 54
    assert covered["GPT-3.5"] == 54
    assert covered["CellMarker2.0"] == 54
    # The classical reference-based annotators and the March 2023 GPT-4 endpoint
    # were not run everywhere, so those cells are missing rather than imputed.
    assert covered["SingleR"] == 36
    assert covered["ScType"] == 36
    assert covered["GPT-4-mar2023"] == 27


def test_gpt4_leads_classical_on_mean_agreement():
    g = load_gptcelltype()
    mean_agreement = np.nanmean(g.scores[:, :, 0], axis=1)
    by_method = dict(zip(g.method_names, mean_agreement, strict=True))
    assert by_method["GPT-4"] > by_method["GPT-3.5"]
    assert by_method["GPT-4"] > by_method["CellMarker2.0"]
    assert by_method["GPT-4"] > by_method["SingleR"]


def test_full_match_rate_never_exceeds_mean_agreement():
    g = load_gptcelltype()
    agreement = g.scores[:, :, 0]
    full_rate = g.scores[:, :, 1]
    covered = ~np.isnan(agreement)
    # A full match scores 1 and a partial match 0.5, so the mean agreement is at
    # least the full match rate in every covered cell.
    assert np.all(full_rate[covered] <= agreement[covered] + 1e-12)


def test_features():
    g = load_gptcelltype()
    assert set(g.features.categorical) == {"source", "tissue", "species", "sample_type"}
    assert set(g.features.numeric) == {"n_cell_types"}
    assert set(g.features.categorical["sample_type"]) == {"normal", "cancer"}
    assert set(g.features.categorical["species"]) == {"human", "mouse"}
    by_dataset = dict(
        zip(g.features.dataset_names, g.features.categorical["sample_type"], strict=True)
    )
    assert by_dataset["BCL_B_cell_lymphoma"] == "cancer"
    assert by_dataset["Azimuth_PBMC"] == "normal"


def test_metric_cards_resolve():
    props = properties_for(list(EXPECTED_METRICS))
    for p in props:
        assert p.polarity == "higher_is_better"
        assert p.recommended_normalization == "min_max"
        assert p.range_lower == 0
        assert p.range_upper == 1


def test_rank_runs_available_case():
    g = load_gptcelltype()
    res = beam.rank(
        g.to_scores(), weights="equal", method="saw", sensitivity=False, missing="available"
    )
    # GPT-4 is not ranked last among the methods.
    gpt4_rank = res.result.ranks[g.method_names.index("GPT-4")]
    assert gpt4_rank < len(g.method_names)
