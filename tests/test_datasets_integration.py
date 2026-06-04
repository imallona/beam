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
    PancreasContrast,
    load_batchbench,
    load_integration_benchmarks,
    load_integration_published_ranks,
    load_pancreas_contrast,
)
from beam.heterogeneity import r_available, source_variance_decomposition

_METHODS = {"combat", "harmony", "fastmnn", "scanorama", "liger"}
_METRICS = {"ARI", "ASW", "kBET", "LISI"}
_BB_METRICS = {"batch_entropy", "cell_type_entropy"}
_BENCHMARKS = {"Tran", "scIB", "OpenProblems", "Tyler", "BatchBench"}
_BENCHMARKS_WITH_PUBLISHED = {"Tran", "scIB", "OpenProblems"}
needs_r = pytest.mark.skipif(not r_available(), reason="Rscript with lme4 not available")


def test_load_integration_benchmarks():
    ib = load_integration_benchmarks()
    assert isinstance(ib, IntegrationBenchmarks)
    assert set(ib.benchmark) == _BENCHMARKS
    assert set(ib.method) <= _METHODS
    assert set(ib.metric) <= _METRICS | _BB_METRICS
    # ranks within the common methods, so in [1, 5].
    assert ib.rank.min() >= 1.0 and ib.rank.max() <= 5.0


def test_mean_rank_matrix_and_records():
    ib = load_integration_benchmarks()
    methods, benchmarks, matrix = ib.mean_rank_matrix()
    # Five benchmarks now: Tran, scIB, OpenProblems, Tyler, BatchBench. Methods
    # stay the same five; Tyler covers three of them and BatchBench covers four
    # (no liger), so those columns carry NaN for the methods they do not score.
    assert matrix.shape == (5, 5)
    assert set(benchmarks) == _BENCHMARKS
    # harmony is a top method on average, though BatchBench demotes it.
    harmony = matrix[methods.index("harmony")]
    assert np.nanmean(harmony) < 3.0
    # Tyler covers harmony, scanorama, liger only; combat and fastmnn are NaN.
    tyler_col = matrix[:, benchmarks.index("Tyler")]
    covered = {methods[i] for i in range(len(methods)) if not np.isnan(tyler_col[i])}
    assert covered == {"harmony", "scanorama", "liger"}
    # BatchBench covers the four non-liger common methods.
    bb_col = matrix[:, benchmarks.index("BatchBench")]
    bb_covered = {methods[i] for i in range(len(methods)) if not np.isnan(bb_col[i])}
    assert bb_covered == {"combat", "harmony", "fastmnn", "scanorama"}
    m, d, b, s = ib.mean_rank_records()
    assert len(m) == len(d) == len(b) == len(s)
    assert set(b) == _BENCHMARKS


def test_published_ranks():
    # Tyler does not publish an overall ranking (the paper is a methodological
    # critique, not a recommendation), so it is not in the published-ranks file.
    pub = load_integration_published_ranks()
    assert set(pub) == _BENCHMARKS_WITH_PUBLISHED
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


def test_load_batchbench():
    bb = load_batchbench()
    assert bb.metric_ids == ("batch_entropy", "cell_type_entropy")
    assert bb.polarity == ("higher_is_better", "lower_is_better")
    assert bb.scores.shape == (8, 30, 2)
    assert {"combat", "harmony", "fastmnn", "scanorama"} <= set(bb.method_names)
    assert np.isfinite(bb.scores).all()  # the entropy table has no missing cells
    assert set(bb.features) == {"n_cells", "n_genes", "n_cell_types", "n_batches"}
    # harmony blurs cell types more than combat (higher cell-type entropy is
    # worse for biology), the tradeoff the bio/batch reading rests on.
    cell = bb.metric_ids.index("cell_type_entropy")
    harmony = bb.method_names.index("harmony")
    combat = bb.method_names.index("combat")
    assert np.nanmean(bb.scores[harmony, :, cell]) > np.nanmean(bb.scores[combat, :, cell])


def test_method_metric_matrix_per_benchmark():
    ib = load_integration_benchmarks()
    # method_metric_matrix is defined on the shared scIB metric family; BatchBench
    # scores on its own entropy metrics, so it is off-family here.
    for bench in _BENCHMARKS - {"BatchBench"}:
        methods, metrics, matrix = ib.method_metric_matrix(bench)
        assert methods == ("combat", "harmony", "fastmnn", "scanorama", "liger")
        assert metrics == ("ARI", "ASW", "kBET", "LISI")
        assert matrix.shape == (5, 4)
        assert np.nanmin(matrix) >= 1.0 and np.nanmax(matrix) <= 5.0


def test_per_benchmark_smallest_weight_perturbation():
    # Verify the smallest_weight_perturbation primitive runs cleanly on each
    # benchmark's mean-rank matrix and that the fragility ordering makes sense.
    from beam.mcda import smallest_weight_perturbation

    ib = load_integration_benchmarks()
    polarity = ("lower_is_better",) * 4
    deltas = {}
    for bench in ("Tran", "scIB", "OpenProblems"):
        _, _, matrix = ib.method_metric_matrix(bench)
        rep = smallest_weight_perturbation(matrix, polarity=polarity, weights="equal", method="saw")
        assert rep.top_rank_perturbation is not None, f"{bench}: no flip found"
        deltas[bench] = rep.top_rank_perturbation.absolute_delta
    # The three benchmarks should not all be equally fragile; if they were,
    # something has masked the per-benchmark structure.
    assert max(deltas.values()) - min(deltas.values()) > 0.1


def test_load_pancreas_contrast():
    # Tran D4 and scIB pancreas share the same five studies (Baron, Muraro,
    # Segerstolpe, Wang, Xin), so the pipelines compete on the same data.
    pc = load_pancreas_contrast()
    assert isinstance(pc, PancreasContrast)
    assert pc.methods == ("combat", "harmony", "fastmnn", "scanorama", "liger")
    assert pc.metrics == ("ARI", "ASW", "kBET", "LISI")
    assert pc.tran_rank.shape == (5, 4)
    assert pc.scib_rank.shape == (5, 4)
    # Ranks within five methods, so every cell lies in [1, 5].
    assert np.nanmin(pc.tran_rank) >= 1.0 and np.nanmax(pc.tran_rank) <= 5.0
    assert np.nanmin(pc.scib_rank) >= 1.0 and np.nanmax(pc.scib_rank) <= 5.0
    # Both pipelines agree harmony ranks first on the shared data.
    tran_top, scib_top = pc.top_method()
    assert tran_top == scib_top == "harmony"
    # The two pipelines disagree on the rest: Spearman is moderate, not perfect.
    rho = pc.spearman()
    assert 0.2 < rho < 0.95, f"expected moderate Spearman, got {rho:.3f}"


@needs_r
def test_source_variance_on_real_benchmarks():
    ib = load_integration_benchmarks()
    methods, datasets, benchmarks, scores = ib.mean_rank_records()
    rep = source_variance_decomposition(methods, datasets, benchmarks, scores)
    assert rep.n_benchmarks == 5
    assert 0.0 <= rep.method_benchmark_share <= 1.0
    assert np.isfinite(rep.total_variance)
