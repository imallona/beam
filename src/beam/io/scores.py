"""Read a benchmark score CSV into a typed, registry-validated container.

beam consumes a tool by metric matrix, or a tool by dataset by metric
tensor. ``load_scores`` reads either from CSV using only the standard
library and numpy, so the core install needs no pandas. The pandas-based
reader in ``beam.io.csv`` stays as an optional convenience under the
``[io]`` extra.

Two CSV layouts are supported.

Wide, one dataset. The first column holds the tool name; every other
column header is a metric id that must resolve to a card in the registry::

    tool,ari,runtime
    seurat,0.81,42.0
    sc3,0.74,310.5

Long, a tool by dataset by metric tensor. Four columns named tool,
dataset, metric and score, in any order::

    tool,dataset,metric,score
    seurat,koh,ari,0.81
    seurat,koh,runtime,42.0
    sc3,koh,ari,0.74

Missing cells are exposed as ``numpy.nan``: the literal string ``NA`` or an
empty field in the wide layout, and any tool-dataset-metric combination
absent from the long layout. The loader does not impute or drop; it surfaces
the gaps so the pipeline can decide on a policy.
"""

from __future__ import annotations

import csv
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from ..cards import Registry

_LONG_COLUMNS = ("tool", "dataset", "metric", "score")


class UnknownMetricError(ValueError):
    """Raised when a score file names a metric id absent from the registry."""


@dataclass(frozen=True)
class Scores:
    """A benchmark score table or tensor with its tool and metric labels.

    Holds either a wide tool by metric matrix (``layout == "wide"``,
    ``values`` is 2D and ``dataset_names`` is ``None``) or a long tool by
    dataset by metric tensor (``layout == "long"``, ``values`` is 3D). The
    metric ids have all been checked against the registry at load time.

    Attributes
    ----------
    values
        Float array. Shape ``(n_tools, n_metrics)`` when wide, or
        ``(n_tools, n_datasets, n_metrics)`` when long. Missing cells are
        ``numpy.nan``.
    tool_names
        Tool names, in the order they index the first axis.
    metric_ids
        Metric ids, in the order they index the last axis. Every id
        resolves to a metric card.
    dataset_names
        Dataset names indexing the middle axis when long, otherwise
        ``None``.
    layout
        ``"wide"`` or ``"long"``.
    source_path
        The file the scores were read from, or ``None`` when constructed
        directly from arrays. Recorded in the run manifest.
    """

    values: np.ndarray
    tool_names: tuple[str, ...]
    metric_ids: tuple[str, ...]
    dataset_names: tuple[str, ...] | None
    layout: str
    source_path: str | None = None

    @property
    def is_tensor(self) -> bool:
        """True for the long layout, where ``values`` is a 3D tensor."""
        return self.layout == "long"

    @property
    def n_tools(self) -> int:
        return len(self.tool_names)

    @property
    def n_metrics(self) -> int:
        return len(self.metric_ids)

    @property
    def n_datasets(self) -> int:
        """Number of datasets, or 1 for the single-dataset wide layout."""
        return 0 if self.dataset_names is None else len(self.dataset_names)


def load_scores(
    path: str | Path,
    layout: str = "auto",
    registry: Registry | None = None,
) -> Scores:
    """Read a benchmark score CSV and validate its metric ids against the registry.

    Parameters
    ----------
    path
        Path to the CSV file.
    layout
        ``"auto"`` (default) detects the layout from the header: a header
        whose columns are exactly tool, dataset, metric and score (in any
        order) is read as long, anything else as wide. Pass ``"wide"`` or
        ``"long"`` to force a layout.
    registry
        Optional ``Registry`` instance. Defaults to a fresh registry over
        the bundled metrics.

    Returns
    -------
    Scores

    Raises
    ------
    UnknownMetricError
        If any metric id in the file does not resolve to a metric card.
    ValueError
        If the file is empty, a forced layout does not match the header, a
        long file is missing a required column, or a long file carries a
        duplicate tool-dataset-metric row.
    """
    path = Path(path)
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    rows = [row for row in rows if row and any(cell.strip() for cell in row)]
    if not rows:
        raise ValueError(f"{path} is empty")

    header = [cell.strip() for cell in rows[0]]
    resolved = _resolve_layout(layout, header, path)
    reg = registry if registry is not None else Registry()

    scores = _read_long(rows, header, reg, path) if resolved == "long" else _read_wide(
        rows, header, reg, path
    )
    return replace(scores, source_path=str(path))


