"""Tests for the bundled OpenProblems task loaders."""

from __future__ import annotations

import numpy as np
import pytest

from beam.cards import properties_for
from beam.datasets import (
    OpenProblems,
    load_openproblems,
    load_openproblems_svg_features,
)


def test_unknown_task_rejected():
    with pytest.raises(ValueError, match="unknown OpenProblems task"):
        load_openproblems("not_a_task")


def test_batch_integration_shape():
    op = load_openproblems("batch_integration")
    assert isinstance(op, OpenProblems)
    assert op.task == "batch_integration"
    assert len(op.method_names) == 19
    assert len(op.dataset_names) == 6
    assert len(op.metric_ids) == 13
    assert op.scores.shape == (19, 6, 13)
    # The platform reports every metric higher is better.
    assert set(op.polarity) == {"higher_is_better"}
    # Controls and baselines were dropped at vendoring time.
    assert not any("shuffle" in m or "no_integration" in m for m in op.method_names)
    # The scIB metric set, with some missing cells preserved as NaN.
    assert {"ari", "nmi", "asw_batch", "ilisi", "kbet"} <= set(op.metric_ids)
    assert np.isnan(op.scores).any()


def test_spatially_variable_genes_shape():
    op = load_openproblems("spatially_variable_genes")
    assert len(op.method_names) == 14
    assert len(op.dataset_names) == 50
    assert op.metric_ids == ("correlation",)
    assert op.scores.shape == (14, 50, 1)
    assert "random_ranking" not in op.method_names


def test_metrics_resolve_to_registry_cards():
    for task in ("batch_integration", "spatially_variable_genes"):
        op = load_openproblems(task)
        # properties_for resolves every id against the registry, raising if one
        # is missing a card, so this asserts all metrics are carded.
        props = properties_for(op.metric_ids)
        assert len(props) == len(op.metric_ids)


def test_tensor_metric_selection():
    op = load_openproblems("batch_integration")
    sub = op.tensor(("ari", "nmi"))
    assert sub.shape == (19, 6, 2)
    np.testing.assert_array_equal(sub[:, :, 0], op.scores[:, :, op.metric_ids.index("ari")])
    with pytest.raises(KeyError):
        op.tensor(("not_a_metric",))


def test_svg_features():
    feats = load_openproblems_svg_features()
    assert len(feats.dataset_names) == 50
    assert set(feats.categorical) == {"technology", "organism", "condition"}
    assert feats.numeric == {}
    # Features parse out of the dataset id; visium is the most common technology.
    technologies = set(feats.categorical["technology"])
    assert {"visium", "merfish", "slideseqv2", "stereoseq"} <= technologies
    assert set(feats.categorical["organism"]) <= {"human", "mouse", "drosophila", "other"}

    op = load_openproblems("spatially_variable_genes")
    # The features align to the loader's dataset order without dropping any.
    _, categorical = feats.aligned_to(op.dataset_names)
    assert len(categorical["technology"]) == len(op.dataset_names)
