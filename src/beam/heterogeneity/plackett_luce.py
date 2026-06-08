"""Plackett-Luce models on per-dataset method rankings.

The Bradley-Terry tree works from pairwise wins. When the natural input is a
full ranking of the methods per dataset, the Plackett-Luce model (Turner, van
Etten, Firth and Kosmidis) is the direct generalisation: it turns each
dataset's ordering of the methods into a single latent strength per method,
the worth, with the worths summing to one. On strictly pairwise input it
reduces to the Bradley-Terry model, so it is the wider tool for the same
question of which method is stronger overall.

For one metric, each dataset column of a method by dataset matrix is read as a
ranking of the methods (the higher score ranks first, after orienting by
polarity), with ties allowed and missing cells left out of that dataset's
ranking. The model is fit by R's PlackettLuce in a one-shot subprocess, the
same boundary as the other heterogeneity wrappers. Use
``plackett_luce_available`` to check the R toolchain before calling
``plackett_luce``.

This is a global ranking tool, not a heterogeneity split: it complements the
Bradley-Terry tree (which localises where the ranking reverses) by giving a
worth with a reference-free quasi-standard-error per method, so two methods
can be compared without picking a baseline.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from scipy.stats import rankdata

from ._rsubprocess import (
    RExecutionError,
    RNotAvailableError,
    packages_available,
    run_rscript,
)

_R_PACKAGE = "beam.heterogeneity"
_R_SCRIPT = "plackett_luce.R"
_R_PACKAGES = ("PlackettLuce", "qvcalc", "jsonlite")
_FIT_TIMEOUT_SECONDS = 300

_POLARITIES = ("higher_is_better", "lower_is_better")

__all__ = [
    "PlackettLuceReport",
    "RExecutionError",
    "RNotAvailableError",
    "plackett_luce",
    "plackett_luce_available",
    "rankings_from_matrix",
]


def plackett_luce_available() -> bool:
    """Return True when Rscript and the PlackettLuce and qvcalc packages are present."""
    return packages_available(_R_PACKAGES)


def rankings_from_matrix(matrix: np.ndarray, polarity: str) -> np.ndarray:
    """Turn a method by dataset score matrix into a per-dataset ranking matrix.

    Each dataset (a column) becomes one ranking of the methods: rank 1 is the
    best method on that dataset, ties share a rank (competition ranking), and a
    method with a missing score is left out of that dataset's ranking, encoded
    as 0 in the PlackettLuce convention. "Best" is resolved through the metric
    polarity.

    Parameters
    ----------
    matrix
        Array of shape ``(n_methods, n_datasets)`` for one metric.
    polarity
        ``"higher_is_better"`` or ``"lower_is_better"``.

    Returns
    -------
    numpy.ndarray
        Integer array of shape ``(n_datasets, n_methods)`` with rank 1 for the
        best method, ties shared, and 0 for a method absent from that ranking.

    Raises
    ------
    ValueError
        If ``matrix`` is not 2D, has fewer than two methods, or ``polarity``
        is not recognised.
    """
    if polarity not in _POLARITIES:
        raise ValueError(f"polarity must be one of {_POLARITIES}; got {polarity!r}")
    matrix = np.asarray(matrix, dtype=float)
    if matrix.ndim != 2:
        raise ValueError(f"matrix must be 2D (methods by datasets); got shape {matrix.shape}")
    n_methods, n_datasets = matrix.shape
    if n_methods < 2:
        raise ValueError("need at least 2 methods to form a ranking")

    oriented = matrix if polarity == "higher_is_better" else -matrix
    rankings = np.zeros((n_datasets, n_methods), dtype=int)
    for d in range(n_datasets):
        column = oriented[:, d]
        observed = ~np.isnan(column)
        if observed.sum() < 2:
            continue  # a ranking needs at least two ranked items
        # Dense ranking: 1 for the best (largest), ties share a rank, no gaps,
        # the form PlackettLuce expects. rankdata gives 1 to the smallest, so
        # negate to put the best first.
        rankings[d, observed] = rankdata(-column[observed], method="dense").astype(int)
    return rankings


@dataclass(frozen=True)
class PlackettLuceReport:
    """Outcome of a Plackett-Luce fit on per-dataset method rankings.

    Attributes
    ----------
    method_names
        Method labels, the order the arrays are aligned to (the input order).
    worth
        Worth parameters summing to one, aligned with ``method_names``; the
        strongest method has the largest worth. NaN for a method that never
        appeared in a ranking.
    quasi_se
        Quasi-standard-error per method (qvcalc), aligned with
        ``method_names``. These allow a reference-free comparison of any two
        methods, unlike the model standard errors which are relative to a
        reference method.
    log_worth
        Log-worth (ability) per method, aligned with ``method_names``, on the
        scale the model is fit; the reference method is fixed at 0.
    n_rankings
        Number of dataset rankings the model was fit on (rankings with fewer
        than two ranked methods are dropped).
    connected
        True when the win-loss network is strongly connected, the condition
        for finite worth estimates without pseudo-rankings. The fit uses the
        package default pseudo-rankings, so it returns estimates either way,
        but a False here flags that the estimates lean on that prior.
    npseudo
        The number of pseudo-rankings added against a hypothetical item.
    loglik, df, aic
        Model fit statistics.
    warnings
        Warnings raised by PlackettLuce during the fit.
    """

    method_names: tuple[str, ...]
    worth: np.ndarray
    quasi_se: np.ndarray
    log_worth: np.ndarray
    n_rankings: int
    connected: bool
    npseudo: float
    loglik: float
    df: int
    aic: float
    warnings: tuple[str, ...]

    def ranking(self) -> list[str]:
        """Method names ordered by worth, strongest first."""
        order = np.argsort(-np.where(np.isnan(self.worth), -np.inf, self.worth))
        return [self.method_names[i] for i in order]

    def top_tool(self) -> str:
        """The method with the largest worth."""
        return self.ranking()[0]


def plackett_luce(
    matrix: np.ndarray,
    method_names: Sequence[str],
    polarity: str = "higher_is_better",
    npseudo: float = 0.5,
) -> PlackettLuceReport:
    """Fit a Plackett-Luce model on per-dataset rankings of the methods.

    Parameters
    ----------
    matrix
        Array of shape ``(n_methods, n_datasets)`` for one metric.
    method_names
        Length ``n_methods`` labels, the items being ranked.
    polarity
        ``"higher_is_better"`` or ``"lower_is_better"``, used to orient each
        dataset's ranking.
    npseudo
        Number of pseudo-rankings against a hypothetical item, the package
        device that keeps the worth estimates finite when the ranking network
        is weakly connected. The PlackettLuce default is 0.5; set 0 for the
        plain maximum-likelihood fit on a strongly connected design.

    Returns
    -------
    PlackettLuceReport

    Raises
    ------
    ValueError
        For shape, length, or polarity problems, or if fewer than two
        rankings survive.
    RNotAvailableError
        If the R toolchain with PlackettLuce is not available.
    RExecutionError
        If the R subprocess fails.
    """
    matrix = np.asarray(matrix, dtype=float)
    if matrix.ndim != 2:
        raise ValueError(f"matrix must be 2D (methods by datasets); got shape {matrix.shape}")
    n_methods = matrix.shape[0]
    if len(method_names) != n_methods:
        raise ValueError(
            f"method_names has {len(method_names)} entries but matrix has {n_methods} rows"
        )
    if npseudo < 0:
        raise ValueError(f"npseudo must be non-negative; got {npseudo}")

    rankings = rankings_from_matrix(matrix, polarity)
    keep = (rankings > 0).sum(axis=1) >= 2
    rankings = rankings[keep]
    if len(rankings) < 2:
        raise ValueError("need at least 2 datasets with two or more ranked methods")

    payload = {
        "objects": [str(m) for m in method_names],
        "rankings": rankings.tolist(),
        "npseudo": float(npseudo),
    }
    reply = run_rscript(_R_PACKAGE, _R_SCRIPT, payload, _R_PACKAGES, _FIT_TIMEOUT_SECONDS)

    return PlackettLuceReport(
        method_names=tuple(str(m) for m in method_names),
        worth=_nan_array(reply["worth"], n_methods),
        quasi_se=_nan_array(reply["quasi_se"], n_methods),
        log_worth=_nan_array(reply["log_worth"], n_methods),
        n_rankings=int(reply["n_rankings"]),
        connected=bool(reply["connected"]),
        npseudo=float(reply["npseudo"]),
        loglik=float(reply["loglik"]),
        df=int(reply["df"]),
        aic=float(reply["aic"]),
        warnings=tuple(reply["warnings"]) if reply["warnings"] else (),
    )


def _nan_array(values, n: int) -> np.ndarray:
    """Convert a JSON list (possibly with nulls) to a length-n float array with NaN."""
    if not isinstance(values, list):
        values = [values]
    out = np.array([np.nan if v is None else float(v) for v in values], dtype=float)
    return out if out.shape == (n,) else np.full(n, np.nan)
