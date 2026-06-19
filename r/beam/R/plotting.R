#' Attach a beam_report S3 class to a Python report object
#'
#' Prepends an S3 class to a reticulate Python object while keeping
#' `python.builtin.object` in the class chain, so `$` field access still works
#' and `print`/`plot` dispatch to the beam methods. Internal helper used by the
#' analysis wrappers.
#'
#' @param report A Python report object returned by a `beam.mcda` function.
#' @param subclass A single character class name, e.g.
#'   `"beam_normalization_agreement"`.
#' @return The same object with the classes prepended.
#' @keywords internal
.as_beam_report <- function(report, subclass) {
  class(report) <- c(subclass, "beam_report", class(report))
  report
}


#' Plot a beam run with the public plotting API
#'
#' Calls one of the `beam.plot` functions on a [beam_rank] result and either
#' returns the matplotlib `Figure` or saves it to a file. The figure code lives
#' in Python, so an R plot is the same one the HTML report embeds.
#'
#' The effect-dissection plots show how the ranking moves when one choice or the
#' data changes: `"weighting_effect"`, `"aggregation_effect"`,
#' `"normalization_effect"` and `"dataset_effect"`. The ranking and stability
#' plots are `"ranking"`, `"normalized_scores"`, `"smaa"`, `"dataset_stability"`
#' and `"funky_heatmap"`. The agreement heatmaps are `"aggregation_agreement"`,
#' `"normalization_agreement"` and `"dataset_concordance"`; `"dataset_struggle"`
#' maps each method's per-dataset rank against its own mean.
#'
#' Some plots take an analysis report in place of the run, passed as the first
#' argument. From [beam_rank_sensitivity]: `"rank_sensitivity"`, the share of
#' rank variance per factor pooled over the methods, and
#' `"rank_sensitivity_by_tool"`, the same split with one bar per method.
#'
#' @param run A `RunResult` returned by [beam_rank], or an analysis report for
#'   the report-based plot kinds.
#' @param kind Character name of the `beam.plot` function to call.
#' @param path Optional output path. When given, the figure is saved there (the
#'   extension picks the format) and the path is returned invisibly. When
#'   `NULL`, the matplotlib `Figure` is returned.
#' @param ... Other keyword arguments forwarded to the chosen plot function.
#'
#' @return Invisibly the output path when `path` is given, otherwise the
#'   matplotlib `Figure`.
#'
#' @seealso [beam_funky_heatmap], [beam_rank].
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
#' beam_plot(result, "ranking", tempfile(fileext = ".png"))
#'
#' @export
beam_plot <- function(run, kind, path = NULL, ...) {
  .require_beam()
  plot_mod <- reticulate::import("beam.plot")
  fn <- tryCatch(plot_mod[[kind]], error = function(e) NULL)
  if (is.null(fn) || !inherits(fn, "python.builtin.object")) {
    stop(sprintf("unknown plot kind '%s'; see ?beam_plot for the list", kind), call. = FALSE)
  }
  fig <- fn(run, ...)
  if (is.null(path)) {
    return(fig)
  }
  fig$savefig(path, bbox_inches = "tight")
  invisible(path)
}


#' Print a compact summary of a beam analysis report
#'
#' Shows the report class and, for the agreement reports, the number of
#' configurations compared, the mean pairwise Kendall tau-b, and whether the top
#' tool is unanimous. Read the full fields with `$`.
#'
#' @param x A `beam_report` object.
#' @param ... Ignored.
#' @return `x`, invisibly.
#'
#' @exportS3Method base::print
print.beam_report <- function(x, ...) {
  kind <- setdiff(class(x), c("beam_report", "python.builtin.object"))[1]
  cat(sprintf("<beam report: %s>\n", kind))
  if (reticulate::py_has_attr(x, "mean_pairwise_tau")) {
    labels <- if (reticulate::py_has_attr(x, "labels")) x$labels else x$methods
    cat(sprintf("  configurations compared: %d\n", length(labels)))
    tau <- x$mean_pairwise_tau
    cat(sprintf("  mean Kendall tau-b: %s\n", if (is.nan(tau)) "n/a" else sprintf("%.3f", tau)))
    cat(sprintf("  top tool unanimous: %s\n", if (isTRUE(x$top_is_unanimous)) "yes" else "no"))
  }
  invisible(x)
}


#' Plot a normalization-agreement report as a tau-b heatmap
#'
#' S3 `plot` method for [beam_normalization_agreement]. Delegates to the Python
#' `beam.plot.normalization_agreement`.
#'
#' @param x A `beam_normalization_agreement` object.
#' @param path Optional output path; when `NULL` the matplotlib `Figure` is
#'   returned.
#' @param ... Ignored.
#' @return Invisibly the output path when `path` is given, otherwise the `Figure`.
#'
#' @exportS3Method base::plot
plot.beam_normalization_agreement <- function(x, path = NULL, ...) {
  .plot_report(x, "normalization_agreement", path)
}


#' Plot an aggregation-agreement report as a tau-b heatmap
#'
#' S3 `plot` method for [beam_aggregation_agreement]. Delegates to the Python
#' `beam.plot.aggregation_agreement`.
#'
#' @param x A `beam_aggregation_agreement` object.
#' @param path Optional output path; when `NULL` the matplotlib `Figure` is
#'   returned.
#' @param ... Ignored.
#' @return Invisibly the output path when `path` is given, otherwise the `Figure`.
#'
#' @exportS3Method base::plot
plot.beam_aggregation_agreement <- function(x, path = NULL, ...) {
  .plot_report(x, "aggregation_agreement", path)
}


.plot_report <- function(report, kind, path) {
  .require_beam()
  plot_mod <- reticulate::import("beam.plot")
  fig <- plot_mod[[kind]](report)
  if (is.null(path)) {
    return(fig)
  }
  fig$savefig(path, bbox_inches = "tight")
  invisible(path)
}
