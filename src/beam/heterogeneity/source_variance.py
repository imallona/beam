"""Cross-benchmark variance decomposition.

When several benchmarks score overlapping methods, the question behind the
"benchmarks disagree" complaint is whether the disagreement comes from the
methods or from the benchmarks. This module fits a mixed-effects model with
the method as a fixed effect and the benchmark, the dataset within a
benchmark, and the method-by-benchmark interaction as random effects:

    score ~ method + (1 | benchmark) + (1 | benchmark:dataset)
                   + (1 | method:benchmark)

The method-by-benchmark variance is the headline number: it is how much a
method's standing changes depending on which benchmark evaluates it, that is,
how much of the spread is the benchmarker's choices rather than the method.
The benchmark and the benchmark:dataset components absorb how hard each
benchmark and each of its datasets is for every method alike. With one score
per method per dataset per benchmark, the method-by-dataset interaction cannot
be separated from measurement noise, so it falls into the residual; the
residual is therefore an upper bound on the genuine within-benchmark
heterogeneity. Datasets do not need to be shared across benchmarks: dataset is
nested in benchmark, so the model handles the usual case where each benchmark
brings its own datasets.

The model is fit by R's lme4 in a one-shot subprocess (ADR 0009), the same
boundary as the rest of beam.heterogeneity. Use ``r_available`` to check the R
toolchain before calling ``source_variance_decomposition``.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from ._rsubprocess import RExecutionError, RNotAvailableError, run_rscript
from .mixed_effects import _R_PACKAGES, r_available

_R_SCRIPT = "source_variance.R"
_FIT_TIMEOUT_SECONDS = 300

__all__ = [
    "RExecutionError",
    "RNotAvailableError",
    "SourceVarianceReport",
    "source_variance_decomposition",
]


@dataclass(frozen=True)
class SourceVarianceReport:
    """Outcome of a cross-benchmark variance decomposition.

    Attributes
    ----------
    method_names
        Method labels in the order the marginal means are reported.
    method_effects, method_effect_se
        Per-method marginal mean over benchmarks and datasets, and its
        standard error, aligned with ``method_names``.
    variance_components
        Map from grouping factor to variance: ``"benchmark"``,
        ``"benchmark:dataset"``, ``"method:benchmark"``, and ``"Residual"``.
    lrt_statistic, lrt_pvalue
        Per random term (``"benchmark"``, ``"benchmark:dataset"``,
        ``"method:benchmark"``), the restricted likelihood-ratio statistic for
        dropping that term and its boundary-corrected p-value. Testing whether a
        variance component is zero is a boundary problem, so the null is a 50:50
        mixture of a point mass at zero and a chi-square with one degree of
        freedom (Self and Liang 1987; Stram and Lee 1994) and the p-value is
        half the ordinary one-degree chi-square tail. A component estimated at
        zero gives a statistic of zero and the largest possible p-value, 0.5.
        Values are ``nan`` when the reduced model failed to fit. The residual is
        not a droppable term and is not tested.
    formula
        The R model formula that was fit.
    singular
        lme4's singular-fit flag. A singular fit usually means a variance
        component collapsed to zero, common when one component carries little
        of the variance.
    n_obs, n_methods, n_datasets, n_benchmarks
        Counts after dropping NaN scores.
    loglik, aic
        Model fit statistics.
    warnings
        Convergence or other warnings raised by lme4.
    """

    method_names: tuple[str, ...]
    method_effects: np.ndarray
    method_effect_se: np.ndarray
    variance_components: dict[str, float]
    lrt_statistic: dict[str, float]
    lrt_pvalue: dict[str, float]
    formula: str
    singular: bool
    n_obs: int
    n_methods: int
    n_datasets: int
    n_benchmarks: int
    loglik: float
    aic: float
    warnings: tuple[str, ...]

    @property
    def total_variance(self) -> float:
        """Sum of all variance components."""
        return float(sum(self.variance_components.values()))

    def _share(self, key: str) -> float:
        total = self.total_variance
        if total == 0.0:
            return float("nan")
        return self.variance_components.get(key, 0.0) / total

    @property
    def method_benchmark_share(self) -> float:
        """Share of the variance in the method-by-benchmark interaction.

        The headline number: the fraction of the spread that is a method
        ranking differently depending on which benchmark evaluates it, the
        disagreement attributable to the benchmarker's choices rather than the
        method.
        """
        return self._share("method:benchmark")

    @property
    def benchmark_share(self) -> float:
        """Share of the variance that is a pure between-benchmark shift."""
        return self._share("benchmark")

    @property
    def dataset_share(self) -> float:
        """Share of the variance in the dataset-within-benchmark shift."""
        return self._share("benchmark:dataset")

    @property
    def residual_share(self) -> float:
        """Share of the variance in the residual.

        With one observation per cell this is the method-by-dataset
        interaction confounded with measurement noise, so it is an upper bound
        on the genuine within-benchmark heterogeneity.
        """
        return self._share("Residual")


def _float_map(raw: dict | None) -> dict[str, float]:
    """Convert an R term-to-number map to floats, with R nulls becoming nan."""
    if not raw:
        return {}
    return {k: (float("nan") if v is None else float(v)) for k, v in raw.items()}


def source_variance_decomposition(
    methods: Sequence[str],
    datasets: Sequence[str],
    benchmarks: Sequence[str],
    scores: Sequence[float],
) -> SourceVarianceReport:
    """Decompose benchmark-score variance into method, benchmark, and interaction.

    Parameters
    ----------
    methods, datasets, benchmarks, scores
        Four parallel sequences, one entry per observation: the method label,
        the dataset label, the benchmark label, and the score on one metric.
        Rows with a NaN score are dropped. Pass scores from one metric (or one
        already-pooled composite) per call; do not mix metrics or polarities.

    Returns
    -------
    SourceVarianceReport

    Raises
    ------
    ValueError
        If the sequences differ in length, or fewer than two methods or two
        benchmarks remain after dropping NaN scores.
    RNotAvailableError
        If the R toolchain with lme4 is not available.
    RExecutionError
        If the R subprocess fails.
    """
    methods = [str(m) for m in methods]
    datasets = [str(d) for d in datasets]
    benchmarks = [str(b) for b in benchmarks]
    scores = np.asarray(scores, dtype=float)
    if not (len(methods) == len(datasets) == len(benchmarks) == len(scores)):
        raise ValueError(
            "methods, datasets, benchmarks and scores must have the same length; "
            f"got {len(methods)}, {len(datasets)}, {len(benchmarks)}, {len(scores)}"
        )

    keep = ~np.isnan(scores)
    methods = [m for m, k in zip(methods, keep, strict=True) if k]
    datasets = [d for d, k in zip(datasets, keep, strict=True) if k]
    benchmarks = [b for b, k in zip(benchmarks, keep, strict=True) if k]
    scores = scores[keep]

    if len(set(methods)) < 2:
        raise ValueError("need at least 2 distinct methods with a non-NaN score")
    if len(set(benchmarks)) < 2:
        raise ValueError("need at least 2 distinct benchmarks with a non-NaN score")

    payload = {
        "method": methods,
        "dataset": datasets,
        "benchmark": benchmarks,
        "score": scores.tolist(),
    }
    if not r_available():
        raise RNotAvailableError(
            "Rscript with the lme4 and jsonlite packages is required; "
            "check beam.heterogeneity.r_available()"
        )
    reply = run_rscript("beam.heterogeneity", _R_SCRIPT, payload, _R_PACKAGES, _FIT_TIMEOUT_SECONDS)

    return SourceVarianceReport(
        method_names=tuple(reply["method_levels"]),
        method_effects=np.asarray(reply["method_effect"], dtype=float),
        method_effect_se=np.asarray(reply["method_effect_se"], dtype=float),
        variance_components={k: float(v) for k, v in reply["variance_components"].items()},
        lrt_statistic=_float_map(reply["lrt_statistic"]),
        lrt_pvalue=_float_map(reply["lrt_pvalue"]),
        formula=reply["formula"],
        singular=bool(reply["singular"]),
        n_obs=int(reply["n_obs"]),
        n_methods=int(reply["n_methods"]),
        n_datasets=int(reply["n_datasets"]),
        n_benchmarks=int(reply["n_benchmarks"]),
        loglik=float(reply["loglik"]),
        aic=float(reply["aic"]),
        warnings=tuple(reply["warnings"]) if reply["warnings"] else (),
    )
