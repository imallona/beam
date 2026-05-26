"""Tests for the cross-benchmark variance decomposition.

The fit needs R with lme4 and is skipped when that toolchain is absent. The
input-validation tests run everywhere.
"""

from __future__ import annotations

import numpy as np
import pytest

from beam.heterogeneity import (
    SourceVarianceReport,
    r_available,
    source_variance_decomposition,
)

HAVE_R = r_available()
needs_r = pytest.mark.skipif(not HAVE_R, reason="Rscript with lme4 not available")


def test_length_mismatch_rejected():
    with pytest.raises(ValueError, match="same length"):
        source_variance_decomposition(["a", "b"], ["d1", "d2"], ["A"], [1.0, 2.0])


def test_too_few_methods_rejected():
    with pytest.raises(ValueError, match="2 distinct methods"):
        source_variance_decomposition(["a", "a"], ["d1", "d2"], ["A", "B"], [1.0, 2.0])


def test_too_few_benchmarks_rejected():
    with pytest.raises(ValueError, match="2 distinct benchmarks"):
        source_variance_decomposition(["a", "b"], ["d1", "d2"], ["A", "A"], [1.0, 2.0])


def _two_benchmark_data(interaction_sd, seed):
    """Five methods scored on six datasets by each of two benchmarks.

    ``interaction_sd`` controls a benchmark-specific offset per method, the
    method-by-benchmark interaction. Datasets are nested in benchmark (each
    benchmark brings its own), as in real cross-benchmark data.
    """
    rng = np.random.default_rng(seed)
    methods = [f"m{i}" for i in range(5)]
    benchmarks = ["A", "B"]
    base = {m: rng.normal(0, 1) for m in methods}
    offset = {(m, b): rng.normal(0, interaction_sd) for m in methods for b in benchmarks}
    M, D, B, S = [], [], [], []
    for b in benchmarks:
        b_shift = rng.normal(0, 0.5)
        for j in range(6):
            d_shift = rng.normal(0, 0.5)
            for m in methods:
                M.append(m)
                D.append(f"{b}_d{j}")
                B.append(b)
                S.append(base[m] + b_shift + d_shift + offset[(m, b)] + rng.normal(0, 0.1))
    return M, D, B, S


@needs_r
def test_disagreement_attributed_to_method_benchmark():
    methods, datasets, benchmarks, scores = _two_benchmark_data(interaction_sd=2.0, seed=0)
    rep = source_variance_decomposition(methods, datasets, benchmarks, scores)

    assert isinstance(rep, SourceVarianceReport)
    assert rep.n_methods == 5
    assert rep.n_benchmarks == 2
    assert "method:benchmark" in rep.variance_components
    # The injected method-by-benchmark disagreement dominates the variance.
    assert rep.method_benchmark_share > 0.7


@needs_r
def test_agreement_gives_small_method_benchmark_share():
    methods, datasets, benchmarks, scores = _two_benchmark_data(interaction_sd=0.05, seed=1)
    rep = source_variance_decomposition(methods, datasets, benchmarks, scores)

    # When methods rank the same in both benchmarks, little variance is the
    # method-by-benchmark interaction.
    assert rep.method_benchmark_share < 0.3
    # The shares sum to one over the components.
    total = (
        rep.benchmark_share + rep.dataset_share + rep.method_benchmark_share + rep.residual_share
    )
    assert abs(total - 1.0) < 1e-6
