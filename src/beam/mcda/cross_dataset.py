"""Reduce a per-dataset score matrix to a per-tool summary for one metric."""

from __future__ import annotations

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
      this function or use ``rank_mean`` only on already-normalised data.

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
