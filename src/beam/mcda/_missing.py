"""Refuse a tool by metric matrix that carries missing cells.

beam does not impute missing benchmark scores and does not pool a single
ranking across tools measured on different metric subsets. A missing cell is a
fact about coverage, not a value to fill in, so every step that consumes a tool
by metric matrix (normalization, weighting, the five aggregations, the
critical-difference test, and the ``run`` and ``beam.rank`` entry points) treats
a NaN as a hard error.

The one place partial coverage is handled, without imputation, is the
dataset-axis available-case summary in ``beam.mcda.reduce_tensor``: a tool is
summarized over the datasets where it was observed, and a tool with no observed
dataset for a metric is refused there. After that summary the matrix is
complete, so the rest of the pipeline never sees a missing cell on a valid path.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

_MAX_NAMED_CELLS = 5


class IncompleteMatrixError(ValueError):
    """Raised when an MCDA step is given a matrix with missing cells.

    A subclass of ``ValueError``. beam does not impute a missing score and does not
    rank tools measured on different metric subsets, so a NaN in the tool by
    metric matrix stops the pipeline. Summarize a tool over the datasets where
    it was observed with ``beam.mcda.reduce_tensor``, analyze the feasible
    subset on its own, or use the heterogeneity module for partial coverage.
    """


def require_complete(
    matrix: np.ndarray,
    *,
    where: str,
    metric_ids: Sequence[str] | None = None,
    tool_names: Sequence[str] | None = None,
) -> None:
    """Raise ``IncompleteMatrixError`` if ``matrix`` holds any NaN.

    Names a few of the offending cells so the message is actionable. Accepts a
    2D tool by metric matrix or a 1D per-tool vector (a composite score), and
    labels rows with ``tool_names`` and columns with ``metric_ids`` when given.

    Parameters
    ----------
    matrix
        The array to check. Coerced to float.
    where
        Short label for the step doing the check, used in the message, for
        example ``"topsis"`` or ``"normalize"``.
    metric_ids
        Optional column labels, used only in the message.
    tool_names
        Optional row labels, used only in the message.
    """
    matrix = np.asarray(matrix, dtype=float)
    missing = np.isnan(matrix)
    if not missing.any():
        return

    count = int(missing.sum())
    cells = _name_missing_cells(missing, metric_ids, tool_names)
    raise IncompleteMatrixError(
        f"{where}: the tool by metric matrix has {count} missing "
        f"{'cell' if count == 1 else 'cells'} ({cells}). beam does not pick a "
        "missing-data policy for you. Choose one on the ranking call: "
        "missing='available' (available-case, SAW only), missing='worst' "
        "(treat a non-run as the worst score), or missing='impute' (mean "
        "imputation, discouraged). For the dataset axis, summarize over the "
        "datasets where each tool ran with beam.mcda.reduce_tensor, or analyze "
        "the feasible subset on its own."
    )


def _name_missing_cells(
    missing: np.ndarray,
    metric_ids: Sequence[str] | None,
    tool_names: Sequence[str] | None,
) -> str:
    """Format up to ``_MAX_NAMED_CELLS`` missing cells as a readable list."""
    if missing.ndim == 1:
        rows = np.nonzero(missing)[0]
        named = [_tool_label(int(i), tool_names) for i in rows[:_MAX_NAMED_CELLS]]
    else:
        rows, cols = np.nonzero(missing)
        named = [
            f"{_tool_label(int(i), tool_names)} on {_metric_label(int(j), metric_ids)}"
            for i, j in zip(rows[:_MAX_NAMED_CELLS], cols[:_MAX_NAMED_CELLS], strict=True)
        ]
    extra = len(np.nonzero(missing)[0]) - len(named)
    listing = ", ".join(named)
    return f"{listing}, and {extra} more" if extra > 0 else listing


def _tool_label(i: int, tool_names: Sequence[str] | None) -> str:
    if tool_names is not None and i < len(tool_names):
        return f"tool {tool_names[i]!r}"
    return f"tool index {i}"


def _metric_label(j: int, metric_ids: Sequence[str] | None) -> str:
    if metric_ids is not None and j < len(metric_ids):
        return f"metric {metric_ids[j]!r}"
    return f"metric index {j}"
