"""Weight vectors for MCDA aggregation."""

from __future__ import annotations

import numpy as np


def equal_weights(n_metrics: int) -> np.ndarray:
    """Return a vector of ``n_metrics`` equal weights that sum to 1."""
    if n_metrics < 1:
        raise ValueError(f"n_metrics must be at least 1; got {n_metrics}")
    return np.full(n_metrics, 1.0 / n_metrics)
