"""Compare methods two at a time with an effect size and a tie band.

The critical-difference diagram (``beam.mcda.critical_difference``) says which
methods differ beyond chance. It does not say by how much, or how often one
outperforms another. Its mean-rank post-hoc also depends on the whole pool:
adding or dropping a method can change whether two others are called different, a
known limitation (Benavoli, Corani and Mangili 2016).

``pairwise_superiority`` compares two methods at a time, on the datasets they
share, with a result that does not depend on the pool. For a pair, on each shared
dataset one method scores higher than the other. Counting over the datasets gives
three numbers: how often A outperforms B, how often B outperforms A, and how often
the two are equivalent. Two methods are equivalent on a dataset when their scores
differ by no more than the region of practical equivalence (the ROPE), which can
be set to the metric's noise floor, the smallest difference the card calls
interpretable. The fraction of datasets on which A outperforms B is the
probability of superiority, the standard name (Grissom 1994) for this
common-language effect size: how often A scores higher than B on a dataset. A sign
test on the decisive datasets, equivalences dropped, says whether the difference
is more than chance.

This is the effect-size and practical-equivalence companion to the
critical-difference test, in the spirit of the Bayesian comparison of Benavoli et
al. (2017), kept frequentist and descriptive here. It reads one metric, or a
composite, as a tool-by-dataset matrix.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from scipy.stats import binomtest

_ORIENTATION = {"higher_is_better": 1.0, "lower_is_better": -1.0}


@dataclass(frozen=True)
class PairSuperiority:
    """The comparison of one method pair across datasets.

    Attributes
    ----------
    a, b
        Method indices, with ``a < b``.
    n_compared
        Datasets where both methods are observed.
    a_outperforms, equivalent, b_outperforms
        Datasets where A scores higher than B by more than the ROPE, where the two
        are within the ROPE, and where B scores higher than A. They sum to
        ``n_compared``.
    p_superior_a, p_equivalent, p_superior_b
        ``a_outperforms``, ``equivalent`` and ``b_outperforms`` as fractions of
        ``n_compared``: the probability that A outperforms B on a dataset, that the
        two are equivalent, and that B outperforms A. NaN when nothing is compared.
    sign_pvalue
        Two-sided sign-test p-value on the decisive datasets (equivalences
        dropped): the chance of a split this lopsided if the two methods were even.
        1.0 when there are no decisive datasets.
    """

    a: int
    b: int
    n_compared: int
    a_outperforms: int
    equivalent: int
    b_outperforms: int
    p_superior_a: float
    p_equivalent: float
    p_superior_b: float
    sign_pvalue: float


@dataclass(frozen=True)
class PairwiseSuperiorityReport:
    """Pairwise method comparison with effect sizes and practical equivalence.

    Attributes
    ----------
    method_names
        Method labels in index order, or ``None`` when none were given.
    rope
        The region of practical equivalence in native units. A difference no
        larger than this counts as equivalent.
    probability_superior
        ``(n_methods, n_methods)`` matrix. Entry ``[i, j]`` is the probability that
        method ``i`` outperforms method ``j`` over their shared datasets. The
        diagonal is NaN. ``[i, j] + [j, i]`` plus the equivalence fraction is 1.
    standing
        ``(n_methods,)`` Copeland-style score: the mean over the other methods of
        the probability of outperforming or being equivalent to them, in
        ``[0, 1]``. 1 outperforms every other method on every dataset, 0.5 is even.
    order
        Method indices sorted by ``standing``, highest first.
    per_pair
        The record for every unordered pair.
    equivalent_pairs
        Pairs whose sign test does not reach ``alpha``: on this evidence the two
        are not distinguishable across the datasets.
    alpha
        The significance level behind ``equivalent_pairs``.
    """

    method_names: tuple[str, ...] | None
    rope: float
    probability_superior: np.ndarray
    standing: np.ndarray
    order: np.ndarray
    per_pair: tuple[PairSuperiority, ...]
    equivalent_pairs: tuple[tuple[int, int], ...]
    alpha: float


def pairwise_superiority(
    scores,
    polarity: str,
    rope: float = 0.0,
    method_names: Sequence[str] | None = None,
    alpha: float = 0.05,
) -> PairwiseSuperiorityReport:
    """Compare every method pair across datasets with a probability of superiority.

    Reads a tool-by-dataset matrix on one metric (or a composite). Each pair is
    compared on the datasets where both are observed. Two methods are equivalent on
    a dataset when their scores differ by no more than ``rope``; otherwise the
    higher-scoring method outperforms the other, with the direction of "higher" set
    by ``polarity``. The probability of superiority of A over B is the fraction of
    shared datasets on which A outperforms B, and a sign test on the decisive
    datasets says whether the difference is more than chance.

    Parameters
    ----------
    scores
        Array-like of shape ``(n_methods, n_datasets)`` in native units. Missing
        cells are NaN and dropped per pair.
    polarity
        ``"higher_is_better"`` or ``"lower_is_better"``, the direction in which a
        higher score means a method outperforms.
    rope
        The region of practical equivalence in native units. A difference within it
        is treated as equivalent. Pass the metric's ``comparability.noise_floor``
        to count an outperformance only past the smallest interpretable difference.
        Default 0.
    method_names
        Optional length ``n_methods`` labels carried in the report.
    alpha
        Significance level for ``equivalent_pairs``. Default 0.05.

    Returns
    -------
    PairwiseSuperiorityReport

    Raises
    ------
    ValueError
        If ``scores`` is not 2D, has fewer than two methods or two datasets,
        ``polarity`` is not monotone, ``rope`` is negative, or ``method_names``
        has the wrong length.

    Examples
    --------
    >>> import numpy as np
    >>> from beam.mcda import pairwise_superiority
    >>> scores = np.array([[0.9, 0.8, 0.7], [0.5, 0.6, 0.4], [0.2, 0.1, 0.3]])
    >>> report = pairwise_superiority(scores, "higher_is_better")
    >>> int(report.order[0])  # method 0 outperforms the others on every dataset
    0
    >>> float(report.probability_superior[0, 1])
    1.0
    """
    x = np.asarray(scores, dtype=float)
    if x.ndim != 2:
        raise ValueError(f"scores must be 2D (methods, datasets); got shape {x.shape}")
    n_methods, n_datasets = x.shape
    if n_methods < 2:
        raise ValueError(f"need at least two methods to compare; got {n_methods}")
    if n_datasets < 2:
        raise ValueError(f"need at least two datasets for a pairwise record; got {n_datasets}")
    if polarity not in _ORIENTATION:
        raise ValueError(
            f"polarity must be 'higher_is_better' or 'lower_is_better'; got {polarity!r}"
        )
    if rope < 0:
        raise ValueError(f"rope must be non-negative; got {rope}")
    names = None if method_names is None else list(method_names)
    if names is not None and len(names) != n_methods:
        raise ValueError(
            f"method_names has {len(names)} entries but scores has {n_methods} methods"
        )

    oriented = x * _ORIENTATION[polarity]

    prob = np.full((n_methods, n_methods), np.nan)
    equivalent_fraction = np.zeros((n_methods, n_methods))
    per_pair: list[PairSuperiority] = []
    equivalent_pairs: list[tuple[int, int]] = []

    for a in range(n_methods):
        for b in range(a + 1, n_methods):
            both = np.isfinite(oriented[a]) & np.isfinite(oriented[b])
            diff = oriented[a, both] - oriented[b, both]
            n = int(both.sum())
            a_over = int((diff > rope).sum())
            b_over = int((diff < -rope).sum())
            equal = n - a_over - b_over
            if n:
                p_a, p_eq, p_b = a_over / n, equal / n, b_over / n
            else:
                p_a = p_eq = p_b = float("nan")
            decisive = a_over + b_over
            sign_p = float(binomtest(a_over, decisive, 0.5).pvalue) if decisive else 1.0

            prob[a, b] = p_a
            prob[b, a] = p_b
            equivalent_fraction[a, b] = equivalent_fraction[b, a] = p_eq if n else 0.0
            per_pair.append(
                PairSuperiority(
                    a=a,
                    b=b,
                    n_compared=n,
                    a_outperforms=a_over,
                    equivalent=equal,
                    b_outperforms=b_over,
                    p_superior_a=p_a,
                    p_equivalent=p_eq,
                    p_superior_b=p_b,
                    sign_pvalue=sign_p,
                )
            )
            if sign_p > alpha:
                equivalent_pairs.append((a, b))

    standing = np.full(n_methods, np.nan)
    for i in range(n_methods):
        contributions = []
        for j in range(n_methods):
            if i == j or not np.isfinite(prob[i, j]):
                continue
            contributions.append(prob[i, j] + 0.5 * equivalent_fraction[i, j])
        if contributions:
            standing[i] = float(np.mean(contributions))

    order = np.argsort(-np.nan_to_num(standing, nan=-np.inf), kind="stable")

    return PairwiseSuperiorityReport(
        method_names=tuple(names) if names is not None else None,
        rope=float(rope),
        probability_superior=prob,
        standing=standing,
        order=order,
        per_pair=tuple(per_pair),
        equivalent_pairs=tuple(equivalent_pairs),
        alpha=float(alpha),
    )
