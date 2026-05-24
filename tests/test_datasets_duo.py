"""Tests for the bundled Duo 2018 clustering benchmark loader.

These checks pin the shape, names, missing-value counts, and coverage
helpers of ``beam.datasets.load_duo2018``, and confirm that the carded
metrics resolve through ``beam.cards.properties_for`` with a polarity that
matches the metric cards. Everything is deterministic: the data is read
from the bundled CSV with no randomness.
"""

from __future__ import annotations

import numpy as np

from beam.cards import properties_for
from beam.datasets import load_duo2018

EXPECTED_METHODS = (
    "CIDR",
    "FlowSOM",
    "monocle",
    "PCAHC",
    "PCAKmeans",
    "pcaReduce",
    "RaceID2",
    "RtsneKmeans",
    "SAFE",
    "SC3",
    "SC3svm",
    "Seurat",
    "TSCAN",
    "ascend",
)

EXPECTED_DATASETS = (
    "Koh",
    "KohTCC",
    "Kumar",
    "KumarTCC",
    "SimKumar4easy",
    "SimKumar4hard",
    "SimKumar8hard",
    "Trapnell",
    "TrapnellTCC",
    "Zhengmix4eq",
    "Zhengmix4uneq",
    "Zhengmix8eq",
)

EXPECTED_NAN_COUNTS = {
    "ari": 5,
    "runtime": 5,
    "shannon_entropy_diff": 5,
    "nclust_deviation": 101,
}


def test_shape_is_14_by_12_by_4() -> None:
    duo = load_duo2018()
    assert duo.scores.shape == (14, 12, 4)
    assert duo.scores.dtype == np.float64


def test_method_and_dataset_names() -> None:
    duo = load_duo2018()
    assert duo.method_names == EXPECTED_METHODS
    assert duo.dataset_names == EXPECTED_DATASETS
    assert len(duo.method_names) == 14
    assert len(duo.dataset_names) == 12


def test_metric_ids_and_polarity() -> None:
    duo = load_duo2018()
    assert duo.metric_ids == ("ari", "runtime", "shannon_entropy_diff", "nclust_deviation")
    assert duo.polarity == (
        "higher_is_better",
        "lower_is_better",
        "lower_is_better",
        "lower_is_better",
    )


def test_nan_counts_match_source() -> None:
    duo = load_duo2018()
    for metric_pos, metric_id in enumerate(duo.metric_ids):
        n_nan = int(np.isnan(duo.scores[:, :, metric_pos]).sum())
        assert n_nan == EXPECTED_NAN_COUNTS[metric_id], metric_id


def test_carded_metrics_resolve_with_matching_polarity() -> None:
    carded = ["ari", "runtime", "shannon_entropy_diff"]
    props = properties_for(carded)
    duo = load_duo2018()
    card_polarity = {p.id: p.polarity for p in props}
    duo_polarity = dict(zip(duo.metric_ids, duo.polarity, strict=True))
    for metric_id in carded:
        assert card_polarity[metric_id] == duo_polarity[metric_id], metric_id


def test_tensor_selects_in_requested_order() -> None:
    duo = load_duo2018()
    selected = duo.tensor(metric_ids=("runtime", "ari"))
    assert selected.shape == (14, 12, 2)
    # The reordered slices must equal the original metric planes.
    assert np.allclose(selected[:, :, 0], duo.scores[:, :, 1], equal_nan=True)
    assert np.allclose(selected[:, :, 1], duo.scores[:, :, 0], equal_nan=True)


def test_tensor_returns_a_copy() -> None:
    duo = load_duo2018()
    full = duo.tensor()
    full[0, 0, 0] = -999.0
    assert duo.scores[0, 0, 0] != -999.0


def test_feasible_mask_on_known_cells() -> None:
    duo = load_duo2018()
    # FlowSOM (row 1) has every nclust_deviation cell missing in Duo 2018.
    nclust_feasible = duo.feasible("nclust_deviation")
    flowsom_row = duo.method_names.index("FlowSOM")
    assert not nclust_feasible[flowsom_row].any()
    # ARI is observed for CIDR on Koh (row 0, col 0).
    ari_feasible = duo.feasible("ari")
    assert ari_feasible[0, 0]


def test_complete_helpers_on_carded_subset() -> None:
    duo = load_duo2018()
    carded = ("ari", "runtime", "shannon_entropy_diff")
    methods_ok = duo.complete_methods(carded)
    datasets_ok = duo.complete_datasets(carded)
    assert methods_ok.shape == (14,)
    assert datasets_ok.shape == (12,)
    # Including the sparse cluster-count metric can only reduce coverage.
    methods_all = duo.complete_methods()
    assert methods_all.sum() <= methods_ok.sum()


def test_unknown_metric_raises_keyerror() -> None:
    duo = load_duo2018()
    try:
        duo.feasible("does_not_exist")
    except KeyError:
        pass
    else:
        raise AssertionError("expected KeyError for an unknown metric id")
