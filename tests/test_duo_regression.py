"""Regression coverage for the Duo 2018 MCDA re-analysis.

These tests pin the computation the duo2018 vignette runs on the real
``beam.datasets.load_duo2018`` data, so a change in the pooling, the
normalization, or any aggregation method that moves the ranking is caught.

The reference is pymcdm. We build the pooled, normalized 14 by 3 matrix
exactly as the vignette does (ARI and Shannon entropy difference pooled by
NaN-aware arithmetic mean, runtime by NaN-aware geometric mean, then the
ontology-aware ``run_from_registry`` pipeline), and assert that beam's
induced ranking matches pymcdm for saw, topsis, vikor and promethee_ii.

We feed pymcdm beam's already-normalized matrix with all criterion types
set to +1, using an identity per-column normalization. beam's normalized
columns are oriented higher-is-better and lie in [0, 1], but they do not
all span the full [0, 1] (the column min is mapped to 0 only when the
worst tool defines the empirical bound). pymcdm's built-in minmax would
re-stretch each column, an affine rescale that changes the relative column
scale and so changes a weighted sum; the identity normalization keeps the
matrix beam produced, which is the faithful cross-check.

Everything is deterministic. The only randomness is the SMAA-free
stability check, which fixes seeds where seeds apply.
"""

from __future__ import annotations

import numpy as np
import pytest
from pymcdm.helpers import rankdata, rrankdata
from pymcdm.methods import PROMETHEE_II, TOPSIS, VIKOR, WSM

from beam.cards import properties_for
from beam.datasets import load_duo2018
from beam.mcda import run_from_registry

ANALYSIS_METRICS = ["ari", "runtime", "shannon_entropy_diff"]


def _pool_metric(matrix: np.ndarray, rule: str) -> np.ndarray:
    """NaN-aware pooling of a method by dataset matrix to a method vector."""
    if rule == "arithmetic_mean":
        return np.nanmean(matrix, axis=1)
    if rule == "geometric_mean":
        return np.exp(np.nanmean(np.log(matrix), axis=1))
    raise ValueError(f"unsupported pooling rule {rule!r}")


def _pooled_matrix() -> np.ndarray:
    """The pooled 14 by 3 matrix the vignette feeds to the MCDA pipeline."""
    duo = load_duo2018()
    props = properties_for(ANALYSIS_METRICS)
    columns = [
        _pool_metric(
            duo.tensor((p.id,))[:, :, 0],
            p.recommended_aggregation_across_datasets,
        )
        for p in props
    ]
    return np.column_stack(columns)


def _identity_normalization(column: np.ndarray, cost: bool = False) -> np.ndarray:
    """Return the column unchanged; beam already normalized it to [0, 1]."""
    return np.asarray(column, dtype=float)


def test_pooled_matrix_is_finite():
    """No NaN may leak through the NaN-aware pooling into the MCDA matrix."""
    pooled = _pooled_matrix()
    assert pooled.shape == (14, 3)
    assert np.isfinite(pooled).all()


@pytest.mark.parametrize("method", ["saw", "topsis", "vikor", "promethee_ii"])
def test_beam_matches_pymcdm(method):
    """beam's ranking equals pymcdm on the same normalized matrix, equal weights."""
    pooled = _pooled_matrix()
    beam_result = run_from_registry(pooled, ANALYSIS_METRICS, weights="equal", method=method)

    normalized = beam_result.normalized
    n_metrics = normalized.shape[1]
    weights = np.full(n_metrics, 1.0 / n_metrics)
    types = np.ones(n_metrics, dtype=int)

    if method == "saw":
        preference = WSM(_identity_normalization)(normalized, weights, types)
        reference_ranks = rrankdata(preference)
    elif method == "topsis":
        preference = TOPSIS(_identity_normalization)(normalized, weights, types)
        reference_ranks = rrankdata(preference)
    elif method == "vikor":
        # VIKOR returns the Q compromise measure where lower is better.
        preference = VIKOR(_identity_normalization)(normalized, weights, types)
        reference_ranks = rankdata(preference)
    else:
        preference = PROMETHEE_II("usual")(normalized, weights, types)
        reference_ranks = rrankdata(preference)

    np.testing.assert_array_equal(beam_result.ranks, reference_ranks.astype(int))


def test_top_ranked_method_is_seurat_under_default():
    """The default pipeline ranks Seurat first on the three pooled metrics."""
    duo = load_duo2018()
    pooled = _pooled_matrix()
    result = run_from_registry(pooled, ANALYSIS_METRICS, weights="equal", method="saw")
    top = duo.method_names[int(np.argmin(result.ranks))]
    assert top == "Seurat"


def test_top_ranked_method_is_stable_across_weightings():
    """Seurat stays top-ranked under equal, entropy, std and critic weights (SAW)."""
    duo = load_duo2018()
    pooled = _pooled_matrix()
    tops = set()
    for weighting in ["equal", "entropy", "std", "critic"]:
        result = run_from_registry(pooled, ANALYSIS_METRICS, weights=weighting, method="saw")
        tops.add(duo.method_names[int(np.argmin(result.ranks))])
    assert tops == {"Seurat"}
