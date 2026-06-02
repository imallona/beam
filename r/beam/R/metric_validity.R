#' Convergent and discriminant validity of a metric set
#'
#' Tests whether metrics that claim to measure the same construct agree
#' (convergent validity) and metrics that claim to measure different constructs
#' do not (discriminant validity), following Campbell and Fiske (1959). Each
#' method-by-dataset cell is one observation. The function orients every metric
#' to higher-is-better, correlates every metric pair with Spearman over the
#' observations they share, and splits the correlations by the construct
#' grouping into within-group (convergent) and between-group (discriminant)
#' evidence. Forwards to the Python `beam.mcda.metric_validity`.
#'
#' @param scores A numeric matrix of shape (observations, metrics), or a 3D
#'   array (methods, datasets, metrics) which is reshaped so each
#'   method-by-dataset cell is one observation row. Missing cells are `NA` and
#'   handled pairwise.
#' @param polarity Character vector, one per metric column, each
#'   `"higher_is_better"` or `"lower_is_better"`. A `"target_value"` metric has
#'   no monotone quality direction; drop it before calling.
#' @param groups Character vector, one construct label per metric column.
#'   Metrics sharing a label claim to measure the same construct.
#' @param metric_ids Optional character vector of metric labels, used to name
#'   the flagged pairs and metrics in the report. Default `NULL`.
#' @param redundant_threshold Within-group correlation at or above which a pair
#'   is reported as redundant. Default `0.9`.
#' @param min_pairwise Minimum shared observations for a pair's correlation to
#'   be computed. Default `3`.
#'
#' @return The Python `MetricValidityReport`. Read its fields with `$`:
#'   `mean_convergent`, `mean_discriminant`, `discriminant_ok`,
#'   `convergent_by_group`, `correlation`, `coverage`, `redundant_pairs`,
#'   `crossloading_metrics`, `n_observations`.
#'
#' @references Campbell DT, Fiske DW. Convergent and discriminant validation by
#'   the multitrait-multimethod matrix. Psychological Bulletin 1959,
#'   56(2):81-105. \doi{10.1037/h0046016}.
#'
#' @seealso [beam_rank], [beam_validate].
#'
#' @examplesIf reticulate::py_module_available("beam.mcda")
#' set.seed(1)
#' bio <- rnorm(40)
#' batch <- rnorm(40)
#' scores <- cbind(
#'   bio + rnorm(40, 0, 0.1), bio + rnorm(40, 0, 0.1),
#'   batch + rnorm(40, 0, 0.1), batch + rnorm(40, 0, 0.1)
#' )
#' report <- beam_metric_validity(
#'   scores,
#'   polarity = rep("higher_is_better", 4),
#'   groups = c("bio", "bio", "batch", "batch")
#' )
#' report$discriminant_ok
#'
#' @export
beam_metric_validity <- function(scores, polarity, groups, metric_ids = NULL,
                                 redundant_threshold = 0.9, min_pairwise = 3) {
  .require_beam()
  mcda <- reticulate::import("beam.mcda")
  mcda$metric_validity(
    scores = scores,
    polarity = as.character(polarity),
    groups = as.character(groups),
    metric_ids = if (is.null(metric_ids)) NULL else as.character(metric_ids),
    redundant_threshold = redundant_threshold,
    min_pairwise = as.integer(min_pairwise)
  )
}
