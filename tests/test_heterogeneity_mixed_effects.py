"""Tests for the mixed-effects variance decomposition.

The fitting tests need R with lme4 and are skipped when that toolchain is
absent. The input-validation tests run everywhere.
"""

from __future__ import annotations

import numpy as np
import pytest

from beam.datasets import load_duo2018
from beam.heterogeneity import (
    MixedEffectsReport,
    mixed_effects,
    mixed_effects_from_matrix,
    r_available,
)

HAVE_R = r_available()
needs_r = pytest.mark.skipif(not HAVE_R, reason="Rscript with lme4 not available")


def test_r_available_returns_bool():
    assert isinstance(r_available(), bool)


def test_length_mismatch_rejected():
    with pytest.raises(ValueError, match="same length"):
        mixed_effects(["a", "b"], ["d1"], [1.0, 2.0])


def test_too_few_methods_rejected():
    with pytest.raises(ValueError, match="2 distinct methods"):
        mixed_effects(["a", "a"], ["d1", "d2"], [1.0, 2.0])


def test_too_few_datasets_rejected():
    with pytest.raises(ValueError, match="2 distinct datasets"):
        mixed_effects(["a", "b"], ["d1", "d1"], [1.0, 2.0])


def test_bad_formula_kind_rejected():
    with pytest.raises(ValueError, match="formula_kind"):
        mixed_effects(["a", "b"], ["d1", "d2"], [1.0, 2.0], formula_kind="nonsense")


def test_matrix_shape_validation():
    with pytest.raises(ValueError, match="2D"):
        mixed_effects_from_matrix(np.zeros((2, 2, 2)), ["a", "b"], ["d1", "d2"])
    with pytest.raises(ValueError, match="method_names"):
        mixed_effects_from_matrix(np.zeros((2, 3)), ["a"], ["d1", "d2", "d3"])
    with pytest.raises(ValueError, match="dataset_names"):
        mixed_effects_from_matrix(np.zeros((2, 3)), ["a", "b"], ["d1", "d2"])


def _additive_matrix(method_effects, dataset_shifts, noise_sd, seed):
    """Single observation per cell: score = method effect + dataset shift + noise."""
    rng = np.random.default_rng(seed)
    n_m, n_d = len(method_effects), len(dataset_shifts)
    matrix = np.empty((n_m, n_d))
    for i, me in enumerate(method_effects):
        for j, ds in enumerate(dataset_shifts):
            matrix[i, j] = me + ds + rng.normal(0.0, noise_sd)
    return matrix


@needs_r
def test_dataset_shift_dominates_variance():
    method_effects = [0.0, 0.5, 1.0, 1.5]
    dataset_shifts = list(np.linspace(-5.0, 5.0, 12))
    matrix = _additive_matrix(method_effects, dataset_shifts, noise_sd=0.05, seed=1)
    methods = [f"m{i}" for i in range(4)]
    datasets = [f"d{j}" for j in range(12)]

    rep = mixed_effects_from_matrix(matrix, methods, datasets)

    assert isinstance(rep, MixedEffectsReport)
    assert rep.formula_kind == "main"
    assert rep.interaction_share is None
    assert rep.icc_dataset > 0.95
    assert rep.n_obs == 48
    # The large additive dataset shift is recovered as the dominant component.
    assert rep.variance_components["dataset"] > rep.variance_components["Residual"]


@needs_r
def test_method_effects_recover_ordering():
    method_effects = [0.0, 1.0, 2.0, 3.0]
    dataset_shifts = list(np.linspace(-1.0, 1.0, 10))
    matrix = _additive_matrix(method_effects, dataset_shifts, noise_sd=0.05, seed=2)
    methods = ["alpha", "beta", "gamma", "delta"]
    datasets = [f"d{j}" for j in range(10)]

    rep = mixed_effects_from_matrix(matrix, methods, datasets)

    by_effect = [rep.method_names[i] for i in np.argsort(rep.method_effects)]
    assert by_effect == ["alpha", "beta", "gamma", "delta"]
    # Each fitted marginal mean lands near its true method effect.
    truth = dict(zip(methods, method_effects, strict=True))
    for name, est in zip(rep.method_names, rep.method_effects, strict=True):
        assert abs(est - truth[name]) < 0.2


@needs_r
def test_interaction_model_with_replicates():
    rng = np.random.default_rng(3)
    methods, datasets, scores = [], [], []
    interaction = rng.normal(0.0, 3.0, size=(4, 8))
    for i in range(4):
        for j in range(8):
            cell_mean = 0.2 * i + 0.1 * j + interaction[i, j]
            for _ in range(4):
                methods.append(f"m{i}")
                datasets.append(f"d{j}")
                scores.append(cell_mean + rng.normal(0.0, 0.1))

    rep = mixed_effects(methods, datasets, scores)

    assert rep.has_replicates
    assert rep.formula_kind == "interaction"
    assert "dataset:method" in rep.variance_components
    assert rep.interaction_share is not None
    # The injected interaction dwarfs the dataset shift and the noise.
    assert rep.interaction_share > 0.8


@needs_r
def test_forced_main_model_ignores_replicates():
    methods = ["a", "a", "b", "b"] * 3
    datasets = ["d1", "d2", "d1", "d2"] * 3
    scores = list(np.random.default_rng(4).normal(size=12))

    rep = mixed_effects(methods, datasets, scores, formula_kind="main")

    assert rep.formula_kind == "main"
    assert "dataset:method" not in rep.variance_components
    assert rep.has_replicates


@needs_r
def test_duo_ari_decomposition():
    duo = load_duo2018()
    ari = duo.tensor(("ari",))[:, :, 0]

    rep = mixed_effects_from_matrix(ari, duo.method_names, duo.dataset_names)

    assert rep.formula_kind == "main"
    assert rep.n_methods == 14
    assert rep.n_datasets == 12
    # 5 of the 168 ARI cells are missing and dropped before the fit.
    assert rep.n_obs == 163
    assert len(rep.residuals) == rep.n_obs
    assert len(rep.residual_methods) == rep.n_obs
    # SC3 and Seurat lead the ARI marginal means, matching findings 0001.
    leaders = {rep.method_names[i] for i in np.argsort(-rep.method_effects)[:2]}
    assert leaders == {"SC3", "Seurat"}
    assert 0.0 < rep.icc_dataset < 1.0
    # RaceID2, the bottom method, produces the largest interaction residuals.
    top_methods = {m for m, _, _ in rep.top_outliers(3)}
    assert "RaceID2" in top_methods


@needs_r
def test_top_outliers_sorted_and_capped():
    matrix = _additive_matrix([0.0, 1.0, 2.0], list(np.linspace(-1, 1, 6)), 0.3, seed=5)
    rep = mixed_effects_from_matrix(matrix, ["a", "b", "c"], [f"d{j}" for j in range(6)])

    outliers = rep.top_outliers(4)
    assert len(outliers) == 4
    magnitudes = [abs(r) for _, _, r in outliers]
    assert magnitudes == sorted(magnitudes, reverse=True)
