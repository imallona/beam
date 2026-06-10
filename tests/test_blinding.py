"""Tests for analysis blinding: relabel, run, unblind."""

import numpy as np
import pytest

import beam
from beam import Scores, blind, unblind
from beam.blinding import Seal, read_seal, write_seal


def _wide_scores():
    return Scores(
        values=np.array([[0.9, 0.1], [0.5, 0.5], [0.2, 0.8]]),
        tool_names=("seurat", "sc3", "raceid"),
        metric_ids=("ari", "runtime"),
        dataset_names=None,
        layout="wide",
    )


def test_blind_relabels_and_hides_true_names():
    scores = _wide_scores()
    blinded, seal = blind(scores, seed=1)
    assert set(blinded.tool_names) == {"method_1", "method_2", "method_3"}
    assert set(seal.mapping.values()) == set(scores.tool_names)
    assert all(name not in blinded.tool_names for name in scores.tool_names)
    assert blinded.blinding_sha256 == seal.fingerprint


def test_blind_is_deterministic_under_seed():
    scores = _wide_scores()
    a, seal_a = blind(scores, seed=7)
    b, seal_b = blind(scores, seed=7)
    assert seal_a.mapping == seal_b.mapping
    assert np.array_equal(a.values, b.values)
    assert seal_a.fingerprint == seal_b.fingerprint


def test_different_seeds_differ():
    scores = _wide_scores()
    _, seal_a = blind(scores, seed=1)
    _, seal_b = blind(scores, seed=2)
    assert seal_a.mapping != seal_b.mapping or seal_a.fingerprint != seal_b.fingerprint


def test_unblind_scores_restores_names_and_keeps_rows():
    scores = _wide_scores()
    blinded, seal = blind(scores, seed=3)
    restored = unblind(blinded, seal)
    # the blinded order is kept; names match the seal translation of the labels.
    assert restored.tool_names == tuple(seal.translate(blinded.tool_names))
    assert restored.blinding_sha256 is None
    # the row values line up with the restored names: find seurat's row.
    seurat_pos = restored.tool_names.index("seurat")
    assert np.array_equal(restored.values[seurat_pos], np.array([0.9, 0.1]))


def test_ranking_is_invariant_under_blinding():
    scores = _wide_scores()
    plain = beam.rank(scores, weights="equal", method="saw")
    blinded, seal = blind(scores, seed=5)
    blind_run = beam.rank(blinded, weights="equal", method="saw")
    restored = unblind(blind_run, seal)
    # each tool gets the same rank whether or not the labels were hidden.
    plain_rank = dict(zip(plain.tool_names, plain.result.ranks, strict=True))
    restored_rank = dict(zip(restored.tool_names, restored.result.ranks, strict=True))
    assert plain_rank == restored_rank


def test_manifest_records_the_blinding():
    scores = _wide_scores()
    blinded, seal = blind(scores, seed=2)
    run = beam.rank(blinded, weights="equal", method="saw")
    assert run.manifest["blinding"]["blinded"] is True
    assert run.manifest["blinding"]["seal_sha256"] == seal.fingerprint
    # a plain run carries no blinding key.
    plain = beam.rank(scores, weights="equal", method="saw")
    assert "blinding" not in plain.manifest


def test_unblind_rejects_other_types():
    _, seal = blind(_wide_scores(), seed=0)
    with pytest.raises(TypeError):
        unblind(42, seal)


def test_seal_roundtrips_through_json(tmp_path):
    _, seal = blind(_wide_scores(), seed=4)
    path = tmp_path / "seal.json"
    write_seal(seal, str(path))
    loaded = read_seal(str(path))
    assert loaded.mapping == seal.mapping
    assert loaded.seed == seal.seed
    assert loaded.fingerprint == seal.fingerprint


def test_fingerprint_is_stable_json():
    _, seal = blind(_wide_scores(), seed=9)
    # the fingerprint is a hash of the canonical seed-and-mapping JSON.
    rebuilt = Seal(mapping=dict(seal.mapping), seed=seal.seed)
    assert rebuilt.fingerprint == seal.fingerprint


def test_long_tensor_blinds_first_axis():
    values = np.arange(2 * 2 * 2, dtype=float).reshape(2, 2, 2)
    scores = Scores(
        values=values,
        tool_names=("a", "b"),
        metric_ids=("ari", "runtime"),
        dataset_names=("d0", "d1"),
        layout="long",
    )
    blinded, seal = blind(scores, seed=0)
    assert blinded.values.shape == values.shape
    restored = unblind(blinded, seal)
    a_pos = restored.tool_names.index("a")
    assert np.array_equal(restored.values[a_pos], values[0])
