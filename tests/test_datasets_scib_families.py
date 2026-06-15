"""Tests for the scIB classical and deep-learning method blocks.

These checks pin the shape, the family split, the shared metric set, and the
available-case handling of ``beam.datasets.load_scib_integration_families``, and
confirm the classical scores match the block already used by
``load_integration_benchmarks``. Everything is deterministic.
"""

from __future__ import annotations

import numpy as np

from beam.datasets import _load_scib_cells, load_scib_integration_families
from beam.mcda import dataset_discrimination, difficulty_concordance

CLASSICAL = ("combat", "harmony", "fastmnn", "scanorama", "liger")
DEEP = ("scVI", "scANVI", "scGen", "DESC", "SAUCIE", "trVAE")


def test_shape_and_families():
    f = load_scib_integration_families()
    assert f.method_names == CLASSICAL + DEEP
    assert f.families == ("classical",) * 5 + ("deep learning",) * 6
    assert f.metric_ids == ("ARI", "ASW", "kBET", "LISI")
    assert set(f.polarity) == {"higher_is_better"}
    assert f.dataset_names == (
        "immune_cell_hum",
        "immune_cell_hum_mou",
        "lung_atlas",
        "mouse_brain",
        "pancreas",
    )
    assert f.scores.shape == (11, 5, 4)


def test_classical_block_matches_integration_source():
    f = load_scib_integration_families()
    cells = _load_scib_cells()
    di = {d: i for i, d in enumerate(f.dataset_names)}
    ki = {k: i for i, k in enumerate(f.metric_ids)}
    for (dataset, metric), by_method in cells.items():
        if dataset not in di or metric not in ki:
            continue
        for method, value in by_method.items():
            got = f.scores[f.method_names.index(method), di[dataset], ki[metric]]
            assert np.isclose(got, value)


def test_missing_cells_are_nan_not_imputed():
    f = load_scib_integration_families()
    # trVAE is scored on three of the five datasets in the source, so its row
    # carries gaps that must stay nan.
    trvae = f.scores[f.method_names.index("trVAE")]
    assert np.isnan(trvae).any()
    assert np.isfinite(f.scores).any()


def test_scores_bounded_where_observed():
    f = load_scib_integration_families()
    observed = f.scores[np.isfinite(f.scores)]
    assert observed.min() >= 0.0
    assert observed.max() <= 1.0


def test_difficulty_concordance_runs_on_families():
    f = load_scib_integration_families()
    conc = difficulty_concordance(f.scores, f.polarity, f.families, dataset_ids=f.dataset_names)
    assert conc.family_names == ("classical", "deep learning")
    assert conc.coverage[0, 1] == 5
    assert -1.0 <= conc.concordance[0, 1] <= 1.0


def test_dataset_discrimination_runs():
    f = load_scib_integration_families()
    disc = dataset_discrimination(f.scores, f.polarity, dataset_ids=f.dataset_names)
    assert disc.most_discriminating in f.dataset_names
    assert np.isfinite(disc.mean_spread)
