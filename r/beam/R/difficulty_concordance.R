#' Whether method families find the same datasets hard
#'
#' Splits the methods into families (for example deep-learning versus classical)
#' and reads how hard each dataset is for each family, then correlates the
#' per-family difficulty profiles across the datasets with Spearman. A high
#' concordance means the families agree on which datasets are hard, so the
#' hardness is a property of the data; a low concordance means a dataset hard for
#' one family is not hard for another, so the hardness is a property of the
#' method family. It is the family-split companion to
#' [beam_dataset_discrimination]. Forwards to the Python
#' `beam.mcda.difficulty_concordance`.
#'
#' @param scores A 3D array of shape (methods, datasets, metrics). Missing cells
#'   are `NA` and handled available-case; nothing is imputed. Pass one benchmark
#'   per call, since the min-max scaling is within the array.
#' @param polarity Character vector, one per metric, each `"higher_is_better"`
#'   or `"lower_is_better"`. Drop `"target_value"` metrics before calling.
#' @param families Character vector, one family label per method. Methods sharing
#'   a label form one family; at least two distinct families are required.
#' @param dataset_ids Optional character vector of dataset labels. Default
#'   `NULL`.
#' @param min_pairwise Minimum datasets where two families both have a score for
#'   their concordance to be computed. Default `3`.
#'
#' @return The Python `DifficultyConcordanceReport`. Read its fields with `$`:
#'   `family_names`, `family_score`, `concordance`, `coverage`,
#'   `mean_pairwise_concordance`, `per_dataset_range`, `most_divergent_dataset`.
#'
#' @seealso [beam_dataset_discrimination], [beam_dataset_concordance].
#'
#' @examplesIf reticulate::py_module_available("beam.mcda")
#' base <- c(0.2, 0.4, 0.6, 0.8)
#' scores <- array(rep(base, each = 1, times = 4), dim = c(4, 4, 1))
#' report <- beam_difficulty_concordance(
#'   scores,
#'   polarity = "higher_is_better",
#'   families = c("A", "A", "B", "B")
#' )
#' report$mean_pairwise_concordance
#'
#' @export
beam_difficulty_concordance <- function(scores, polarity, families,
                                        dataset_ids = NULL, min_pairwise = 3) {
  .require_beam()
  mcda <- reticulate::import("beam.mcda")
  mcda$difficulty_concordance(
    scores = scores,
    polarity = as.list(as.character(polarity)),
    families = as.list(as.character(families)),
    dataset_ids = if (is.null(dataset_ids)) NULL else as.list(as.character(dataset_ids)),
    min_pairwise = as.integer(min_pairwise)
  )
}
