"""Network meta-analysis over benchmark results.

When several benchmarks score an overlapping but not identical set of methods,
no single benchmark compares every pair of methods directly. A network
meta-analysis pools the direct and the indirect evidence into one coherent
ranking. Clinical research uses it to rank treatments that were never all tried
head to head in one trial. Here the treatments are the methods and the studies
are the (benchmark, dataset) blocks. The within-study effect of a method is its
mean rank over the metrics, with a standard error from the spread across them.

The standard error is the modeling choice to read honestly. Benchmarks publish
one score per method per dataset per metric, with no replicate runs, so there
is no sampling standard error in the usual sense. This wrapper takes the
variability across the metrics within a (benchmark, dataset) block as the
within-arm spread. That treats the metrics as repeated readings of the same
quantity, which they are not exactly: they measure related but distinct aspects
of integration quality. The pooled ranking is therefore a descriptive summary
of the evidence as published, not an inference back to a population of runs.
The mixed-effects ``source_variance_decomposition`` answers the complementary
question of how much of the spread is the benchmark rather than the method.

The model is fit by R's netmeta (built on meta) in a one-shot subprocess (ADR
0009), the same boundary as the rest of beam.heterogeneity. Use
``netmeta_available`` to check the R toolchain before calling
``network_meta_analysis``. Lower ranks are better, so the P-score treats small
values as desirable: a higher P-score is a better-ranked method.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from ._rsubprocess import RExecutionError, RNotAvailableError, packages_available, run_rscript

_R_PACKAGE = "beam.heterogeneity"
_R_SCRIPT = "network_meta.R"
_R_PACKAGES = ("netmeta", "meta", "jsonlite")
_FIT_TIMEOUT_SECONDS = 300

__all__ = [
    "NetworkMetaReport",
    "RExecutionError",
    "RNotAvailableError",
    "netmeta_available",
    "network_meta_analysis",
]


def netmeta_available() -> bool:
    """Return True if Rscript and the netmeta toolchain are callable."""
    return packages_available(_R_PACKAGES)


@dataclass(frozen=True)
class NetworkMetaReport:
    """Outcome of a network meta-analysis over benchmark results.

    Attributes
    ----------
    treatments
        Method labels in the order the effects and P-scores are reported.
    reference
        The reference treatment that the effects are expressed against.
    effect, effect_se, effect_lower, effect_upper
        Per-treatment pooled random-effects mean-rank difference relative to the
        reference, its standard error, and the 95 percent confidence interval.
        The reference treatment is 0 by construction. A negative effect means a
        better (lower) pooled rank than the reference.
    pscore
        Per-treatment P-score, the share of competing treatments a method beats
        averaged over the ranking uncertainty, in 0 to 1. Higher is better.
    tau, tau2, i2
        Between-study heterogeneity standard deviation, its square, and the I^2
        share of the total variation that is heterogeneity plus inconsistency.
    q_total, df_total, pval_total
        The total Q statistic for heterogeneity and inconsistency, its degrees
        of freedom, and its p-value.
    q_heterogeneity, df_heterogeneity, pval_heterogeneity
        The within-design part of Q (heterogeneity), where the design structure
        supports the split; nan otherwise.
    q_inconsistency, df_inconsistency, pval_inconsistency
        The between-design part of Q (inconsistency), where the design structure
        supports the split; nan otherwise.
    n_studies, n_treatments, n_comparisons
        Counts of studies, treatments and pairwise comparisons in the network.
    sm
        The summary measure, "MD" for the mean-rank difference.
    warnings
        Any warnings raised by netmeta during the fit.
    """

    treatments: tuple[str, ...]
    reference: str
    effect: np.ndarray
    effect_se: np.ndarray
    effect_lower: np.ndarray
    effect_upper: np.ndarray
    pscore: np.ndarray
    tau: float
    tau2: float
    i2: float
    q_total: float
    df_total: float
    pval_total: float
    q_heterogeneity: float
    df_heterogeneity: float
    pval_heterogeneity: float
    q_inconsistency: float
    df_inconsistency: float
    pval_inconsistency: float
    n_studies: int
    n_treatments: int
    n_comparisons: int
    sm: str
    warnings: tuple[str, ...]

    def ranking(self) -> list[str]:
        """Treatments ordered best to worst by P-score (higher P-score first)."""
        order = np.argsort(-self.pscore)
        return [self.treatments[i] for i in order]

    def top_treatment(self) -> str:
        """The treatment with the highest P-score."""
        return self.treatments[int(np.argmax(self.pscore))]


def _as_float(value: object) -> float:
    return float("nan") if value is None else float(value)


def network_meta_analysis(
    treatment: Sequence[str],
    study: Sequence[str],
    mean: Sequence[float],
    sd: Sequence[float],
    n: Sequence[float],
    reference: str | None = None,
    sm: str = "MD",
) -> NetworkMetaReport:
    """Pool benchmark results into one coherent method ranking.

    Parameters
    ----------
    treatment, study, mean, sd, n
        Five parallel sequences, one entry per study arm: the method label, the
        study label (a (benchmark, dataset) block), the mean rank of the method
        over the metrics, the standard deviation of those ranks, and the number
        of metrics it rests on. Each study must contribute at least two arms.
        Arms with a NaN mean, sd or n are dropped.
    reference
        The reference treatment to express effects against. Defaults to
        netmeta's own choice (the first treatment) when None.
    sm
        The summary measure passed to netmeta; "MD" (mean difference) is the
        right choice for the mean-rank arms.

    Returns
    -------
    NetworkMetaReport

    Raises
    ------
    ValueError
        If the sequences differ in length, or fewer than two treatments or two
        studies remain after dropping incomplete arms.
    RNotAvailableError
        If the R toolchain with netmeta is not available.
    RExecutionError
        If the R subprocess fails.
    """
    treatment = [str(t) for t in treatment]
    study = [str(s) for s in study]
    mean_a = np.asarray(mean, dtype=float)
    sd_a = np.asarray(sd, dtype=float)
    n_a = np.asarray(n, dtype=float)
    if not (len(treatment) == len(study) == len(mean_a) == len(sd_a) == len(n_a)):
        raise ValueError(
            "treatment, study, mean, sd and n must have the same length; "
            f"got {len(treatment)}, {len(study)}, {len(mean_a)}, {len(sd_a)}, {len(n_a)}"
        )

    keep = ~(np.isnan(mean_a) | np.isnan(sd_a) | np.isnan(n_a))
    treatment = [t for t, k in zip(treatment, keep, strict=True) if k]
    study = [s for s, k in zip(study, keep, strict=True) if k]
    mean_a = mean_a[keep]
    sd_a = sd_a[keep]
    n_a = n_a[keep]

    if len(set(treatment)) < 2:
        raise ValueError("network meta-analysis needs at least two treatments")
    arms_per_study: dict[str, int] = {}
    for s in study:
        arms_per_study[s] = arms_per_study.get(s, 0) + 1
    connected = [s for s, c in arms_per_study.items() if c >= 2]
    if len(connected) < 2:
        raise ValueError("network meta-analysis needs at least two studies with two or more arms")
    if reference is not None and reference not in set(treatment):
        raise ValueError(f"reference {reference!r} is not among the treatments")

    payload: dict[str, object] = {
        "treatment": treatment,
        "study": study,
        "mean": mean_a.tolist(),
        "sd": sd_a.tolist(),
        "n": n_a.tolist(),
        "sm": sm,
    }
    if reference is not None:
        payload["reference"] = reference

    reply = run_rscript(_R_PACKAGE, _R_SCRIPT, payload, _R_PACKAGES, _FIT_TIMEOUT_SECONDS)

    treatments = tuple(str(t) for t in reply["treatments"])
    return NetworkMetaReport(
        treatments=treatments,
        reference=str(reply["reference"]),
        effect=np.asarray(reply["effect"], dtype=float),
        effect_se=np.asarray(reply["effect_se"], dtype=float),
        effect_lower=np.asarray(reply["effect_lower"], dtype=float),
        effect_upper=np.asarray(reply["effect_upper"], dtype=float),
        pscore=np.asarray(reply["pscore"], dtype=float),
        tau=_as_float(reply["tau"]),
        tau2=_as_float(reply["tau2"]),
        i2=_as_float(reply["i2"]),
        q_total=_as_float(reply["q_total"]),
        df_total=_as_float(reply["df_total"]),
        pval_total=_as_float(reply["pval_total"]),
        q_heterogeneity=_as_float(reply["q_heterogeneity"]),
        df_heterogeneity=_as_float(reply["df_heterogeneity"]),
        pval_heterogeneity=_as_float(reply["pval_heterogeneity"]),
        q_inconsistency=_as_float(reply["q_inconsistency"]),
        df_inconsistency=_as_float(reply["df_inconsistency"]),
        pval_inconsistency=_as_float(reply["pval_inconsistency"]),
        n_studies=int(reply["n_studies"]),
        n_treatments=int(reply["n_treatments"]),
        n_comparisons=int(reply["n_comparisons"]),
        sm=str(reply["sm"]),
        warnings=tuple(str(w) for w in (reply.get("warnings") or [])),
    )
