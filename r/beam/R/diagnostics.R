#' Run the three metric-set diagnostics over one grouping
#'
#' Runs [beam_metric_validity], [beam_metric_reliability] and
#' [beam_metric_dimensionality] on one set of inputs and returns the three
#' reports together. The three rest on the same oriented Spearman correlations,
#' so this reads a grouping from every angle without repeating the call.
#' Validity is skipped (returned as `NULL`) when the grouping has a single
#' construct, since convergent and discriminant evidence need at least two.
#' Forwards to the Python `beam.mcda.metric_diagnostics`.
#'
#' @param scores A numeric matrix of shape (observations, metrics), or a 3D
#'   array (methods, datasets, metrics) which is reshaped so each
#'   method-by-dataset cell is one observation row. Missing cells are `NA` and
#'   handled pairwise.
#' @param polarity Character vector, one per metric column, each
#'   `"higher_is_better"` or `"lower_is_better"`.
#' @param groups Character vector, one construct label per metric column.
#' @param metric_ids Optional character vector of metric labels carried into each
#'   report. Default `NULL`.
#' @param min_pairwise Minimum shared observations for a pair's correlation,
#'   shared by all three diagnostics. Default `3`.
#' @param redundant_threshold Within-group correlation at or above which the
#'   validity check reports a pair as redundant. Default `0.9`.
#' @param alpha_threshold Alpha below which the reliability check flags a group.
#'   Default `0.7`.
#' @param n_iter Number of random matrices the dimensionality check averages
#'   parallel analysis over. Default `500`.
#' @param seed Seed for the parallel-analysis draws. Default `0`.
#'
#' @return The Python `MetricDiagnosticsReport`. Read its fields with `$`:
#'   `validity` (or `NULL`), `reliability`, `dimensionality`.
#'
#' @seealso [beam_metric_validity], [beam_metric_reliability],
#'   [beam_metric_dimensionality].
#'
#' @examplesIf reticulate::py_module_available("beam.mcda")
#' set.seed(1)
#' bio <- rnorm(60)
#' batch <- rnorm(60)
#' scores <- cbind(
#'   bio + rnorm(60, 0, 0.1), bio + rnorm(60, 0, 0.1),
#'   batch + rnorm(60, 0, 0.1), batch + rnorm(60, 0, 0.1)
#' )
#' report <- beam_metric_diagnostics(
#'   scores,
#'   polarity = rep("higher_is_better", 4),
#'   groups = c("bio", "bio", "batch", "batch")
#' )
#' report$validity$discriminant_ok
#'
#' @export
beam_metric_diagnostics <- function(scores, polarity, groups, metric_ids = NULL,
                                    min_pairwise = 3, redundant_threshold = 0.9,
                                    alpha_threshold = 0.7, n_iter = 500, seed = 0) {
  .require_beam()
  mcda <- reticulate::import("beam.mcda")
  mcda$metric_diagnostics(
    scores = scores,
    polarity = as.character(polarity),
    groups = as.character(groups),
    metric_ids = if (is.null(metric_ids)) NULL else as.character(metric_ids),
    min_pairwise = as.integer(min_pairwise),
    redundant_threshold = redundant_threshold,
    alpha_threshold = alpha_threshold,
    n_iter = as.integer(n_iter),
    seed = as.integer(seed)
  )
}
