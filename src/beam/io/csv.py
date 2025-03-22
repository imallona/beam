"""Read a tool by metric CSV file into a DataFrame.

This is a stub. Richer adapters (omnibenchmark output, FunkyHeatmap matrix,
parquet) will follow in Phase 2.
"""

from __future__ import annotations

from pathlib import Path


def read_csv(path: str | Path):
    """Return a pandas DataFrame indexed by tool name, with one column per metric.

    pandas is an optional dependency; install with `pip install .[io]`.
    """
    import pandas as pd

    return pd.read_csv(path, index_col=0)
