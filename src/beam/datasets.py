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

The second data set is the M4 forecasting competition (Makridakis,
Spiliotis and Assimakopoulos 2020). ``load_m4`` reads a small derived table
into an ``M4Forecasting`` dataclass holding a method by frequency by metric
tensor. The frequency bands (yearly, quarterly, monthly, weekly, daily,
hourly) play the data set role, and the two metrics map to the registry as
``smape`` and ``mase``, both lower is better. The table was computed once
from the GPL-3 ``M4comp2018`` data; how it was generated, the source commit,
and the reduction script are documented in ``src/beam/data/README.md`` and
``src/beam/data/reduce_m4.R``.
"""

from __future__ import annotations

import csv
from collections.abc import Sequence
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


_M4_CSV_NAME: Final = "M4_2018_by_frequency.csv"

# Frequency bands in increasing sampling rate (decreasing typical horizon),
# the order the loader uses for the data set axis. The source CSV lists them
# alphabetically.
_M4_FREQUENCIES: Final[tuple[str, ...]] = (
    "Yearly",
    "Quarterly",
    "Monthly",
    "Weekly",
    "Daily",
    "Hourly",
)

_M4_METRIC_IDS: Final[tuple[str, ...]] = ("smape", "mase")

_M4_POLARITY: Final[tuple[str, ...]] = ("lower_is_better", "lower_is_better")


@dataclass(frozen=True)
class M4Forecasting:
    """The M4 competition results as a method by frequency by metric tensor.

    The tensor is dense (every top-25 method has a score on every frequency
    band for both metrics). The data set axis is the six M4 frequency bands.

    Attributes
    ----------
    method_names
        The 25 forecasting methods whose point forecasts the M4comp2018 data
        ships, in competition rank order (Smyl, the ES-RNN winner, first).
    frequency_names
        The six frequency bands, in the order they index the data set axis.
    metric_ids
        The beam metric ids, in last-axis order: ``smape`` then ``mase``.
    polarity
        ``"lower_is_better"`` for both metrics, aligned with ``metric_ids``.
    scores
        Float array of shape (25, 6, 2) holding the mean sMAPE and mean MASE
        per method per frequency band.
    n_series
        Int array of shape (6,) with the number of series in each frequency
        band, the weight behind each column.
    """

    method_names: tuple[str, ...]
    frequency_names: tuple[str, ...]
    metric_ids: tuple[str, ...]
    polarity: tuple[str, ...]
    scores: np.ndarray
    n_series: np.ndarray

    def tensor(self, metric_ids: tuple[str, ...] | None = None) -> np.ndarray:
        """Return the (n_methods, n_frequencies, len(metric_ids)) sub-tensor.

        Parameters
        ----------
        metric_ids
            Metric ids to select, in the requested order. ``None`` returns
            both metrics in the canonical order.

        Returns
        -------
        numpy.ndarray
            A copy of the requested metric slices stacked along the last axis.

        Raises
        ------
        KeyError
            If a requested metric id is not present.
        """
        if metric_ids is None:
            return self.scores.copy()
        indices = []
        for mid in metric_ids:
            try:
                indices.append(self.metric_ids.index(mid))
            except ValueError as exc:
                raise KeyError(f"unknown metric id {mid!r}; available: {self.metric_ids}") from exc
        return self.scores[:, :, indices].copy()


def load_m4() -> M4Forecasting:
    """Load the bundled M4 forecasting results table.

    Reads ``M4_2018_by_frequency.csv`` from the installed package via
    ``importlib.resources``. The long CSV has one row per method and frequency
    band with columns ``method, frequency, smape, mase, n_series``. The loader
    reshapes it into a (25, 6, 2) method by frequency by metric tensor, with
    methods kept in competition rank order and frequencies ordered from yearly
    to hourly.

    The table is a derived artefact, computed once from the GPL-3
    ``M4comp2018`` data (the top-25 methods' point forecasts and the realized
    values) by ``src/beam/data/reduce_m4.R``. See ``src/beam/data/README.md``
    for the provenance, the metric definitions, and the validation against the
    published competition figures.

    Returns
    -------
    M4Forecasting
        Frozen dataclass with method names, frequency names, the metric ids
        ``smape`` and ``mase``, per-metric polarity, the (25, 6, 2) score
        tensor, and the per-frequency series counts.
    """
    csv_text = resources.files(_CSV_PACKAGE).joinpath(_M4_CSV_NAME).read_text(encoding="utf-8")
    rows = list(csv.DictReader(csv_text.splitlines()))

    method_names: list[str] = []
    for row in rows:
        if row["method"] not in method_names:
            method_names.append(row["method"])

    freq_index = {name: i for i, name in enumerate(_M4_FREQUENCIES)}
    method_index = {name: i for i, name in enumerate(method_names)}
    n_methods = len(method_names)
    n_freqs = len(_M4_FREQUENCIES)

    scores = np.full((n_methods, n_freqs, len(_M4_METRIC_IDS)), np.nan, dtype=float)
    n_series = np.zeros(n_freqs, dtype=int)
    for row in rows:
        mi = method_index[row["method"]]
        fi = freq_index[row["frequency"]]
        scores[mi, fi, 0] = float(row["smape"])
        scores[mi, fi, 1] = float(row["mase"])
        n_series[fi] = int(row["n_series"])

    if np.isnan(scores).any():
        missing = int(np.isnan(scores).sum())
        raise ValueError(f"M4 table has {missing} unfilled cells; expected a dense tensor")

    return M4Forecasting(
        method_names=tuple(method_names),
        frequency_names=_M4_FREQUENCIES,
        metric_ids=_M4_METRIC_IDS,
        polarity=_M4_POLARITY,
        scores=scores,
        n_series=n_series,
    )


_FEATURES_CSV_NAME: Final = "DuoSCClustering2018_features.csv"

# Dataset descriptors split by type so the heterogeneity module can pass them
# as numeric covariates or factors to a Bradley-Terry tree. The numeric ones
# are continuous splitters; the categorical ones are factors.
_NUMERIC_FEATURES: Final[tuple[str, ...]] = ("n_cells", "n_clusters")
_CATEGORICAL_FEATURES: Final[tuple[str, ...]] = ("source_type", "family", "quantification")


@dataclass(frozen=True)
class Duo2018Features:
    """Dataset-level descriptors for the Duo 2018 benchmark.

    These are the candidate splitting variables for a Bradley-Terry tree
    (``beam.heterogeneity.bradley_terry_tree``): they describe each data set
    rather than any method, so a tree can ask which data set properties
    reverse the method ranking. The values are read from the bundled
    ``DuoSCClustering2018_features.csv``; their provenance (the published
    cell and subpopulation counts from the DuoClustering2018 package help
    files) is documented in ``src/beam/data/README.md``.

    Attributes
    ----------
    dataset_names
        Data set labels, in the CSV row order.
    numeric
        Map from feature name (``n_cells``, ``n_clusters``) to a tuple of
        floats aligned with ``dataset_names``.
    categorical
        Map from feature name (``source_type``, ``family``,
        ``quantification``) to a tuple of strings aligned with
        ``dataset_names``.
    """

    dataset_names: tuple[str, ...]
    numeric: dict[str, tuple[float, ...]]
    categorical: dict[str, tuple[str, ...]]

    def aligned_to(
        self, dataset_names: Sequence[str]
    ) -> tuple[dict[str, list[float]], dict[str, list[str]]]:
        """Reorder the features to match an external data set order.

        Parameters
        ----------
        dataset_names
            The data set order to align to, typically the data set axis of a
            score tensor.

        Returns
        -------
        tuple
            ``(numeric, categorical)``, each a dict from feature name to a
            list of values in the requested order.

        Raises
        ------
        KeyError
            If a requested data set has no feature row.
        """
        index = {name: i for i, name in enumerate(self.dataset_names)}
        try:
            order = [index[name] for name in dataset_names]
        except KeyError as exc:
            raise KeyError(f"no Duo 2018 features for data set {exc.args[0]!r}") from exc
        numeric = {k: [v[i] for i in order] for k, v in self.numeric.items()}
        categorical = {k: [v[i] for i in order] for k, v in self.categorical.items()}
        return numeric, categorical


def load_duo2018_features() -> Duo2018Features:
    """Load the bundled Duo 2018 dataset-level descriptors.

    Returns
    -------
    Duo2018Features
        The data set names and their numeric and categorical descriptors,
        read from ``DuoSCClustering2018_features.csv`` via
        ``importlib.resources``.
    """
    csv_text = (
        resources.files(_CSV_PACKAGE).joinpath(_FEATURES_CSV_NAME).read_text(encoding="utf-8")
    )
    rows = list(csv.DictReader(csv_text.splitlines()))
    dataset_names = tuple(row["dataset"] for row in rows)
    numeric = {feat: tuple(float(row[feat]) for row in rows) for feat in _NUMERIC_FEATURES}
    categorical = {feat: tuple(row[feat] for row in rows) for feat in _CATEGORICAL_FEATURES}
    return Duo2018Features(
        dataset_names=dataset_names,
        numeric=numeric,
        categorical=categorical,
    )


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


# OpenProblems in Single-Cell Analysis (openproblems.bio, Nature Biotechnology
# 2025). Each task publishes a method by dataset by metric result tensor as
# CC-BY JSON. beam ships only small derived long-format tables (method_id,
# dataset_id, metric_id, score), one per task, with the control or baseline
# methods dropped. Provenance, the pinned source commit, and the metric
# directions are in src/beam/data/README.md.
_OP_TASKS: Final[dict[str, str]] = {
    "batch_integration": "openproblems_batch_integration.csv",
    "spatially_variable_genes": "openproblems_svg.csv",
}
_OP_SVG_FEATURES_CSV: Final = "openproblems_svg_features.csv"
_OP_SVG_FEATURES: Final[tuple[str, ...]] = ("technology", "organism", "condition")


@dataclass(frozen=True)
class OpenProblems:
    """One OpenProblems task as a method by dataset by metric tensor.

    Built from a bundled derived table; missing cells are ``numpy.nan``.
    Every OpenProblems metric here is reported with higher is better (the
    platform's ``maximize`` flag is true for all of them), so ``polarity`` is
    uniform; the canonical per-metric semantics live in the registry cards.

    Attributes
    ----------
    task
        The OpenProblems task id, for example ``"batch_integration"``.
    method_names
        Method ids, sorted, controls and baselines already dropped.
    dataset_names
        Dataset ids, sorted.
    metric_ids
        Metric ids, sorted; each resolves to a beam registry card.
    polarity
        ``"higher_is_better"`` per metric, aligned with ``metric_ids``.
    scores
        Float array of shape ``(n_methods, n_datasets, n_metrics)`` with NaN
        in the cells the source reported as missing.
    """

    task: str
    method_names: tuple[str, ...]
    dataset_names: tuple[str, ...]
    metric_ids: tuple[str, ...]
    polarity: tuple[str, ...]
    scores: np.ndarray

    def tensor(self, metric_ids: tuple[str, ...] | None = None) -> np.ndarray:
        """Return the (n_methods, n_datasets, len(metric_ids)) sub-tensor.

        ``None`` returns every metric in the canonical (sorted) order.
        """
        if metric_ids is None:
            return self.scores.copy()
        try:
            indices = [self.metric_ids.index(mid) for mid in metric_ids]
        except ValueError as exc:
            raise KeyError(f"unknown metric id; available: {self.metric_ids}") from exc
        return self.scores[:, :, indices].copy()


def load_openproblems(task: str) -> OpenProblems:
    """Load a bundled OpenProblems task as a method by dataset by metric tensor.

    Parameters
    ----------
    task
        One of the bundled task ids: ``"batch_integration"`` (19 methods, 6
        datasets, 13 scIB metrics) or ``"spatially_variable_genes"`` (14
        methods, 50 datasets, one correlation metric).

    Returns
    -------
    OpenProblems

    Raises
    ------
    ValueError
        If ``task`` is not one of the bundled tasks.
    """
    if task not in _OP_TASKS:
        raise ValueError(f"unknown OpenProblems task {task!r}; bundled: {sorted(_OP_TASKS)}")
    csv_text = resources.files(_CSV_PACKAGE).joinpath(_OP_TASKS[task]).read_text(encoding="utf-8")
    rows = list(csv.DictReader(csv_text.splitlines()))
    method_names = tuple(sorted({r["method_id"] for r in rows}))
    dataset_names = tuple(sorted({r["dataset_id"] for r in rows}))
    metric_ids = tuple(sorted({r["metric_id"] for r in rows}))
    mi = {m: i for i, m in enumerate(method_names)}
    di = {d: i for i, d in enumerate(dataset_names)}
    ki = {k: i for i, k in enumerate(metric_ids)}

    scores = np.full((len(method_names), len(dataset_names), len(metric_ids)), np.nan, dtype=float)
    for r in rows:
        value = r["score"]
        if value not in ("", "NA"):
            scores[mi[r["method_id"]], di[r["dataset_id"]], ki[r["metric_id"]]] = float(value)

    return OpenProblems(
        task=task,
        method_names=method_names,
        dataset_names=dataset_names,
        metric_ids=metric_ids,
        polarity=("higher_is_better",) * len(metric_ids),
        scores=scores,
    )


def load_openproblems_svg_features() -> Duo2018Features:
    """Load the dataset features for the OpenProblems spatially-variable-genes task.

    Returns a ``Duo2018Features`` container (the same shape the Bradley-Terry
    tree consumes) holding the categorical descriptors parsed from each
    dataset id: the spatial assay ``technology`` (visium, merfish, slideseqv2,
    and so on), the ``organism``, and a cancer or non-cancer ``condition``.
    There are no numeric features. Provenance is in
    ``src/beam/data/README.md``.
    """
    csv_text = (
        resources.files(_CSV_PACKAGE).joinpath(_OP_SVG_FEATURES_CSV).read_text(encoding="utf-8")
    )
    rows = list(csv.DictReader(csv_text.splitlines()))
    dataset_names = tuple(r["dataset_id"] for r in rows)
    categorical = {feat: tuple(r[feat] for r in rows) for feat in _OP_SVG_FEATURES}
    return Duo2018Features(dataset_names=dataset_names, numeric={}, categorical=categorical)


# Cross-benchmark single-cell integration set for the cross-benchmark meta-analysis.
# Three benchmarks publish reusable per-method scores on the shared scIB metric
# family (ARI, ASW, kBET, LISI) for an overlapping set of classical integration
# methods: scIB (Luecken 2022), the OpenProblems batch_integration task, and
# Tran 2020. The five methods common to all three are combat, harmony, fastmnn,
# scanorama and liger. Provenance and the keep/discard reasoning are in
# src/beam/data/README.md.
_INTEGRATION_METHODS: Final[tuple[str, ...]] = (
    "combat",
    "harmony",
    "fastmnn",
    "scanorama",
    "liger",
)
_INTEGRATION_METRICS: Final[tuple[str, ...]] = ("ARI", "ASW", "kBET", "LISI")
# OpenProblems metric ids for the four shared metrics (all higher is better).
_OP_INTEGRATION_METRIC: Final[dict[str, str]] = {
    "ARI": "ari",
    "ASW": "asw_label",
    "kBET": "kbet",
    "LISI": "ilisi",
}
_OP_INTEGRATION_METHOD: Final[dict[str, str]] = {
    "combat": "combat",
    "harmony": "harmony",
    "fastmnn": "batchelor_fastmnn",
    "scanorama": "scanorama",
    "liger": "liger",
}


@dataclass(frozen=True)
class IntegrationBenchmarks:
    """The harmonized cross-benchmark single-cell integration set.

    Holds one record per (benchmark, dataset, method, metric): the rank of the
    method among the common methods on that metric within that benchmark's
    dataset, 1 best. Ranking within the common methods per benchmark, dataset
    and metric is the scale-free common currency across benchmarks that score
    on different native scales; for scIB and OpenProblems the rank is computed
    from the raw (unscaled) higher-is-better scores, for Tran from its published
    per-metric ranks. The five methods are common to all three benchmarks.

    Attributes
    ----------
    benchmark, dataset, method, metric
        Parallel label tuples, one entry per record.
    rank
        Float rank within the common methods, aligned with the labels.
    """

    benchmark: tuple[str, ...]
    dataset: tuple[str, ...]
    method: tuple[str, ...]
    metric: tuple[str, ...]
    rank: np.ndarray

    def mean_rank_records(self) -> tuple[list[str], list[str], list[str], list[float]]:
        """Collapse to the mean rank across metrics per (benchmark, dataset, method).

        Returns four parallel lists ``(methods, datasets, benchmarks, scores)``
        ready for ``beam.heterogeneity.source_variance_decomposition``, with the
        dataset label namespaced by benchmark so datasets nest in benchmark.
        """
        from collections import defaultdict

        groups: dict[tuple[str, str, str], list[float]] = defaultdict(list)
        for b, d, m, _metric, r in zip(
            self.benchmark, self.dataset, self.method, self.metric, self.rank, strict=True
        ):
            groups[(b, d, m)].append(float(r))
        methods, datasets, benchmarks, scores = [], [], [], []
        for (b, d, m), rs in groups.items():
            methods.append(m)
            datasets.append(f"{b}:{d}")
            benchmarks.append(b)
            scores.append(float(np.mean(rs)))
        return methods, datasets, benchmarks, scores

    def mean_rank_matrix(self) -> tuple[tuple[str, ...], tuple[str, ...], np.ndarray]:
        """Method by benchmark matrix of the mean rank (over datasets and metrics).

        Returns ``(methods, benchmarks, matrix)`` with the mean rank of each
        method in each benchmark, the content of the rank-disagreement heatmap.
        """
        from collections import defaultdict

        benchmarks = tuple(dict.fromkeys(self.benchmark))
        cell: dict[tuple[str, str], list[float]] = defaultdict(list)
        for b, _d, m, _metric, r in zip(
            self.benchmark, self.dataset, self.method, self.metric, self.rank, strict=True
        ):
            cell[(m, b)].append(float(r))
        matrix = np.full((len(_INTEGRATION_METHODS), len(benchmarks)), np.nan)
        for i, m in enumerate(_INTEGRATION_METHODS):
            for j, b in enumerate(benchmarks):
                if cell[(m, b)]:
                    matrix[i, j] = float(np.mean(cell[(m, b)]))
        return _INTEGRATION_METHODS, benchmarks, matrix


def _rank_within_common(
    value_by_method: dict[str, float], higher_is_better: bool
) -> dict[str, float]:
    """Average-rank the common methods present in one (dataset, metric) cell, 1 best."""
    from scipy.stats import rankdata

    names = [m for m in _INTEGRATION_METHODS if m in value_by_method]
    if len(names) < 2:
        return {}
    values = np.array([value_by_method[m] for m in names], dtype=float)
    oriented = -values if higher_is_better else values  # rank 1 = best
    ranks = rankdata(oriented, method="average")
    return dict(zip(names, ranks, strict=True))


def load_integration_benchmarks() -> IntegrationBenchmarks:
    """Load the harmonized scIB, OpenProblems and Tran integration benchmark set.

    Reads the bundled scIB raw scores and Tran ranks, plus the OpenProblems
    batch_integration scores already shipped, restricts to the five common
    methods and the four shared metrics (ARI, ASW, kBET, LISI), and reduces each
    benchmark-dataset-metric cell to a rank within the common methods. The
    result feeds the cross-benchmark analysis.

    Returns
    -------
    IntegrationBenchmarks
    """
    records: list[tuple[str, str, str, str, float]] = []

    # scIB: raw (unscaled) scores, higher is better; rank within common methods.
    scib_text = resources.files(_CSV_PACKAGE).joinpath("scib2022_metrics.csv").read_text("utf-8")
    scib_cells: dict[tuple[str, str], dict[str, float]] = {}
    for row in csv.DictReader(scib_text.splitlines()):
        scib_cells.setdefault((row["dataset"], row["metric"]), {})[row["method"]] = float(
            row["score"]
        )
    for (dataset, metric), vals in scib_cells.items():
        for method, r in _rank_within_common(vals, higher_is_better=True).items():
            records.append(("scIB", dataset, method, metric, r))

    # Tran: published per-metric ranks (lower is better); re-rank within common.
    tran_text = resources.files(_CSV_PACKAGE).joinpath("tran2020_metrics.csv").read_text("utf-8")
    tran_cells: dict[tuple[str, str], dict[str, float]] = {}
    for row in csv.DictReader(tran_text.splitlines()):
        tran_cells.setdefault((row["dataset"], row["metric"]), {})[row["method"]] = float(
            row["rank"]
        )
    for (dataset, metric), vals in tran_cells.items():
        for method, r in _rank_within_common(vals, higher_is_better=False).items():
            records.append(("Tran", dataset, method, metric, r))

    # OpenProblems batch_integration: raw scores, higher is better.
    op = load_openproblems("batch_integration")
    mi = {m: i for i, m in enumerate(op.method_names)}
    ki = {k: i for i, k in enumerate(op.metric_ids)}
    for di, dataset in enumerate(op.dataset_names):
        for metric, op_metric in _OP_INTEGRATION_METRIC.items():
            if op_metric not in ki:
                continue
            vals = {}
            for canon, op_name in _OP_INTEGRATION_METHOD.items():
                if op_name in mi:
                    v = op.scores[mi[op_name], di, ki[op_metric]]
                    if not np.isnan(v):
                        vals[canon] = float(v)
            for method, r in _rank_within_common(vals, higher_is_better=True).items():
                records.append(("OpenProblems", dataset.split("/")[-1], method, metric, r))

    records.sort()
    return IntegrationBenchmarks(
        benchmark=tuple(r[0] for r in records),
        dataset=tuple(r[1] for r in records),
        method=tuple(r[2] for r in records),
        metric=tuple(r[3] for r in records),
        rank=np.array([r[4] for r in records], dtype=float),
    )


def load_integration_published_ranks() -> dict[str, dict[str, int]]:
    """Load the benchmarks' own published ranks of the common integration methods.

    Returns a map ``{benchmark: {method: rank}}`` (rank 1 best) for the five
    common methods, as each benchmark reported them with its own machinery:
    Tran from its Table S7 final rank, scIB from its 0.6 biological / 0.4 batch
    weighted overall on its full metric set, and OpenProblems from its
    mean-of-scaled-scores leaderboard. These are the reported rankings the beam
    consistent re-ranking is compared against; provenance is in
    ``src/beam/data/README.md``.
    """
    text = (
        resources.files(_CSV_PACKAGE)
        .joinpath("integration_published_ranks.csv")
        .read_text(encoding="utf-8")
    )
    out: dict[str, dict[str, int]] = {}
    for row in csv.DictReader(text.splitlines()):
        out.setdefault(row["benchmark"], {})[row["method"]] = int(row["published_rank"])
    return out
