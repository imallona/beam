"""End-to-end test: pull metric metadata from the registry, normalize, aggregate, rank."""

import numpy as np

from beam.cards import Registry
from beam.mcda import equal_weights, min_max_normalize, rank, weighted_sum


def test_end_to_end_with_registry():
    reg = Registry()
    metric_ids = ["ari", "runtime"]
    polarity = [reg.get(mid).polarity for mid in metric_ids]

    scores = np.array(
        [
            [0.85, 120.0],
            [0.70, 30.0],
            [0.60, 90.0],
        ]
    )

    normalized = min_max_normalize(scores, polarity)
    weights = equal_weights(len(metric_ids))
    composite = weighted_sum(normalized, weights)
    ranks = rank(composite)

    assert composite.shape == (3,)
    assert ranks.shape == (3,)
    assert min(ranks) == 1
    assert max(ranks) == 3
    assert (normalized >= 0).all() and (normalized <= 1).all()
