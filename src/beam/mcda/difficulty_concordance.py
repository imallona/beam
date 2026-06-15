"""Whether method families find the same datasets hard.

A dataset can be hard because the biology is complex, in which case every method
struggles, or because of something one family of methods depends on, such as
label quality for semi-supervised methods, in which case another family is
unaffected. The distinction matters for a cross-benchmark reading: a
recommendation that holds for classical methods need not hold for deep-learning
ones when the datasets are hard for different reasons.

``difficulty_concordance`` splits the methods into families (deep-learning versus
classical, or semi-supervised versus unsupervised), measures each dataset's
difficulty for each family as the family's mean score after orienting and min-max
scaling every metric, and correlates the per-family difficulty profiles across
datasets with Spearman. High concordance means the hardness comes from the data;
low concordance means it comes from the method family.

It is the family-split companion to :func:`dataset_discrimination`, which measures
how much a dataset separates all its methods at once.
"""

from __future__ import annotations

import warnings
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from scipy.stats import spearmanr

from .dataset_discrimination import _minmax_per_metric, _oriented


@dataclass(frozen=True)
class DifficultyConcordanceReport:
    """Whether method families find the same datasets hard.

    Attributes
    ----------
    family_names
        Family labels in first-seen order, indexing the matrix rows.
    dataset_ids
        Dataset labels in input order, or ``None`` when the input carried none.
    family_score
        ``(n_families, n_datasets)`` mean pooled normalized score per family per
        dataset, higher meaning the family does better (the dataset is easier for
        it). ``nan`` where a family has no observed method on a dataset.
    concordance
        ``(n_families, n_families)`` Spearman correlation across the datasets
        between the families' difficulty profiles. The diagonal is 1; an entry is
        ``nan`` when the two families share fewer than ``min_pairwise`` datasets.
    coverage
        ``(n_families, n_families)`` count of datasets where both families have a
        finite score, the denominator behind each correlation.
    mean_pairwise_concordance
        Mean of the off-diagonal finite ``concordance`` entries. High means the
        families agree on which datasets are hard.
    per_dataset_range
        Max-minus-min family score per dataset, the size of the family
        disagreement on that dataset. ``nan`` when fewer than two families are
        observed.
    most_divergent_dataset
        Dataset id with the largest ``per_dataset_range``, where the families
        disagree most on difficulty, or ``None``.
    """

    family_names: tuple[str, ...]
    dataset_ids: tuple[str, ...] | None
    family_score: np.ndarray
    concordance: np.ndarray
    coverage: np.ndarray
    mean_pairwise_concordance: float
    per_dataset_range: np.ndarray
    most_divergent_dataset: str | None


def difficulty_concordance(
    scores,
    polarity: Sequence[str],
    families: Sequence[str],
    dataset_ids: Sequence[str] | None = None,
    min_pairwise: int = 3,
) -> DifficultyConcordanceReport:
    """Test whether method families find the same datasets hard.

    Parameters
    ----------
    scores
        Tensor of shape ``(n_methods, n_datasets, n_metrics)``. Missing cells are
        ``nan`` and handled available-case; nothing is imputed. Pass one
        benchmark per call, since the min-max scaling is within the tensor.
    polarity
        Length ``n_metrics`` sequence of ``"higher_is_better"`` or
        ``"lower_is_better"``. Drop ``"target_value"`` metrics before calling.
    families
        Length ``n_methods`` family label per method, for example ``"DL"`` or
        ``"classical"``. Methods sharing a label form one family.
    dataset_ids
        Optional length ``n_datasets`` labels carried into the report.
    min_pairwise
        Minimum datasets where two families both have a score for their
        concordance to be computed. Default 3.

    Returns
    -------
    DifficultyConcordanceReport

    Raises
    ------
    ValueError
        If ``scores`` is not three-dimensional, or ``polarity``/``families``
        lengths do not match the tensor, or fewer than two families are given.
    """
    scores = np.asarray(scores, dtype=float)
    if scores.ndim != 3:
        raise ValueError(f"scores must be (n_methods, n_datasets, n_metrics); got {scores.shape}")
    n_methods, n_datasets, n_metrics = scores.shape
    if len(polarity) != n_metrics:
        raise ValueError(f"polarity length {len(polarity)} does not match {n_metrics} metrics")
    if len(families) != n_methods:
        raise ValueError(f"families length {len(families)} does not match {n_methods} methods")
    if dataset_ids is not None and len(dataset_ids) != n_datasets:
        raise ValueError(f"dataset_ids length {len(dataset_ids)} does not match {n_datasets}")

    family_names = tuple(dict.fromkeys(str(f) for f in families))
    if len(family_names) < 2:
        raise ValueError("need at least two distinct families")

    normalized = _minmax_per_metric(_oriented(scores, polarity))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        pooled = np.nanmean(normalized, axis=2)  # (n_methods, n_datasets)

    member_rows = [
        [i for i, f in enumerate(families) if str(f) == name] for name in family_names
    ]
    family_score = np.full((len(family_names), n_datasets), np.nan)
    for fi, rows in enumerate(member_rows):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            family_score[fi] = np.nanmean(pooled[rows], axis=0)

    n_families = len(family_names)
    concordance = np.full((n_families, n_families), np.nan)
    coverage = np.zeros((n_families, n_families), dtype=int)
    np.fill_diagonal(concordance, 1.0)
    for a in range(n_families):
        for b in range(a + 1, n_families):
            both = np.isfinite(family_score[a]) & np.isfinite(family_score[b])
            n_shared = int(both.sum())
            coverage[a, b] = coverage[b, a] = n_shared
            if n_shared < min_pairwise:
                continue
            xa, xb = family_score[a, both], family_score[b, both]
            if np.ptp(xa) == 0 or np.ptp(xb) == 0:
                continue
            rho = float(spearmanr(xa, xb).statistic)
            concordance[a, b] = concordance[b, a] = rho

    off_diagonal = concordance[~np.eye(n_families, dtype=bool)]
    finite_off = off_diagonal[np.isfinite(off_diagonal)]
    mean_pairwise = float(finite_off.mean()) if finite_off.size else float("nan")

    observed_per_dataset = np.isfinite(family_score).sum(axis=0)
    per_dataset_range = np.full(n_datasets, np.nan)
    for d in range(n_datasets):
        if observed_per_dataset[d] >= 2:
            col = family_score[:, d]
            col = col[np.isfinite(col)]
            per_dataset_range[d] = float(col.max() - col.min())

    most_divergent = None
    if dataset_ids is not None and np.isfinite(per_dataset_range).any():
        most_divergent = dataset_ids[int(np.nanargmax(per_dataset_range))]

    return DifficultyConcordanceReport(
        family_names=family_names,
        dataset_ids=tuple(dataset_ids) if dataset_ids is not None else None,
        family_score=family_score,
        concordance=concordance,
        coverage=coverage,
        mean_pairwise_concordance=mean_pairwise,
        per_dataset_range=per_dataset_range,
        most_divergent_dataset=most_divergent,
    )
