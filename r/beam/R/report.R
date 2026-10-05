#' Render a beam run result to a self-contained HTML report
#'
#' Writes one HTML file with the ranking, the normalization diagnostics, the
#' sensitivity outputs (SMAA, leave-one-out, perturbation, and
#' leave-one-dataset-out when there are datasets), a critical-difference
#' section for tensor inputs, and a recommendation paragraph. Figures are
#' embedded as base64 PNGs.
#'
#' @param result A `RunResult` returned by [beam_rank].
#' @param path Output HTML path.
#' @param ground_truth_tool Optional character: name of the documented top tool
#'   to outline in the ranking figure. The vignettes set it; a plain CSV has
#'   none.
#' @param ... Other keyword arguments forwarded to `beam.report`.
#'
#' @return Invisibly, the output path.
#'
#' @seealso [beam_rank].
#'
#' @examplesIf reticulate::py_module_available("beam.mcda")
#' scores <- tempfile(fileext = ".csv")
#' write.csv(
#'   data.frame(tool = c("a", "b", "c"),
#'              ari = c(0.81, 0.74, 0.69),
#'              runtime = c(42, 310, 88)),
#'   scores, row.names = FALSE
#' )
#' result <- beam_rank(scores, sensitivity = FALSE)
#' beam_report(result, tempfile(fileext = ".html"))
#'
#' @export
beam_report <- function(result, path, ground_truth_tool = NULL, ...) {
  py <- .require_beam()
  py$report(result, path, ground_truth_tool = ground_truth_tool, ...)
  invisible(path)
}
