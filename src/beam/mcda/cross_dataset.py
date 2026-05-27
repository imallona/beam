"""Reduce a per-dataset score matrix to a per-tool summary for one metric."""

from __future__ import annotations

import warnings
from collections.abc import Sequence

import numpy as np

_KNOWN_RULES = ("arithmetic_mean", "geometric_mean", "median", "rank_mean")


def aggregate_across_datasets(
    scores: np.ndarray,
    rule: str,
) -> np.ndarray:
    """Reduce a tool by dataset score matrix to a tool vector for one metric.

    Used to fold the dataset dimension out of a benchmark before MCDA, so
    that the rest of the pipeline can work on a tool by metric matrix. The
    choice of rule comes from the metric card's
    ``comparability.recommended_aggregation_across_datasets`` field.

    Rules:

    - ``arithmetic_mean``: per-row mean. The default for bounded interval
      and ratio metrics where the value can be averaged on its own scale.
    - ``geometric_mean``: per-row geometric mean. Requires strictly
      positive scores. The natural mean for ratio metrics whose values
      span orders of magnitude (Smith 1988), notably runtime and peak
      memory. Raises if any entry is non-positive.
    - ``median``: per-row median. Outlier-robust summary.
    - ``rank_mean``: rank each tool within each dataset (1 is best on a
      higher-is-better metric), then take the per-tool mean rank. Polarity
      is not consulted here; the caller must align polarity before calling
      this function or use ``rank_mean`` only on already-normalized data.

    Parameters
    ----------
    scores
        2D array of shape ``(n_tools, n_datasets)``.
    rule
        One of the strings listed above. The caller typically pulls this
        from ``MetricProperties.recommended_aggregation_across_datasets``.

    Returns
    -------
    np.ndarray
        1D array of length ``n_tools``.
    """
    scores = np.asarray(scores, dtype=float)
    if scores.ndim != 2:
        raise ValueError(f"scores must be 2D; got shape {scores.shape}")
    if rule not in _KNOWN_RULES:
        raise ValueError(f"unknown rule {rule!r}; supported: {_KNOWN_RULES}")

    if rule == "arithmetic_mean":
        return scores.mean(axis=1)
    if rule == "geometric_mean":
        if np.any(scores <= 0):
            raise ValueError("geometric_mean requires strictly positive scores")
        return np.exp(np.log(scores).mean(axis=1))
    if rule == "median":
        return np.median(scores, axis=1)
    # rank_mean
    n_tools, n_datasets = scores.shape
    ranks = np.empty_like(scores)
    for d in range(n_datasets):
        col = scores[:, d]
        order = np.argsort(-col, kind="stable")
        col_ranks = np.empty(n_tools, dtype=float)
        current_rank = 1
        for i, idx in enumerate(order):
            if i > 0 and col[idx] < col[order[i - 1]]:
                current_rank = i + 1
            col_ranks[idx] = current_rank
        ranks[:, d] = col_ranks
    return ranks.mean(axis=1)


