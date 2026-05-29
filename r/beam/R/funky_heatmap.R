#' Draw the funky heatmap for a beam run result
#'
#' Builds the glyph-table benchmarking plot (methods as rows, metrics as
#' circles sized by the normalized score, plus a composite bar) augmented with
#' the rank-robustness panels beam derives from the run: a leave-one-dataset-out
#' rank span, a SMAA rank-acceptability bar, and an aggregation-consensus span
#' across the five aggregations. Model-worth intervals and Friedman-Nemenyi
#' cliques can be passed through `...` when the R heterogeneity models have been
#' fit. Forwards to the Python `beam.funky_heatmap_from_run`.
#'
#' @param result A `RunResult` returned by [beam_rank].
#' @param path Optional output path. When given, the figure is saved there (the
#'   extension picks the format, e.g. `.png` or `.pdf`) and the path is returned
#'   invisibly. When `NULL`, the matplotlib `Figure` object is returned.
#' @param ... Other keyword arguments forwarded to
#'   `beam.funky_heatmap_from_run` (e.g. `metric_groups`, `title`, `worth`,
#'   `worth_ci`, `cliques`, `show_smaa`, `show_aggregation_consensus`).
#'
#' @return Invisibly the output path when `path` is given, otherwise the
#'   matplotlib `Figure`.
#'
#' @seealso [beam_rank], [beam_report].
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
#' beam_funky_heatmap(result, tempfile(fileext = ".png"))
#'
#' @export
beam_funky_heatmap <- function(result, path = NULL, ...) {
  py <- .require_beam()
  fig <- py$funky_heatmap_from_run(result, ...)
  if (is.null(path)) {
    return(fig)
  }
  fig$savefig(path, bbox_inches = "tight")
  invisible(path)
}

#' Plot a beam run result as a funky heatmap
#'
#' S3 `plot` method for the object returned by [beam_rank]. A thin alias for
#' [beam_funky_heatmap], so `plot(result)` draws the glyph table with beam's
#' rank-robustness panels.
#'
#' @param x A `beam_run` object returned by [beam_rank].
#' @param path Optional output path, as in [beam_funky_heatmap]. When `NULL`,
#'   the matplotlib `Figure` is returned.
#' @param ... Other keyword arguments forwarded to [beam_funky_heatmap].
#'
#' @return Invisibly the output path when `path` is given, otherwise the
#'   matplotlib `Figure`.
#'
#' @seealso [beam_funky_heatmap].
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
#' plot(result, tempfile(fileext = ".png"))
#'
#' @exportS3Method base::plot
plot.beam_run <- function(x, path = NULL, ...) {
  beam_funky_heatmap(x, path = path, ...)
}
