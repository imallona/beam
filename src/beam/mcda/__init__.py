"""beam.mcda: multi-criteria decision analysis on a tool by metric matrix."""

from .aggregate import rank, weighted_sum
from .facade import Result, run
from .normalize import min_max_normalize
from .topsis import topsis
from .weights import entropy_weights, equal_weights

__all__ = [
    "Result",
    "entropy_weights",
    "equal_weights",
    "min_max_normalize",
    "rank",
    "run",
    "topsis",
    "weighted_sum",
]
