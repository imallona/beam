#' How many factors a metric group carries
#'
#' Counts the factors in each construct group by principal component analysis of
#' the metric correlation matrix, the companion to [beam_metric_reliability].
#' Cronbach's alpha reads a group as one scale when it is high but cannot test
#' whether the group is a single factor; this check does, with parallel analysis
#' (Horn 1965), using Glorfeld's (1995) 95th-percentile cutoff over Horn's mean
#' rule. Each method-by-dataset cell is one observation, oriented to
#' higher-is-better and correlated with Spearman, the same engine the validity
#' and reliability checks use. Forwards to the Python
#' `beam.mcda.metric_dimensionality`.
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
#' @param metric_ids Optional character vector of metric labels carried into the
#'   report. Default `NULL`.
#' @param min_pairwise Minimum shared observations for a pair's correlation to be
#'   computed. Default `3`.
#' @param n_iter Number of random matrices parallel analysis averages over.
#'   Default `500`.
#' @param seed Seed for the parallel-analysis random draws, so the result
#'   reproduces. Default `0`.
#'
#' @return The Python `MetricDimensionalityReport`. Read its fields with `$`:
#'   `eigenvalues_by_group`, `pc1_explained_by_group`,
#'   `kaiser_components_by_group`, `parallel_components_by_group`, `k_by_group`,
#'   `unidimensional_groups`, `multidimensional_groups`, `undefined_groups`,
#'   `n_observations`.
#'
#' @references Horn JL. A rationale and test for the number of factors in factor
#'   analysis. Psychometrika 1965, 30(2):179-185. \doi{10.1007/BF02289447}.
#'   Glorfeld LW. An improvement on Horn's parallel analysis methodology for
#'   selecting the correct number of factors to retain. Educational and
#'   Psychological Measurement 1995, 55(3):377-393.
#'   \doi{10.1177/0013164495055003002}.
#'
#' @seealso [beam_metric_validity], [beam_metric_reliability].
#'
#' @examplesIf reticulate::py_module_available("beam.mcda")
#' set.seed(1)
#' factor <- rnorm(60)
#' scores <- cbind(
#'   factor + rnorm(60, 0, 0.2), factor + rnorm(60, 0, 0.2),
#'   factor + rnorm(60, 0, 0.2), factor + rnorm(60, 0, 0.2)
#' )
#' report <- beam_metric_dimensionality(
#'   scores,
#'   polarity = rep("higher_is_better", 4),
#'   groups = rep("bio", 4)
#' )
#' report$unidimensional_groups
#'
#' @export
beam_metric_dimensionality <- function(scores, polarity, groups, metric_ids = NULL,
                                       min_pairwise = 3, n_iter = 500, seed = 0) {
  .require_beam()
  mcda <- reticulate::import("beam.mcda")
  mcda$metric_dimensionality(
    scores = scores,
    polarity = as.character(polarity),
    groups = as.character(groups),
    metric_ids = if (is.null(metric_ids)) NULL else as.character(metric_ids),
    min_pairwise = as.integer(min_pairwise),
    n_iter = as.integer(n_iter),
    seed = as.integer(seed)
  )
}