def reduce_tensor(
    tensor: np.ndarray,
    rules: Sequence[str],
    metric_ids: Sequence[str] | None = None,
    on_zero_coverage: str = "error",
) -> np.ndarray:
    """Fold the dataset axis of a tool by dataset by metric tensor, nan-aware.

    Each metric column is reduced over the dataset axis with its own rule, so
    the MCDA pipeline downstream sees a tool by metric matrix. Unlike
    ``aggregate_across_datasets``, this function tolerates missing cells: a tool
    measured on only some datasets is summarized over the datasets where it was
    observed. This available-case summary is not imputation; it estimates each
    tool's performance from the runs that exist.

    A tool with no observed dataset for a metric (zero coverage) has nothing to
    summarize. By default ``on_zero_coverage="error"`` raises, since the pooled
    matrix cannot rank a value that does not exist. ``on_zero_coverage="nan"``
    instead leaves that cell missing, so the downstream missing-data policy on
    the ranking call (``beam.rank(..., missing=...)``) decides what to do with
    it, rather than this function deciding for the caller.

    When a metric column has no missing cells the reduction delegates to
    ``aggregate_across_datasets``, so the complete-data path supports every rule
    including ``rank_mean``. When a column has missing cells, ``rank_mean`` is
    rejected: coverage-aware ranking across datasets is future work tied to the
    heterogeneity module.

    Parameters
    ----------
    tensor
        3D array of shape ``(n_tools, n_datasets, n_metrics)``.
    rules
        Length ``n_metrics`` sequence of reduction rule names, one per metric.
        Typically sourced from each card's
        ``recommended_aggregation_across_datasets``.
    metric_ids
        Optional length ``n_metrics`` labels used only in error messages.
    on_zero_coverage
        ``"error"`` (default) raises when a tool has no observed dataset for a
        metric; ``"nan"`` leaves that cell missing for the downstream policy.

    Returns
    -------
    np.ndarray
        Tool by metric matrix of shape ``(n_tools, n_metrics)``.

    Raises
    ------
    ValueError
        If the tensor is not 3D, the rule count does not match the metric
        count, ``on_zero_coverage="error"`` and a tool has no observed dataset
        for some metric, or a geometric-mean column has a non-positive observed
        value.
    NotImplementedError
        If ``rank_mean`` is requested on a column that has missing cells.
    """
    tensor = np.asarray(tensor, dtype=float)
    if tensor.ndim != 3:
        raise ValueError(f"tensor must be 3D; got shape {tensor.shape}")
    if on_zero_coverage not in ("error", "nan"):
        raise ValueError(f"on_zero_coverage must be 'error' or 'nan'; got {on_zero_coverage!r}")
    n_tools, _, n_metrics = tensor.shape
    if len(rules) != n_metrics:
        raise ValueError(f"rules has {len(rules)} entries but tensor has {n_metrics} metrics")

    out = np.empty((n_tools, n_metrics), dtype=float)
    for j in range(n_metrics):
        label = metric_ids[j] if metric_ids is not None else f"index {j}"
        out[:, j] = _reduce_column(tensor[:, :, j], rules[j], label, on_zero_coverage)
    return out


def _reduce_column(
    per_dataset: np.ndarray, rule: str, label: object, on_zero_coverage: str = "error"
) -> np.ndarray:
    """Reduce one metric's tool by dataset slice to a tool vector, nan-aware."""
    if rule not in _KNOWN_RULES:
        raise ValueError(f"unknown rule {rule!r}; supported: {_KNOWN_RULES}")

    observed = ~np.isnan(per_dataset)
    if on_zero_coverage == "error" and not observed.any(axis=1).all():
        missing = np.where(~observed.any(axis=1))[0].tolist()
        raise ValueError(
            f"metric {label!r} has tool rows with no observed dataset (indices {missing}); "
            "reduce or analyze per dataset, use the heterogeneity module, or choose a "
            "missing-data policy on the ranking call (beam.rank(..., missing=...))"
        )

    if observed.all():
        return aggregate_across_datasets(per_dataset, rule)

    # A zero-coverage tool row reduces to NaN here (only reached when the caller
    # asked for on_zero_coverage="nan"); silence the all-NaN-slice warning.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        if rule == "arithmetic_mean":
            return np.nanmean(per_dataset, axis=1)
        if rule == "median":
            return np.nanmedian(per_dataset, axis=1)
        if rule == "geometric_mean":
            if np.nanmin(per_dataset) <= 0:
                raise ValueError(
                    f"geometric_mean reduction for metric {label!r} needs positive scores"
                )
            return np.exp(np.nanmean(np.log(per_dataset), axis=1))
    # rank_mean
    raise NotImplementedError(
        f"rank_mean cross-dataset reduction for metric {label!r} with missing cells is "
        "coverage-aware future work; reduce per dataset first"
    )
