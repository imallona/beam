"""beam.mcda: multi-criteria decision analysis on a tool by metric matrix."""

from .aggregate import rank, weighted_sum
from .normalize import min_max_normalize
from .weights import equal_weights

__all__ = ["equal_weights", "min_max_normalize", "rank", "weighted_sum"]
