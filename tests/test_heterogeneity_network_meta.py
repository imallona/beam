"""Tests for the network meta-analysis over benchmark results.

The fitting tests need R with netmeta and are skipped when that toolchain is
absent. The input-validation tests run everywhere.
"""

from __future__ import annotations

import numpy as np
import pytest

from beam.datasets import load_integration_benchmarks
from beam.heterogeneity import (
    NetworkMetaReport,
    netmeta_available,
    network_meta_analysis,
)

HAVE_NETMETA = netmeta_available()
needs_netmeta = pytest.mark.skipif(not HAVE_NETMETA, reason="Rscript with netmeta not available")


def test_netmeta_available_returns_bool():
    assert isinstance(netmeta_available(), bool)


def test_length_mismatch_rejected():
    with pytest.raises(ValueError, match="same length"):
        network_meta_analysis(["a", "b"], ["s1", "s1"], [1.0, 2.0], [0.1, 0.1], [3])


def test_too_few_treatments_rejected():
    with pytest.raises(ValueError, match="two treatments"):
        network_meta_analysis(["a", "a"], ["s1", "s2"], [1.0, 2.0], [0.1, 0.1], [3, 3])


def test_too_few_studies_rejected():
    # Two treatments but only one study carries two arms; the other is a singleton.
    with pytest.raises(ValueError, match="two studies"):
        network_meta_analysis(
            ["a", "b", "a"],
            ["s1", "s1", "s2"],
            [1.0, 2.0, 1.5],
            [0.1, 0.1, 0.1],
            [3, 3, 3],
        )


def test_unknown_reference_rejected():
    with pytest.raises(ValueError, match="reference"):
        network_meta_analysis(
            ["a", "b", "a", "b"],
            ["s1", "s1", "s2", "s2"],
            [1.0, 2.0, 1.0, 2.0],
            [0.2, 0.2, 0.2, 0.2],
            [3, 3, 3, 3],
            reference="zzz",
        )


@needs_netmeta
def test_recovers_a_clear_ranking():
    # Three treatments over four studies, with a built-in order a < b < c on the
    # mean rank (a is best). The network meta-analysis should rank a first.
    treatments, studies, means, sds, ns = [], [], [], [], []
    for s in range(4):
        for t, base in (("a", 1.0), ("b", 2.0), ("c", 3.0)):
            treatments.append(t)
            studies.append(f"study{s}")
            means.append(base + 0.1 * s)
            sds.append(0.3)
            ns.append(4)
    rep = network_meta_analysis(treatments, studies, means, sds, ns)
    assert isinstance(rep, NetworkMetaReport)
    assert rep.top_treatment() == "a"
    assert rep.ranking() == ["a", "b", "c"]
    # P-scores are a probability-like quantity in the unit interval.
    assert np.all(rep.pscore >= 0) and np.all(rep.pscore <= 1)


@needs_netmeta
def test_integration_benchmarks_network_ranking():
    ib = load_integration_benchmarks()
    treatments, studies, means, sds, ns = ib.network_arms()
    rep = network_meta_analysis(treatments, studies, means, sds, ns)
    assert rep.n_treatments == 5
    assert rep.n_studies >= 2
    # With BatchBench added as the fifth source, harmony no longer leads on its
    # own: harmony and liger are the top two by P-score, and combat trails. The
    # fifth source weights biology equally and so demotes harmony.
    ranking = rep.ranking()
    assert set(ranking[:2]) == {"harmony", "liger"}
    assert ranking[-1] == "combat"
    # The reference arm sits at effect 0 by construction.
    ref_index = rep.treatments.index(rep.reference)
    assert rep.effect[ref_index] == 0.0
    # The benchmarks disagree, so heterogeneity is high.
    assert rep.i2 > 0.5
