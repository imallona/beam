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


#' Plot a beam run or analysis report natively in R
#'
#' Dispatches `kind` to a native ggplot2 builder and either returns the plot
#' object or saves it to a file. The figures are drawn in R with ggplot2, and
#' \pkg{patchwork} for the funky-heatmap panels, so they no longer depend on the
#' Python matplotlib code.
#'
#' Run-based kinds take a [beam_rank] result: `"ranking"`, `"normalized_scores"`,
#' `"smaa"`, `"dataset_stability"`, `"funky_heatmap"`, and the effect bump charts
#' `"weighting_effect"`, `"aggregation_effect"`, `"normalization_effect"` and
#' `"dataset_effect"`. Report-based kinds take the matching analysis report (or a
#' run, when the report can be derived from it): `"rank_sensitivity"`,
#' `"rank_sensitivity_by_tool"`, `"aggregation_agreement"`,
#' `"normalization_agreement"`, `"dataset_concordance"`, `"dataset_struggle"`,
#' `"dataset_discrimination"`, `"bayesian_comparison"`, `"pairwise_majority"` and
#' `"critical_difference"`.
#'
#' @param run A `beam_run` from [beam_rank], or an analysis report.
#' @param kind Character name of the plot.
#' @param path Optional output path. When given, the figure is saved there (the
#'   extension picks the format) and the path is returned invisibly. When
#'   `NULL`, the ggplot object is returned.
#' @param ... Other arguments forwarded to the chosen builder.
#'
#' @return Invisibly the output path when `path` is given, otherwise the ggplot
#'   object.
#'
#' @seealso [beam_funky_heatmap], [beam_rank].
#'
#' @examplesIf reticulate::py_module_available("beam.mcda") && requireNamespace("ggplot2", quietly = TRUE)
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
  .need("ggplot2")
  builder <- .beam_plot_kinds[[kind]]
  if (is.null(builder)) {
    stop(sprintf("unknown plot kind '%s'; see ?beam_plot for the list", kind), call. = FALSE)
  }
  fig <- builder(run, ...)
  if (is.null(path)) return(fig)
  .beam_save(fig, path)
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


#' Plot a beam run result as a funky heatmap
#'
#' S3 `plot` method for the object returned by [beam_rank]. A thin alias for
#' [beam_funky_heatmap], so `plot(result)` draws the glyph table with beam's
#' rank-robustness columns.
#'
#' @param x A `beam_run` object returned by [beam_rank].
#' @param path Optional output path, as in [beam_funky_heatmap].
#' @param ... Other keyword arguments forwarded to [beam_funky_heatmap].
#' @return Invisibly the output path when `path` is given, otherwise the figure.
#'
#' @exportS3Method base::plot
plot.beam_run <- function(x, path = NULL, ...) {
  beam_funky_heatmap(x, path = path, ...)
}


#' Plot a normalization-agreement report as a tau-b heatmap
#'
#' S3 `plot` method for [beam_normalization_agreement].
#'
#' @param x A `beam_normalization_agreement` object.
#' @param path Optional output path; when `NULL` the ggplot object is returned.
#' @param ... Ignored.
#' @return Invisibly the output path when `path` is given, otherwise the plot.
#'
#' @exportS3Method base::plot
plot.beam_normalization_agreement <- function(x, path = NULL, ...) {
  .plot_or_save(.k_normalization_agreement(x), path)
}


#' Plot an aggregation-agreement report as a tau-b heatmap
#'
#' S3 `plot` method for [beam_aggregation_agreement].
#'
#' @param x A `beam_aggregation_agreement` object.
#' @param path Optional output path; when `NULL` the ggplot object is returned.
#' @param ... Ignored.
#' @return Invisibly the output path when `path` is given, otherwise the plot.
#'
#' @exportS3Method base::plot
plot.beam_aggregation_agreement <- function(x, path = NULL, ...) {
  .plot_or_save(.k_aggregation_agreement(x), path)
}


.plot_or_save <- function(fig, path) {
  if (is.null(path)) return(fig)
  .beam_save(fig, path)
}
