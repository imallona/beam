"""Adapters that read benchmark output into a tool by metric score table.

``load_scores`` is the canonical loader: standard library plus numpy, no
pandas, returning a registry-validated ``Scores`` container. ``read_csv`` is
an optional pandas convenience under the ``[io]`` extra.
"""

from .csv import read_csv
from .scores import Scores, UnknownMetricError, load_scores

__all__ = ["Scores", "UnknownMetricError", "load_scores", "read_csv"]
