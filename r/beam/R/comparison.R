#' Friedman test and Nemenyi critical-difference diagram
#'
#' Runs the Friedman test and the Nemenyi post-hoc on a tool by dataset matrix
#' of one metric, returning the average ranks, the critical difference, and the
#' cliques of methods that are not separable (Demsar 2006). Forwards to the
#' Python `beam.mcda.critical_difference`.
#'
#' @param scores A numeric matrix of shape (tools, datasets), complete (no `NA`).
#'   For an incomplete matrix use [beam_skillings_mack].
#' @param higher_is_better Whether a higher score is better. Default `TRUE`.
#' @param alpha Significance level for the Nemenyi critical difference. Default
#'   `0.05`.
#' @param tool_names Optional character vector of tool labels. Default `NULL`.
#'
#' @return The Python `CriticalDifferenceReport`. Read its fields with `$`.
#'
#' @references Demsar J. Statistical comparisons of classifiers over multiple
#'   data sets. Journal of Machine Learning Research 2006, 7:1-30.
#'
#' @seealso [beam_skillings_mack].
#'
#' @export
beam_critical_difference <- function(scores, higher_is_better = TRUE, alpha = 0.05,
                                     tool_names = NULL) {
  .require_beam()
  mcda <- reticulate::import("beam.mcda")
  mcda$critical_difference(
    scores = scores,
    higher_is_better = higher_is_better,
    alpha = alpha,
    tool_names = if (is.null(tool_names)) NULL else as.character(tool_names)
  )
}

#' Coverage-aware Friedman test for incomplete designs (Skillings-Mack)
#'
#' Runs the Skillings-Mack (1981) generalization of the Friedman test on a tool
#' by dataset matrix that may have `NA`, returning the chi-squared statistic, the
#' degrees of freedom, the p-value, and the per-method standardized sums.
#' Forwards to the Python `beam.mcda.skillings_mack`. The Nemenyi post-hoc is not
#' generalized; restrict to the complete block and call [beam_critical_difference]
#' for pairwise cliques.
#'
#' @param scores A numeric matrix of shape (tools, datasets) that may contain
#'   `NA` for a tool not run on a dataset.
#' @param higher_is_better Whether a higher score is better. Default `TRUE`.
#' @param method_names Optional character vector of tool labels. Default `NULL`.
#'
#' @return The Python `SkillingsMackReport`. Read its fields with `$`.
#'
#' @references Skillings JH, Mack GA. On the use of a Friedman-type statistic in
#'   balanced and unbalanced block designs. Technometrics 1981, 23(2):171-177.
#'
#' @seealso [beam_critical_difference].
#'
#' @export
beam_skillings_mack <- function(scores, higher_is_better = TRUE, method_names = NULL) {
  .require_beam()
  mcda <- reticulate::import("beam.mcda")
  mcda$skillings_mack(
    scores = scores,
    higher_is_better = higher_is_better,
    method_names = if (is.null(method_names)) NULL else as.character(method_names)
  )
}

#' Coverage-aware critical difference (alias of Skillings-Mack)
#'
#' Alias for [beam_skillings_mack] under the critical-difference name, so a caller
#' that branched on a critical-difference result can swap the call on an
#' incomplete matrix. Forwards to the Python
#' `beam.mcda.coverage_aware_critical_difference` and returns the same
#' `SkillingsMackReport`.
#'
#' @inheritParams beam_skillings_mack
#'
#' @return The Python `SkillingsMackReport`. Read its fields with `$`.
#'
#' @seealso [beam_skillings_mack], [beam_critical_difference].
#'
#' @export
beam_coverage_aware_critical_difference <- function(scores, higher_is_better = TRUE,
                                                    method_names = NULL) {
  .require_beam()
  mcda <- reticulate::import("beam.mcda")
  mcda$coverage_aware_critical_difference(
    scores = scores,
    higher_is_better = higher_is_better,
    method_names = if (is.null(method_names)) NULL else as.character(method_names)
  )
}
