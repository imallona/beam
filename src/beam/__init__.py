"""beam: Benchmark Evaluation And Metrics.

This package is the Python canonical implementation of beam. See the ADRs
(docs/adr/) for the decisions behind its design.
"""

from importlib import metadata

from .api import RunResult, rank
from .io import Scores, load_scores
from .mcda import IncompleteMatrixError
from .reporting import write_report as report

try:
    __version__ = metadata.version("beam")
except metadata.PackageNotFoundError:  # pragma: no cover - source tree without install
    __version__ = "0.0.0+unknown"

__all__ = [
    "IncompleteMatrixError",
    "RunResult",
    "Scores",
    "__version__",
    "load_scores",
    "rank",
    "report",
]
