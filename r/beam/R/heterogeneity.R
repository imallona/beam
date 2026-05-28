#' Mixed-effects variance decomposition on benchmark scores
#'
#' Fits `score ~ method + (1 | dataset)` (plus a method-by-dataset random
#' effect when cells have replicates) in R's lme4 or glmmTMB via a one-shot
#' subprocess on the Python side. Returns the per-method marginal means,
#' the variance components, the dataset intraclass correlation, the
#' interaction-or-residual share, and the largest-residual outlier cells.
#'
#' The Python wrapper drives this through a one-shot R subprocess (see ADR
#' 0009 in the docs), so an R caller goes
#' R -> reticulate -> Python -> Rscript subprocess -> lme4.
#'
#' @param scores Numeric matrix or array of shape `(n_methods, n_datasets)`
#'   (one metric) or `(n_methods, n_datasets, n_metrics)`.
#' @param method_names,dataset_names Character vectors aligned with the score
#'   axes.
#' @param metric Character. The metric id whose scores feed the fit. Required
#'   when `scores` is a 3D tensor; ignored when 2D.
#' @param engine `"lmer"` (default) or `"glmmtmb"`.
#' @param family For `engine = "glmmtmb"`, one of `"beta"` (bounded in 0..1),
#'   `"gaussian"`, or `NULL` for auto-selection.
#' @param ... Other arguments forwarded to `beam.heterogeneity.mixed_effects`.
#'
#' @return A Python `MixedEffectsReport`.
#'
#' @seealso [beam_bradley_terry_tree], [beam_plackett_luce].
#'
#' @export
beam_mixed_effects <- function(scores,
                                method_names,
                                dataset_names,
                                metric = NULL,
                                engine = c("lmer", "glmmtmb"),
                                family = NULL,
                                ...) {
  engine <- match.arg(engine)
  py <- reticulate::import("beam.heterogeneity")
  py$mixed_effects(
    scores,
    method_names = method_names,
    dataset_names = dataset_names,
    metric = metric,
    engine = engine,
    family = family,
    ...
  )
}

#' Bradley-Terry tree on per-dataset paired method comparisons
#'
#' Wraps `beam.heterogeneity.bradley_terry_tree`, which in turn drives
#' psychotree::bttree through a one-shot R subprocess. The tree partitions
#' the datasets by their features so each leaf has its own Bradley-Terry
#' ranking of the methods. The report carries the splits with their
#' parameter-stability p-values, per-leaf worths, the leaf assignment per
#' dataset, the global flat ranking, and the reversed-leaves list (subgroups
#' where the pooled top method does not hold).
#'
#' @param scores Numeric matrix of shape `(n_methods, n_datasets)` on one
#'   metric.
#' @param method_names,dataset_names Character vectors aligned with the score
#'   axes.
#' @param features Named list of dataset-level feature vectors (numeric or
#'   character), each of length `n_datasets`, aligned with `dataset_names`.
#' @param higher_is_better Logical: whether higher scores are preferred.
#' @param ... Other arguments forwarded to `beam.heterogeneity.bradley_terry_tree`.
#'
#' @return A Python `BradleyTerryTreeReport`.
#'
#' @seealso [beam_plackett_luce].
#'
#' @export
beam_bradley_terry_tree <- function(scores,
                                     method_names,
                                     dataset_names,
                                     features,
                                     higher_is_better = TRUE,
                                     ...) {
  py <- reticulate::import("beam.heterogeneity")
  py$bradley_terry_tree(
    scores,
    method_names = method_names,
    dataset_names = dataset_names,
    features = features,
    higher_is_better = higher_is_better,
    ...
  )
}

#' Plackett-Luce model on per-dataset rankings of methods
#'
#' Generalisation of Bradley-Terry from pairwise wins to full orderings.
#' Wraps `beam.heterogeneity.plackett_luce`, which in turn drives R's
#' PlackettLuce through a one-shot subprocess. Returns a worth per method
#' summing to one, the log-worth, and reference-free quasi-standard-errors
#' from qvcalc.
#'
#' @param scores Numeric matrix of shape `(n_methods, n_datasets)` on one
#'   metric.
#' @param method_names,dataset_names Character vectors aligned with the score
#'   axes.
#' @param higher_is_better Logical.
#' @param ... Other arguments forwarded to `beam.heterogeneity.plackett_luce`.
#'
#' @return A Python `PlackettLuceReport`.
#'
#' @seealso [beam_bradley_terry_tree].
#'
#' @export
beam_plackett_luce <- function(scores,
                                method_names,
                                dataset_names,
                                higher_is_better = TRUE,
                                ...) {
  py <- reticulate::import("beam.heterogeneity")
  py$plackett_luce(
    scores,
    method_names = method_names,
    dataset_names = dataset_names,
    higher_is_better = higher_is_better,
    ...
  )
}

#' Cross-benchmark variance decomposition
#'
#' Fits `score ~ method + (1 | benchmark) + (1 | benchmark:dataset) +
#' (1 | method:benchmark)` in lme4, with dataset nested in benchmark since
#' benchmarks rarely share datasets. Reports the method-by-benchmark variance
#' share, the disagreement attributable to the benchmarker rather than the
#' method.
#'
#' @param methods,datasets,benchmarks,scores Parallel character or numeric
#'   vectors of equal length, one entry per (benchmark, dataset, method)
#'   observation.
#'
#' @return A Python `SourceVarianceReport`.
#'
#' @export
beam_source_variance_decomposition <- function(methods,
                                                 datasets,
                                                 benchmarks,
                                                 scores) {
  py <- reticulate::import("beam.heterogeneity")
  py$source_variance_decomposition(
    methods,
    datasets,
    benchmarks,
    scores
  )
}
