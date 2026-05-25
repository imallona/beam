"""Read a tool by metric CSV file into a pandas DataFrame.

This is the optional pandas convenience under the ``[io]`` extra, for users
who already work in pandas. The canonical loader is ``beam.load_scores``,
which uses only the standard library and numpy and validates the metric ids
against the registry.
"""

from __future__ import annotations

from pathlib import Path


def read_csv(path: str | Path):
    """Return a pandas DataFrame indexed by tool name, with one column per metric.

    pandas is an optional dependency; install with ``pip install .[io]``. For
    the registry-validated container used by the pipeline, use
    ``beam.load_scores`` instead.
    """
    import pandas as pd

    return pd.read_csv(path, index_col=0)
