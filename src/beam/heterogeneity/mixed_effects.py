"""Mixed-effects variance decomposition on benchmark scores.

Following Eugster, Hothorn and Leisch (2008), benchmark results for one
metric are modelled as a mixed-effects model with the method as a fixed
effect and the dataset as a random effect:

    score ~ method + (1 | dataset)

The method fixed effects give a global ranking that adjusts for the fact
that some datasets are harder than others (a shift that lifts or lowers
every method). The variance components split the score variation into a
between-dataset part (the random dataset intercept) and a residual part.
With one observation per (method, dataset) cell the residual is the
method-by-dataset interaction confounded with measurement noise: the two
cannot be separated without replicates. When the input does carry
replicates (a multi-run benchmark, several runs of the same method on the
same dataset), the richer model

    score ~ method + (1 | dataset) + (1 | dataset:method)

fits the interaction as its own variance component, and its share of the
total is the formal answer to "how much of the apparent ranking is
dataset-dependent". This is the diagnostic counterpart to
``beam.mcda.leave_one_dataset_out``: the leave-one-out check asks whether
the pooled ranking hangs on any single dataset; this asks how much of the
score variance lives in the interaction at all.

The model is fit by R's lme4 in a one-shot subprocess (ADR 0009). The
``score`` values are taken as supplied for a single metric. Polarity does
not enter a variance decomposition, but scale does, so do not mix metrics:
pass one metric's scores per call. lme4 uses a Gaussian likelihood; for a
bounded metric this is an approximation, and glmmTMB with a beta family is
the documented future extension (PLAN Phase 4).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from ._rsubprocess import (
    RExecutionError,
    RNotAvailableError,
    packages_available,
    run_rscript,
)

_R_PACKAGE = "beam.heterogeneity"
_R_SCRIPT = "mixed_effects.R"
_R_PACKAGES = ("lme4", "jsonlite")
_FIT_TIMEOUT_SECONDS = 300

__all__ = [
    "MixedEffectsReport",
    "RExecutionError",
    "RNotAvailableError",
    "mixed_effects",
    "mixed_effects_from_matrix",
    "r_available",
]


def r_available() -> bool:
    """Return True when Rscript and the lme4 and jsonlite packages are present.

    Tests and vignettes use this to skip the analysis cleanly on a machine
    without the R toolchain.
    """
    return packages_available(_R_PACKAGES)


@dataclass(frozen=True)
class MixedEffectsReport:
    """Outcome of a mixed-effects variance decomposition on one metric.

    Attributes
    ----------
    method_names
        Method labels in the order the effect estimates are reported (the
        sorted factor levels lme4 used, not the input order).
    method_effects
        Estimated marginal mean per method over datasets, aligned with
        ``method_names``. Higher means a higher score on the metric as
        supplied, regardless of the metric's polarity.
    method_effect_se
        Standard error of each marginal mean, aligned with ``method_names``.
    variance_components
        Map from grouping factor to variance: ``"dataset"``, optionally
        ``"dataset:method"`` (only in the interaction model), and
        ``"Residual"``.
    residuals
        Per-observation residual, aligned with ``residual_methods`` and
        ``residual_datasets`` (the rows fed to the model, with NaN scores
        dropped).
    residual_methods, residual_datasets
        Method and dataset label per residual row.
    formula
        The R model formula that was fit.
    formula_kind
        ``"main"`` or ``"interaction"``, after resolving ``"auto"``.
    has_replicates
        True when at least one (dataset, method) cell held more than one
        observation, so the interaction model is identifiable.
    singular
        lme4's singular-fit flag. A singular fit usually means a variance
        component collapsed to its boundary (often zero) and the estimate
        should be read with caution.
    n_obs, n_methods, n_datasets
        Observation and factor-level counts after dropping NaN scores.
    loglik, aic
        Model fit statistics.
    warnings
        Convergence or other warnings raised by lme4 during the fit.
    """

    method_names: tuple[str, ...]
    method_effects: np.ndarray
    method_effect_se: np.ndarray
    variance_components: dict[str, float]
    residuals: np.ndarray
    residual_methods: tuple[str, ...]
    residual_datasets: tuple[str, ...]
    formula: str
    formula_kind: str
    has_replicates: bool
    singular: bool
    n_obs: int
    n_methods: int
    n_datasets: int
    loglik: float
    aic: float
    warnings: tuple[str, ...]
    engine: str = "lmer"
    scale: str = "response"

    @property
    def total_variance(self) -> float:
        """Sum of all variance components."""
        return float(sum(self.variance_components.values()))

    @property
    def icc_dataset(self) -> float:
        """Share of variance that is a pure between-dataset shift.

        The intraclass correlation for the dataset random intercept: the
        dataset variance over the total. A high value means most of the
        spread in scores is datasets being easier or harder for every
        method alike, not methods reordering across datasets.
        """
        total = self.total_variance
        if total == 0.0:
            return float("nan")
        return self.variance_components.get("dataset", 0.0) / total

    @property
    def interaction_share(self) -> float | None:
        """Share of variance in the method-by-dataset interaction.

        Only defined for the interaction model, which needs replicates.
        ``None`` for the main-effects model, where the interaction is
        confounded with the residual and cannot be separated; in that case
        read ``residual_share`` as an upper bound on the interaction.
        """
        if "dataset:method" not in self.variance_components:
            return None
        total = self.total_variance
        if total == 0.0:
            return float("nan")
        return self.variance_components["dataset:method"] / total

    @property
    def residual_share(self) -> float:
        """Share of the total in the observation-level term.

        In the lmer main-effects model this is the residual, the method-by-dataset
        interaction confounded with measurement noise, so it is an upper bound on
        the interaction. For a glmmTMB beta fit it is the dispersion term on the
        link scale, which is the beta precision rather than a Gaussian variance,
        so read it only as a rough share, not a variance ratio.
        """
        total = self.total_variance
        if total == 0.0:
            return float("nan")
        observation = self.variance_components.get(
            "Residual", self.variance_components.get("dispersion", 0.0)
        )
        return observation / total

    def top_outliers(self, k: int = 10) -> list[tuple[str, str, float]]:
        """Return the k (method, dataset, residual) cells with the largest absolute residual.

        These are the cells where a method departs most from what its global
        effect predicts on that dataset, the strongest single signals of
        method-by-dataset interaction.
        """
        order = np.argsort(-np.abs(self.residuals))[:k]
        return [
            (self.residual_methods[i], self.residual_datasets[i], float(self.residuals[i]))
            for i in order
        ]


_GLMMTMB_PACKAGES = ("glmmTMB", "jsonlite")


def glmmtmb_available() -> bool:
    """Return True when Rscript and the glmmTMB and jsonlite packages are present.

    Gate for the ``engine="glmmtmb"`` path, the way ``r_available`` gates the
    default lme4 path.
    """
    return packages_available(_GLMMTMB_PACKAGES)


def _run_r(payload: dict, engine: str) -> dict:
    """Invoke the R subprocess for the chosen engine and parse the JSON it prints."""
    packages = _GLMMTMB_PACKAGES if engine == "glmmtmb" else _R_PACKAGES
    return run_rscript(_R_PACKAGE, _R_SCRIPT, payload, packages, _FIT_TIMEOUT_SECONDS)


def mixed_effects(
    methods: Sequence[str],
    datasets: Sequence[str],
    scores: Sequence[float],
    formula_kind: str = "auto",
    engine: str = "lmer",
    family: str | None = None,
) -> MixedEffectsReport:
    """Fit a mixed-effects model on one metric's scores and decompose its variance.

    Parameters
    ----------
    methods, datasets, scores
        Three parallel sequences, one entry per observation: the method
        label, the dataset label, and the metric score. Rows with a NaN
        score are dropped before fitting. Several rows sharing a (method,
        dataset) pair are replicates and enable the interaction model.
    formula_kind
        ``"auto"`` (default) fits the interaction model when the input has
        replicates and the main-effects model otherwise. ``"main"`` forces
        ``score ~ method + (1 | dataset)``. ``"interaction"`` forces
        ``score ~ method + (1 | dataset) + (1 | dataset:method)``, which is
        only identifiable with replicates and otherwise yields a singular
        fit.
    engine
        ``"lmer"`` (default) fits a Gaussian linear mixed model in lme4.
        ``"glmmtmb"`` fits the same structure in glmmTMB, which allows a
        non-Gaussian ``family`` for a bounded metric. The variance components
        and marginal means it reports are then on the model's link scale, not
        the response scale, so they are not directly comparable to the lmer
        numbers; the method ordering is comparable.
    family
        Only used when ``engine="glmmtmb"``. ``None`` (default) resolves to
        ``"beta"`` when every score lies strictly in (0, 1) and ``"gaussian"``
        otherwise. Pass ``"beta"`` or ``"gaussian"`` to force one. The beta
        family models a metric bounded in (0, 1) such as ARI; scores exactly
        at 0 or 1 are squeezed inside the open interval before the fit.

    Returns
    -------
    MixedEffectsReport
        With ``engine`` set to the engine used and ``scale`` set to
        ``"response"`` for the Gaussian fits or ``"link"`` for a beta fit.

    Raises
    ------
    ValueError
        If the three sequences differ in length, fewer than two methods or
        two datasets remain after dropping NaN scores, or ``engine`` or
        ``family`` is not recognised.
    RNotAvailableError
        If the R toolchain for the chosen engine is not available.
    RExecutionError
        If the R subprocess fails.
    """
    if formula_kind not in ("auto", "main", "interaction"):
        raise ValueError(f"formula_kind must be auto, main or interaction; got {formula_kind!r}")
    if engine not in ("lmer", "glmmtmb"):
        raise ValueError(f"engine must be lmer or glmmtmb; got {engine!r}")
    if family is not None and family not in ("beta", "gaussian"):
        raise ValueError(f"family must be beta, gaussian or None; got {family!r}")
    if family is not None and engine != "glmmtmb":
        raise ValueError("family only applies to engine='glmmtmb'")
    methods = [str(m) for m in methods]
    datasets = [str(d) for d in datasets]
    scores = np.asarray(scores, dtype=float)
    if not (len(methods) == len(datasets) == len(scores)):
        raise ValueError(
            f"methods, datasets and scores must have the same length; got "
            f"{len(methods)}, {len(datasets)}, {len(scores)}"
        )

    keep = ~np.isnan(scores)
    methods = [m for m, k in zip(methods, keep, strict=True) if k]
    datasets = [d for d, k in zip(datasets, keep, strict=True) if k]
    scores = scores[keep]

    if len(set(methods)) < 2:
        raise ValueError("need at least 2 distinct methods with a non-NaN score")
    if len(set(datasets)) < 2:
        raise ValueError("need at least 2 distinct datasets with a non-NaN score")

    payload = {
        "method": methods,
        "dataset": datasets,
        "score": scores.tolist(),
        "formula_kind": formula_kind,
        "engine": engine,
        "family": family,
    }
    reply = _run_r(payload, engine)

    return MixedEffectsReport(
        method_names=tuple(reply["method_levels"]),
        method_effects=np.asarray(reply["method_effect"], dtype=float),
        method_effect_se=np.asarray(reply["method_effect_se"], dtype=float),
        variance_components={k: float(v) for k, v in reply["variance_components"].items()},
        residuals=np.asarray(reply["residuals"], dtype=float),
        residual_methods=tuple(methods),
        residual_datasets=tuple(datasets),
        formula=reply["formula"],
        formula_kind=reply["formula_kind"],
        has_replicates=bool(reply["has_replicates"]),
        singular=bool(reply["singular"]),
        n_obs=int(reply["n_obs"]),
        n_methods=int(reply["n_methods"]),
        n_datasets=int(reply["n_datasets"]),
        loglik=float(reply["loglik"]),
        aic=float(reply["aic"]),
        warnings=tuple(reply["warnings"]) if reply["warnings"] else (),
        engine=str(reply.get("engine", engine)),
        scale=str(reply.get("scale", "response")),
    )


def mixed_effects_from_matrix(
    matrix,
    method_names: Sequence[str],
    dataset_names: Sequence[str],
    formula_kind: str = "auto",
    engine: str = "lmer",
    family: str | None = None,
) -> MixedEffectsReport:
    """Fit the mixed-effects model from a method by dataset score matrix for one metric.

    Convenience wrapper that flattens a 2D matrix into the long-format
    sequences ``mixed_effects`` expects. NaN cells are carried through and
    dropped by ``mixed_effects``.

    Parameters
    ----------
    matrix
        Array-like of shape ``(n_methods, n_datasets)`` holding one metric's
        scores.
    method_names
        Length ``n_methods`` row labels.
    dataset_names
        Length ``n_datasets`` column labels.
    formula_kind
        Forwarded to ``mixed_effects``. A single matrix has one observation
        per cell, so only ``"auto"`` (resolving to main) or ``"main"`` are
        meaningful here.

    Returns
    -------
    MixedEffectsReport
    """
    matrix = np.asarray(matrix, dtype=float)
    if matrix.ndim != 2:
        raise ValueError(f"matrix must be 2D; got shape {matrix.shape}")
    n_methods, n_datasets = matrix.shape
    if len(method_names) != n_methods:
        raise ValueError(
            f"method_names has {len(method_names)} entries but matrix has {n_methods} rows"
        )
    if len(dataset_names) != n_datasets:
        raise ValueError(
            f"dataset_names has {len(dataset_names)} entries but matrix has {n_datasets} columns"
        )

    methods: list[str] = []
    datasets: list[str] = []
    scores: list[float] = []
    for mi in range(n_methods):
        for di in range(n_datasets):
            methods.append(str(method_names[mi]))
            datasets.append(str(dataset_names[di]))
            scores.append(float(matrix[mi, di]))
    return mixed_effects(
        methods, datasets, scores, formula_kind=formula_kind, engine=engine, family=family
    )
