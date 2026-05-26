"""Tests for the cross-benchmark single-cell integration set.

The loader and the agreement comparison run everywhere. The variance
decomposition needs R with lme4 and is skipped when it is absent.
"""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations

import numpy as np
import pytest
from scipy.stats import spearmanr

from beam.datasets import (
    IntegrationBenchmarks,
    load_integration_benchmarks,
    load_integration_published_ranks,
)
from beam.heterogeneity import r_available, source_variance_decomposition

_METHODS = {"combat", "harmony", "fastmnn", "scanorama", "liger"}
_METRICS = {"ARI", "ASW", "kBET", "LISI"}
_BENCHMARKS = {"Tran", "scIB", "OpenProblems"}
needs_r = pytest.mark.skipif(not r_available(), reason="Rscript with lme4 not available")


def test_load_integration_benchmarks():
    ib = load_integration_benchmarks()
    assert isinstance(ib, IntegrationBenchmarks)
    assert set(ib.benchmark) == _BENCHMARKS
    assert set(ib.method) <= _METHODS
    assert set(ib.metric) <= _METRICS
    # ranks within the five common methods, so in [1, 5].
    assert ib.rank.min() >= 1.0 and ib.rank.max() <= 5.0


def test_mean_rank_matrix_and_records():
    ib = load_integration_benchmarks()
    methods, _benchmarks, matrix = ib.mean_rank_matrix()
    assert matrix.shape == (5, 3)
    # harmony is a stable top method, so its mean rank is among the best.
    harmony = matrix[methods.index("harmony")]
    assert np.nanmean(harmony) < 3.0
    m, d, b, s = ib.mean_rank_records()
    assert len(m) == len(d) == len(b) == len(s)
    assert set(b) == _BENCHMARKS


def test_published_ranks():
    pub = load_integration_published_ranks()
    assert set(pub) == _BENCHMARKS
    assert all(set(pub[b]) == _METHODS for b in pub)
    # combat is reported very differently across benchmarks, the disagreement.
    assert pub["Tran"]["combat"] == 5
    assert pub["OpenProblems"]["combat"] == 1


def test_beam_ranking_agrees_more_than_published():
    # The headline result: re-ranking with one consistent rule raises the
    # cross-benchmark agreement above the benchmarks' own reported rankings.
    canon = ["combat", "harmony", "fastmnn", "scanorama", "liger"]
    benchmarks = ["Tran", "scIB", "OpenProblems"]
    pub = load_integration_published_ranks()
    ib = load_integration_benchmarks()
    cell = defaultdict(list)
    for b, _d, m, _mk, r in zip(
        ib.benchmark, ib.dataset, ib.method, ib.metric, ib.rank, strict=True
    ):
        cell[(b, m)].append(r)

    def mean_spearman(vectors):
        return float(
            np.mean(
                [
                    spearmanr(vectors[a], vectors[b]).correlation
                    for a, b in combinations(benchmarks, 2)
                ]
            )
        )

    published = mean_spearman({b: np.array([pub[b][m] for m in canon]) for b in benchmarks})
    beam = mean_spearman({b: np.array([np.mean(cell[(b, m)]) for m in canon]) for b in benchmarks})
    assert published < 0.1  # reported rankings barely agree
    assert beam > 0.4  # the consistent ranking agrees much more
    assert beam - published > 0.3


@needs_r
def test_source_variance_on_real_benchmarks():
    ib = load_integration_benchmarks()
    methods, datasets, benchmarks, scores = ib.mean_rank_records()
    rep = source_variance_decomposition(methods, datasets, benchmarks, scores)
    assert rep.n_benchmarks == 3
    assert 0.0 <= rep.method_benchmark_share <= 1.0
    assert np.isfinite(rep.total_variance)
