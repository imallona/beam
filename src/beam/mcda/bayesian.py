"""Posterior probabilities for comparing two methods across datasets.

The critical-difference test (``beam.mcda.critical_difference``) reports whether
methods differ. The pairwise superiority report (``beam.mcda.pairwise_superiority``)
reports by how much, as outperformance counts, an effect size and a sign test.
Both are frequentist: they answer with a p-value, which is the chance of the
observed split if the two methods scored the same, not the chance that one method
scores higher. Choosing between two methods needs the second quantity.

``bayesian_sign_comparison`` supplies it. It reads the same per-pair
outperformance counts ``pairwise_superiority`` already produced and treats them as
the Bayesian sign test of Benavoli, Corani, Demsar and Zaffalon (2017). For a
pair, each shared dataset falls into one of three regions: A practically better, B
practically better, or the two within the region of practical equivalence (the
ROPE, set to the metric's noise floor by the superiority report). The proportion
of future datasets in each region follows a Dirichlet posterior whose parameters
are the observed counts plus a prior. From that posterior the function reports the
probability that A is practically better, that the two are practically
equivalent, and that B is practically better, three numbers that sum to one.

It is the posterior companion to ``pairwise_superiority`` and ``pairwise_transitivity``,
both of which also post-process a ``PairwiseSuperiorityReport`` rather than
re-reading the scores. The reference implementation of the test is the baycomp
package (Benavoli et al.), which beam matches on the closed-form posterior mean
and, with a matched prior, on the Monte Carlo region probabilities.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .pairwise import PairwiseSuperiorityReport

_PLACEMENTS = ("rope", "uniform", "neutral")


@dataclass(frozen=True)
class PairPosterior:
    """The Bayesian sign-test posterior for one method pair.

    Attributes
    ----------
    a, b
        Method indices, with ``a < b``.
    n_compared
        Datasets where both methods are observed, the sum of the three counts.
    a_better, equivalent, b_better
        Datasets where A scores higher than B by more than the ROPE, where the two
        are within the ROPE, and where B scores higher than A. Taken from the
        superiority report.
    p_a_better, p_equivalent, p_b_better
        Posterior probability that A is practically better, that the two are
        practically equivalent, and that B is practically better: the chance that
        the corresponding region holds the largest share of future datasets. They
        sum to one.
    mean_a_better, mean_equivalent, mean_b_better
        Posterior mean share of each region, the Dirichlet mean
        ``alpha_i / sum(alpha)``. The expected fraction of future datasets in each
        region. They sum to one.
    decision
        ``"a_better"``, ``"b_better"`` or ``"equivalent"`` when the matching
        probability reaches ``decision_threshold``; ``"inconclusive"`` otherwise.
    """

    a: int
    b: int
    n_compared: int
    a_better: int
    equivalent: int
    b_better: int
    p_a_better: float
    p_equivalent: float
    p_b_better: float
    mean_a_better: float
    mean_equivalent: float
    mean_b_better: float
    decision: str


@dataclass(frozen=True)
class BayesianSignReport:
    """Bayesian sign-test posteriors over every method pair.

    Attributes
    ----------
    method_names
        Method labels in index order, or ``None`` when none were given.
    rope
        The region of practical equivalence taken from the superiority
        report, in native units.
    prior_strength, prior_placement
        The Dirichlet prior: ``prior_strength`` pseudo-observations placed as
        ``prior_placement`` (``"rope"``, ``"uniform"`` or ``"neutral"``).
    n_samples, seed
        The Monte Carlo sample count and seed behind the region probabilities.
    decision_threshold
        The probability a region must reach for a decisive ``per_pair`` label.
    probability_better
        ``(n_methods, n_methods)`` matrix. Entry ``[i, j]`` is the posterior
        probability that method ``i`` is practically better than method ``j``. The
        diagonal is NaN. ``[i, j] + [j, i]`` plus the equivalence probability is 1.
    probability_equivalent
        ``(n_methods, n_methods)`` symmetric matrix of the posterior probability
        that the two methods are practically equivalent.
    standing
        ``(n_methods,)`` score: the mean over the other methods of the posterior
        probability of being practically better than or equivalent to them, in
        ``[0, 1]``.
    order
        Method indices sorted by ``standing``, highest first.
    per_pair
        The posterior for every unordered pair.
    """

    method_names: tuple[str, ...] | None
    rope: float
    prior_strength: float
    prior_placement: str
    n_samples: int
    seed: int
    decision_threshold: float
    probability_better: np.ndarray
    probability_equivalent: np.ndarray
    standing: np.ndarray
    order: np.ndarray
    per_pair: tuple[PairPosterior, ...]


def _prior_vector(strength: float, placement: str) -> np.ndarray:
    """Prior pseudo-counts in (a_better, equivalent, b_better) order."""
    if placement == "rope":
        return np.array([0.0, strength, 0.0])
    if placement == "uniform":
        return np.full(3, strength / 3.0)
    if placement == "neutral":
        return np.array([strength / 2.0, 0.0, strength / 2.0])
    raise ValueError(f"prior_placement must be one of {_PLACEMENTS}; got {placement!r}")


def bayesian_sign_comparison(
    report: PairwiseSuperiorityReport,
    prior_strength: float = 1.0,
    prior_placement: str = "rope",
    decision_threshold: float = 0.95,
    n_samples: int = 50000,
    seed: int = 42,
) -> BayesianSignReport:
    """Posterior probability that one method is practically better than another.

    Reads a ``PairwiseSuperiorityReport`` and applies the Bayesian sign test of
    Benavoli et al. (2017) to each pair's outperformance counts. The proportions of
    future datasets in the three regions (A practically better, equivalent, B
    practically better) follow a Dirichlet posterior whose parameters are the
    observed counts plus ``prior_strength`` pseudo-observations placed by
    ``prior_placement``. The probability that a region holds the largest share is
    estimated by drawing ``n_samples`` from the posterior; the posterior mean share
    of each region is the closed-form Dirichlet mean.

    Parameters
    ----------
    report
        A ``PairwiseSuperiorityReport`` from ``beam.mcda.pairwise_superiority``. Its
        ROPE (set when the report was built, often the metric's noise floor) is the
        equivalence band used here, so the equivalence count already reflects it.
    prior_strength
        Number of prior pseudo-observations. Default 1, a single weak prior dataset.
        Must be non-negative.
    prior_placement
        Where the prior mass sits: ``"rope"`` (default, all on the equivalence
        region, the weak prior that the two are equivalent, matching the baycomp
        default), ``"uniform"`` (split across the three regions), or ``"neutral"``
        (split across the two directional regions, none on the equivalence region).
    decision_threshold
        The posterior probability a region must reach for a decisive ``per_pair``
        ``decision`` label. Default 0.95.
    n_samples
        Monte Carlo draws from each posterior. Default 50000.
    seed
        Seed for the draws, so two runs reproduce. Default 42.

    Returns
    -------
    BayesianSignReport

    Raises
    ------
    ValueError
        If ``prior_strength`` is negative, ``prior_placement`` is unknown, or
        ``decision_threshold`` is not in ``(0, 1]``.

    Examples
    --------
    >>> import numpy as np
    >>> from beam.mcda import pairwise_superiority, bayesian_sign_comparison
    >>> high = [0.9, 0.8, 0.7, 0.85, 0.75, 0.95, 0.8, 0.9]
    >>> low = [0.2, 0.1, 0.3, 0.15, 0.25, 0.05, 0.2, 0.1]
    >>> sup = pairwise_superiority(np.array([high, low]), "higher_is_better")
    >>> bayes = bayesian_sign_comparison(sup, seed=0)
    >>> bayes.per_pair[0].decision  # method 0 better on every dataset
    'a_better'
    >>> float(bayes.probability_better[0, 1]) > 0.95
    True
    """
    if prior_strength < 0:
        raise ValueError(f"prior_strength must be non-negative; got {prior_strength}")
    if not 0.0 < decision_threshold <= 1.0:
        raise ValueError(f"decision_threshold must be in (0, 1]; got {decision_threshold}")
    prior = _prior_vector(float(prior_strength), prior_placement)

    n = report.probability_superior.shape[0]
    names = report.method_names
    rng = np.random.default_rng(seed)

    prob_better = np.full((n, n), np.nan)
    prob_equivalent = np.zeros((n, n))
    per_pair: list[PairPosterior] = []

    for pair in report.per_pair:
        counts = np.array([pair.a_outperforms, pair.equivalent, pair.b_outperforms], dtype=float)
        alpha = counts + prior
        total = float(alpha.sum())
        means = alpha / total if total > 0 else np.full(3, 1.0 / 3.0)

        draws = rng.dirichlet(alpha if total > 0 else np.ones(3), size=n_samples)
        top_region = np.argmax(draws, axis=1)
        p_a = float(np.mean(top_region == 0))
        p_eq = float(np.mean(top_region == 1))
        p_b = float(np.mean(top_region == 2))

        decision = _decide(p_a, p_eq, p_b, decision_threshold)

        prob_better[pair.a, pair.b] = p_a
        prob_better[pair.b, pair.a] = p_b
        prob_equivalent[pair.a, pair.b] = prob_equivalent[pair.b, pair.a] = p_eq

        per_pair.append(
            PairPosterior(
                a=pair.a,
                b=pair.b,
                n_compared=pair.n_compared,
                a_better=pair.a_outperforms,
                equivalent=pair.equivalent,
                b_better=pair.b_outperforms,
                p_a_better=p_a,
                p_equivalent=p_eq,
                p_b_better=p_b,
                mean_a_better=float(means[0]),
                mean_equivalent=float(means[1]),
                mean_b_better=float(means[2]),
                decision=decision,
            )
        )

    standing = np.full(n, np.nan)
    for i in range(n):
        contributions = [
            prob_better[i, j] + 0.5 * prob_equivalent[i, j]
            for j in range(n)
            if i != j and np.isfinite(prob_better[i, j])
        ]
        if contributions:
            standing[i] = float(np.mean(contributions))

    order = np.argsort(-np.nan_to_num(standing, nan=-np.inf), kind="stable")

    return BayesianSignReport(
        method_names=names,
        rope=report.rope,
        prior_strength=float(prior_strength),
        prior_placement=prior_placement,
        n_samples=int(n_samples),
        seed=int(seed),
        decision_threshold=float(decision_threshold),
        probability_better=prob_better,
        probability_equivalent=prob_equivalent,
        standing=standing,
        order=order,
        per_pair=tuple(per_pair),
    )


def _decide(p_a: float, p_eq: float, p_b: float, threshold: float) -> str:
    if p_a >= threshold:
        return "a_better"
    if p_b >= threshold:
        return "b_better"
    if p_eq >= threshold:
        return "equivalent"
    return "inconclusive"
