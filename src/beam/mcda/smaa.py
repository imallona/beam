"""Stochastic multi-criteria acceptability analysis on an MCDA run."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from .facade import _KNOWN_METHODS, Result, run


@dataclass(frozen=True)
class SMAAReport:
    """Outcome of an SMAA weight-sampling sensitivity analysis.

    Holds a reference run with equal weights, the sampled weight matrix, the
    per-sample rank matrix, and three summary fields: the rank acceptability
    index, the central weight vector per tool, and the confidence factor per
    tool (Lahdelma and Salminen 2001).

    Shapes:
        sampled_weights: (n_samples, n_metrics)
        sampled_ranks:   (n_samples, n_tools), each row a rank permutation
        rank_acceptability_index: (n_tools, n_tools), entry [a, k - 1] is
            the empirical probability that tool a obtains rank k.
        central_weight_vector: (n_tools, n_metrics), the mean of the sampled
            weight vectors restricted to samples where tool a is top-ranked;
            row a is the zero vector if tool a is never top-ranked.
        confidence_factor: (n_tools,), the share of samples in which tool a
            is top-ranked; equal to rank_acceptability_index[:, 0].
    """

    base: Result
    sampled_weights: np.ndarray
    sampled_ranks: np.ndarray
    rank_acceptability_index: np.ndarray
    central_weight_vector: np.ndarray
    confidence_factor: np.ndarray
    method: str
    n_samples: int
    seed: int | None


def smaa(
    scores,
    polarity: Sequence[str],
    n_samples: int = 1000,
    method: str = "saw",
    alpha: Sequence[float] | None = None,
    seed: int | None = None,
) -> SMAAReport:
    """Run an SMAA-style weight-sampling sensitivity analysis on ``scores``.

    Draw ``n_samples`` weight vectors from a Dirichlet over the metrics
    simplex (so every sampled vector is non-negative and sums to 1). For
    each draw, run the full MCDA pipeline with ``run`` and record the rank
    vector. Tabulate three summaries:

    1. The rank acceptability index, the empirical probability per tool
       and per rank.
    2. The central weight vector per tool, the mean of the sampled weights
       restricted to samples where that tool is top-ranked. A tool that is
       never top-ranked gets the zero vector.
    3. The confidence factor per tool, the share of samples in which the
       tool is top-ranked.

    Parameters
    ----------
    scores
        Array-like of shape ``(n_tools, n_metrics)``.
    polarity
        Length ``n_metrics`` sequence of ``"higher_is_better"`` or
        ``"lower_is_better"``. Use ``beam.cards.polarities_for`` to source
        this from the registry.
    n_samples
        Number of weight vectors to draw. Defaults to 1000.
    method
        Aggregation method forwarded to ``run``. Any of the five methods
        supported by ``run``: ``"saw"``, ``"topsis"``, ``"vikor"``,
        ``"promethee_ii"`` or ``"comet"``.
    alpha
        Optional length ``n_metrics`` concentration vector for the
        Dirichlet draw. Defaults to ones, which gives a uniform
        distribution over the simplex.
    seed
        Optional integer seed for the random generator. Recorded in the
        report so the run can be reproduced.

    Returns
    -------
    SMAAReport
    """
    scores = np.asarray(scores, dtype=float)
    polarity = list(polarity)

    if scores.ndim != 2:
        raise ValueError(f"scores must be 2D; got shape {scores.shape}")
    n_tools, n_metrics = scores.shape
    if len(polarity) != n_metrics:
        raise ValueError(f"polarity has {len(polarity)} entries but scores has {n_metrics} columns")
    if n_samples < 1:
        raise ValueError(f"n_samples must be at least 1; got {n_samples}")
    if method not in _KNOWN_METHODS:
        raise ValueError(f"unknown method {method!r}; supported: {_KNOWN_METHODS}")

    if alpha is None:
        alpha_arr = np.ones(n_metrics)
    else:
        alpha_arr = np.asarray(alpha, dtype=float)
        if alpha_arr.shape != (n_metrics,):
            raise ValueError(f"alpha has shape {alpha_arr.shape}; expected ({n_metrics},)")
        if np.any(alpha_arr <= 0):
            raise ValueError("alpha must be strictly positive")

    rng = np.random.default_rng(seed)
    sampled_weights = rng.dirichlet(alpha_arr, size=n_samples)

    base = run(scores, polarity, weights="equal", method=method)

    sampled_ranks = np.empty((n_samples, n_tools), dtype=int)
    for s in range(n_samples):
        sampled_ranks[s] = run(scores, polarity, weights=sampled_weights[s], method=method).ranks

    rai = np.zeros((n_tools, n_tools), dtype=float)
    for a in range(n_tools):
        for k in range(1, n_tools + 1):
            rai[a, k - 1] = float((sampled_ranks[:, a] == k).sum()) / n_samples

    central = np.zeros((n_tools, n_metrics), dtype=float)
    for a in range(n_tools):
        mask = sampled_ranks[:, a] == 1
        if mask.any():
            central[a] = sampled_weights[mask].mean(axis=0)

    confidence = rai[:, 0]

    return SMAAReport(
        base=base,
        sampled_weights=sampled_weights,
        sampled_ranks=sampled_ranks,
        rank_acceptability_index=rai,
        central_weight_vector=central,
        confidence_factor=confidence,
        method=method,
        n_samples=n_samples,
        seed=seed,
    )
