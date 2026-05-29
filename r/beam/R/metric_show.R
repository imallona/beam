#' Print one metric card from the registry
#'
#' Reads the card by id from the bundled registry and pretty-prints its
#' identity, kind, semantics (scale type, polarity, range, allowed
#' transformations, target if any), comparability (recommended normalization
#' and cross-dataset aggregation), declared implementations, and ontology
#' mappings (where populated).
#'
#' @param metric_id Character. The metric id, e.g. `"ari"`, `"runtime"`,
#'   `"asw_label"`, `"calibration_slope"`.
#'
#' @return Invisibly, the parsed `MetricCard` dataclass.
#'
#' @seealso [beam_validate].
#'
#' @examplesIf reticulate::py_module_available("beam.cards")
#' beam_metric_show("ari")
#'
#' @export
beam_metric_show <- function(metric_id) {
  py <- .require_beam()
  cards <- reticulate::import("beam.cards")
  card <- cards$Registry()$get(metric_id)
  cat("id:       ", card$id, "\n", sep = "")
  cat("name:     ", card$name, "\n", sep = "")
  cat("version:  ", card$version, "\n", sep = "")
  cat("polarity: ", card$polarity, "\n", sep = "")
  cat("scale:    ", card$scale_type, "\n", sep = "")
  if (!is.null(card$range_lower) && !is.null(card$range_upper)) {
    cat("range:    ", card$range_lower, "to", card$range_upper, "\n")
  }
  invisible(card)
}
