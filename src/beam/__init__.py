"""beam: Benchmark Evaluation And Metrics.

This package is the Python canonical implementation of beam.
"""

from importlib import metadata

from . import plot
from .api import RunResult, rank
from .blinding import Seal, blind, read_seal, unblind, write_seal
from .io import Scores, load_scores
from .mcda import IncompleteMatrixError
from .reporting import funky_heatmap, funky_heatmap_from_run
from .reporting import write_report as report

try:
    __version__ = metadata.version("beam")
except metadata.PackageNotFoundError:  # pragma: no cover - source tree without install
    __version__ = "0.0.0+unknown"

__all__ = [
    "IncompleteMatrixError",
    "RunResult",
    "Scores",
    "Seal",
    "__version__",
    "blind",
    "funky_heatmap",
    "funky_heatmap_from_run",
    "load_scores",
    "plot",
    "rank",
    "read_seal",
    "report",
    "unblind",
    "write_seal",
]
