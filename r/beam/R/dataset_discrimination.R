#' How strongly each dataset separates the methods it scores
#'
#' Measures, per dataset, how far apart the methods are pulled (the spread, an
#' effect size) and whether the metrics agree on the order (Kendall's W, a
#' consistency check). It needs no shared methods across benchmarks, so
#' benchmarks that run disjoint method sets can each be measured and then
#' compared. It is the dataset-level companion to [beam_dataset_concordance]:
#' concordance asks whether datasets agree on the order, this asks whether a
#' dataset produces an order at all. Forwards to the Python
#' `beam.mcda.dataset_discrimination`.
#'
#' @param scores A 3D array of shape (methods, datasets, metrics). A method or
#'   metric not observed on a dataset is `NA`; nothing is imputed. Pass one
#'   benchmark per call, since the min-max scaling is within the array.
#' @param polarity Character vector, one per metric, each `"higher_is_better"`
#'   or `"lower_is_better"`. Drop `"target_value"` metrics before calling.
#' @param dataset_ids Optional character vector of dataset labels. Default
#'   `NULL`.
#' @param min_methods Minimum methods in a dataset's complete method-by-metric
#'   block for Kendall's W to be computed. Default `3`.
#' @param alpha Significance level for the `significant` field. Default `0.05`.
#'
#' @return The Python `DatasetDiscriminationReport`. Read its fields with `$`:
#'   `spread`, `kendall_w`, `p_value`, `significant`, `pooled_score`, `order`,
#'   `mean_spread`, `mean_kendall_w`, `most_discriminating`,
#'   `least_discriminating`.
#'
#' @seealso [beam_dataset_concordance], [beam_difficulty_concordance].
#'
#' @examplesIf reticulate::py_module_available("beam.mcda")
#' scores <- array(c(0.1, 0.5, 0.9, 0.5, 0.5, 0.5), dim = c(3, 2, 1))
#' report <- beam_dataset_discrimination(
#'   scores,
#'   polarity = "higher_is_better",
#'   dataset_ids = c("spread", "tied")
#' )
#' report$most_discriminating
#'
#' @export
beam_dataset_discrimination <- function(scores, polarity, dataset_ids = NULL,
                                        min_methods = 3, alpha = 0.05) {
  .require_beam()
  mcda <- reticulate::import("beam.mcda")
  mcda$dataset_discrimination(
    scores = scores,
    polarity = as.list(as.character(polarity)),
    dataset_ids = if (is.null(dataset_ids)) NULL else as.list(as.character(dataset_ids)),
    min_methods = as.integer(min_methods),
    alpha = alpha
  )
}
