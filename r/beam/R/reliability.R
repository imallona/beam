#' Internal-consistency reliability of a metric group
#'
#' Reports standardized Cronbach's alpha for each construct group of metrics,
#' the companion to [beam_metric_validity]. Validity asks whether a grouping is
#' the right split; reliability asks how consistently the metrics inside a group
#' measure one thing, following Cronbach (1951). Each method-by-dataset cell is
#' one observation. The function orients every metric to higher-is-better and
#' uses the same oriented Spearman correlations as the validity check, so the two
#' read together. Forwards to the Python `beam.mcda.metric_reliability`.
#'
#' @param scores A numeric matrix of shape (observations, metrics), or a 3D
#'   array (methods, datasets, metrics) which is reshaped so each
#'   method-by-dataset cell is one observation row. Missing cells are `NA` and
#'   handled pairwise.
#' @param polarity Character vector, one per metric column, each
#'   `"higher_is_better"` or `"lower_is_better"`. A `"target_value"` metric has
#'   no monotone quality direction; drop it before calling.
#' @param groups Character vector, one construct label per metric column.
#'   Metrics sharing a label are read together as one composite scale.
#' @param metric_ids Optional character vector of metric labels, used to name the
#'   alpha-if-dropped entries in the report. Default `NULL`.
#' @param alpha_threshold Alpha below which a group is reported as
#'   low-reliability. Default `0.7`, the conventional cutoff.
#' @param min_pairwise Minimum shared observations for a pair's correlation to be
#'   computed. Default `3`.
#'
#' @return The Python `MetricReliabilityReport`. Read its fields with `$`:
#'   `alpha_by_group`, `mean_inter_item_by_group`, `k_by_group`,
#'   `alpha_if_dropped`, `low_reliability_groups`, `n_observations`.
#'
#' @references Cronbach LJ. Coefficient alpha and the internal structure of
#'   tests. Psychometrika 1951, 16(3):297-334. \doi{10.1007/BF02310555}.
#'
#' @seealso [beam_metric_validity], [beam_metric_dimensionality].
#'
#' @examplesIf reticulate::py_module_available("beam.mcda")
#' set.seed(1)
#' factor <- rnorm(40)
#' scores <- cbind(
#'   factor + rnorm(40, 0, 0.2), factor + rnorm(40, 0, 0.2),
#'   factor + rnorm(40, 0, 0.2)
#' )
#' report <- beam_metric_reliability(
#'   scores,
#'   polarity = rep("higher_is_better", 3),
#'   groups = rep("bio", 3)
#' )
#' report$alpha_by_group$bio
#'
#' @export
beam_metric_reliability <- function(scores, polarity, groups, metric_ids = NULL,
                                    alpha_threshold = 0.7, min_pairwise = 3) {
  .require_beam()
  mcda <- reticulate::import("beam.mcda")
  mcda$metric_reliability(
    scores = scores,
    polarity = as.character(polarity),
    groups = as.character(groups),
    metric_ids = if (is.null(metric_ids)) NULL else as.character(metric_ids),
    alpha_threshold = alpha_threshold,
    min_pairwise = as.integer(min_pairwise)
  )
}
