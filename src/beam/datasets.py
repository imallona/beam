"""Loaders for benchmark data sets bundled with beam.

The headline data set is the single-cell RNA-seq clustering benchmark of
Duo, Robinson and Soneson (2018). ``load_duo2018`` reads the bundled CSV
into a frozen ``Duo2018`` dataclass that holds a method by data set by
metric tensor, with missing cells exposed as ``numpy.nan``. The loader
does not impute or drop anything: it surfaces the gaps so the caller, the
MCDA pipeline or the heterogeneity module, can decide how to handle
partial method-data-set coverage.

The data and metric mapping are documented in
``src/beam/data/README.md``. The four metrics map to the bundled metric
registry as ARI to ``ari``, elapsed to ``runtime``, s.norm.vs.true to
``shannon_entropy_diff``, and nclust.vs.true to ``nclust_deviation``.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from importlib import resources
from typing import Final

import numpy as np

_CSV_PACKAGE: Final = "beam.data"
_CSV_NAME: Final = "DuoSCClustering2018.csv"

# Source column prefix per beam metric id, in the canonical metric order.
_METRIC_PREFIX: Final[dict[str, str]] = {
    "ari": "ARI",
    "runtime": "elapsed",
    "shannon_entropy_diff": "s.norm.vs.true",
    "nclust_deviation": "nclust.vs.true",
}

_METRIC_IDS: Final[tuple[str, ...]] = (
    "ari",
    "runtime",
    "shannon_entropy_diff",
    "nclust_deviation",
)

# Polarity per metric, in the same order as _METRIC_IDS. ARI is
# higher_is_better; the other three are lower_is_better (less runtime,
# entropy closer to the truth, fewer clusters away from the truth).
_POLARITY: Final[tuple[str, ...]] = (
    "higher_is_better",
    "lower_is_better",
    "lower_is_better",
    "lower_is_better",
)


@dataclass(frozen=True)
class Duo2018:
    """The Duo 2018 clustering benchmark as a method by data set by metric tensor.

    The tensor is built once at load time and exposed read only. Missing
    cells are ``numpy.nan``. No imputation or row or column dropping
    happens here; the helpers report coverage so callers can choose a
    policy.

    Attributes
    ----------
    method_names
        The 14 clustering methods, in CSV row order.
    dataset_names
        The 12 data sets, in CSV column order.
    metric_ids
        The four beam metric ids, in the order they index the last tensor
        axis: ari, runtime, shannon_entropy_diff, nclust_deviation.
    polarity
        One of "higher_is_better" or "lower_is_better" per metric, aligned
        with ``metric_ids``.
    scores
        Float array of shape (14, 12, 4) holding the scores, with NaN in
        the cells that were the literal string NA in the source.
    """

    method_names: tuple[str, ...]
    dataset_names: tuple[str, ...]
    metric_ids: tuple[str, ...]
    polarity: tuple[str, ...]
    scores: np.ndarray

    def tensor(self, metric_ids: tuple[str, ...] | None = None) -> np.ndarray:
        """Return the (n_methods, n_datasets, len(metric_ids)) sub-tensor.

        Parameters
        ----------
        metric_ids
            Metric ids to select, in the requested order. ``None`` returns
            all metrics in the canonical order.

        Returns
        -------
        numpy.ndarray
            A copy of the requested metric slices stacked along the last
            axis, preserving the requested order.

        Raises
        ------
        KeyError
            If a requested metric id is not present in this benchmark.
        """
        if metric_ids is None:
            return self.scores.copy()
        indices = [self._metric_index(mid) for mid in metric_ids]
        return self.scores[:, :, indices].copy()

    def feasible(self, metric_id: str) -> np.ndarray:
        """Boolean (n_methods, n_datasets) mask, True where the metric is observed.

        Parameters
        ----------
        metric_id
            The beam metric id to inspect.

        Returns
        -------
        numpy.ndarray
            Boolean array, True where the cell for that metric is not NaN.
        """
        return ~np.isnan(self.scores[:, :, self._metric_index(metric_id)])

    def complete_methods(self, metric_ids: tuple[str, ...] | None = None) -> np.ndarray:
        """Boolean (n_methods,) mask of methods with no NaN across the metric subset.

        A method is complete when it is observed on every data set for every
        metric in the subset.

        Parameters
        ----------
        metric_ids
            Metric ids to require coverage for. ``None`` requires coverage
            across all four metrics.

        Returns
        -------
        numpy.ndarray
            Boolean array over methods, True where the method has no NaN in
            the selected metrics over all data sets.
        """
        sub = self.tensor(metric_ids)
        return ~np.isnan(sub).any(axis=(1, 2))

    def complete_datasets(self, metric_ids: tuple[str, ...] | None = None) -> np.ndarray:
        """Boolean (n_datasets,) mask of data sets with no NaN across the metric subset.

        A data set is complete when every method is observed on it for every
        metric in the subset.

        Parameters
        ----------
        metric_ids
            Metric ids to require coverage for. ``None`` requires coverage
            across all four metrics.

        Returns
        -------
        numpy.ndarray
            Boolean array over data sets, True where the data set has no NaN
            in the selected metrics over all methods.
        """
        sub = self.tensor(metric_ids)
        return ~np.isnan(sub).any(axis=(0, 2))

    def _metric_index(self, metric_id: str) -> int:
        try:
            return self.metric_ids.index(metric_id)
        except ValueError as exc:
            raise KeyError(
                f"unknown metric id {metric_id!r}; available: {self.metric_ids}"
            ) from exc


def _parse_cell(value: str) -> float:
    """Parse one CSV cell, mapping the literal string NA to NaN."""
    if value == "NA":
        return np.nan
    return float(value)


def load_duo2018() -> Duo2018:
    """Load the bundled Duo 2018 clustering benchmark.

    Reads ``DuoSCClustering2018.csv`` from the installed package via
    ``importlib.resources`` so it works whether beam runs from a source
    checkout or an installed wheel. The wide CSV has one method per row and
    one column per metric and data set combination, named
    ``<prefix>_<dataset>``. The function reshapes it into a
    (n_methods, n_datasets, n_metrics) tensor with NaN where the source
    held the literal string NA.

    Returns
    -------
    Duo2018
        Frozen dataclass with method names, data set names, metric ids,
        per-metric polarity, and the (14, 12, 4) score tensor.

    Notes
    -----
    No imputation or dropping happens here. The missing cells (5 each in
    ari, runtime and shannon_entropy_diff, 101 in nclust_deviation) are
    exposed as NaN. Use the coverage helpers to decide on a policy.
    """
    csv_text = resources.files(_CSV_PACKAGE).joinpath(_CSV_NAME).read_text(encoding="utf-8")
    rows = list(csv.reader(csv_text.splitlines()))
    header = rows[0]
    data_rows = rows[1:]

    method_names = tuple(row[0] for row in data_rows)
    column_index = {name: i for i, name in enumerate(header)}

    # Data set order is taken from the ARI columns and reused for every
    # metric, since all four metrics span the same data sets.
    ari_prefix = _METRIC_PREFIX["ari"]
    dataset_names = tuple(
        name.split("_", 1)[1] for name in header if name.startswith(f"{ari_prefix}_")
    )

    n_methods = len(method_names)
    n_datasets = len(dataset_names)
    n_metrics = len(_METRIC_IDS)
    scores = np.full((n_methods, n_datasets, n_metrics), np.nan, dtype=float)

    for metric_pos, metric_id in enumerate(_METRIC_IDS):
        prefix = _METRIC_PREFIX[metric_id]
        for dataset_pos, dataset in enumerate(dataset_names):
            col = column_index[f"{prefix}_{dataset}"]
            for method_pos, row in enumerate(data_rows):
                scores[method_pos, dataset_pos, metric_pos] = _parse_cell(row[col])

    return Duo2018(
        method_names=method_names,
        dataset_names=dataset_names,
        metric_ids=_METRIC_IDS,
        polarity=_POLARITY,
        scores=scores,
    )