def _resolve_layout(layout: str, header: Sequence[str], path: Path) -> str:
    is_long_header = {h.lower() for h in header} == set(_LONG_COLUMNS)
    if layout == "auto":
        return "long" if is_long_header else "wide"
    if layout == "long" and not is_long_header:
        raise ValueError(
            f"{path} forced as long but its header is {list(header)}; "
            f"expected columns {list(_LONG_COLUMNS)}"
        )
    if layout not in ("wide", "long"):
        raise ValueError(f"unknown layout {layout!r}; use 'auto', 'wide' or 'long'")
    return layout


def _check_metrics(metric_ids: Sequence[str], registry: Registry, path: Path) -> None:
    known = set(registry.list_ids())
    unknown = [mid for mid in metric_ids if mid not in known]
    if unknown:
        raise UnknownMetricError(
            f"{path} names metric ids with no card: {unknown}; "
            f"registered ids are {sorted(known)}"
        )


def _parse_cell(value: str) -> float:
    cell = value.strip()
    if cell == "" or cell.upper() == "NA":
        return np.nan
    return float(cell)


def _read_wide(
    rows: list[list[str]],
    header: list[str],
    registry: Registry,
    path: Path,
) -> Scores:
    metric_ids = tuple(header[1:])
    if not metric_ids:
        raise ValueError(
            f"{path} wide layout needs at least one metric column after the tool column"
        )
    _check_metrics(metric_ids, registry, path)

    tool_names: list[str] = []
    values: list[list[float]] = []
    for line_no, row in enumerate(rows[1:], start=2):
        if len(row) != len(header):
            raise ValueError(
                f"{path} line {line_no} has {len(row)} fields; header has {len(header)}"
            )
        tool_names.append(row[0].strip())
        values.append([_parse_cell(cell) for cell in row[1:]])

    return Scores(
        values=np.asarray(values, dtype=float),
        tool_names=tuple(tool_names),
        metric_ids=metric_ids,
        dataset_names=None,
        layout="wide",
    )


def _read_long(
    rows: list[list[str]],
    header: list[str],
    registry: Registry,
    path: Path,
) -> Scores:
    col = {name.lower(): i for i, name in enumerate(header)}
    tool_i, dataset_i, metric_i, score_i = (
        col["tool"],
        col["dataset"],
        col["metric"],
        col["score"],
    )

    tool_order: list[str] = []
    dataset_order: list[str] = []
    metric_order: list[str] = []
    cells: dict[tuple[str, str, str], float] = {}

    for line_no, row in enumerate(rows[1:], start=2):
        if len(row) != len(header):
            raise ValueError(
                f"{path} line {line_no} has {len(row)} fields; header has {len(header)}"
            )
        tool = row[tool_i].strip()
        dataset = row[dataset_i].strip()
        metric = row[metric_i].strip()
        key = (tool, dataset, metric)
        if key in cells:
            raise ValueError(f"{path} line {line_no} duplicates tool-dataset-metric row {key}")
        cells[key] = _parse_cell(row[score_i])
        _append_unique(tool_order, tool)
        _append_unique(dataset_order, dataset)
        _append_unique(metric_order, metric)

    _check_metrics(metric_order, registry, path)

    values = np.full((len(tool_order), len(dataset_order), len(metric_order)), np.nan, dtype=float)
    tool_pos = {name: i for i, name in enumerate(tool_order)}
    dataset_pos = {name: i for i, name in enumerate(dataset_order)}
    metric_pos = {name: i for i, name in enumerate(metric_order)}
    for (tool, dataset, metric), score in cells.items():
        values[tool_pos[tool], dataset_pos[dataset], metric_pos[metric]] = score

    return Scores(
        values=values,
        tool_names=tuple(tool_order),
        metric_ids=tuple(metric_order),
        dataset_names=tuple(dataset_order),
        layout="long",
    )


def _append_unique(order: list[str], name: str) -> None:
    if name not in order:
        order.append(name)
