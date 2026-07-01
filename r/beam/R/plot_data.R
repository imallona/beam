#' Convert a reticulate-wrapped numpy array or sequence to a plain R object
#'
#' `reticulate` already maps numpy arrays to R matrices and Python tuples to
#' lists; these helpers force the result to the atomic type the plot builders
#' expect, so a length-one tuple does not arrive as a list and a 1xN array does
#' not collapse to a vector unexpectedly.
#'
#' @param x A Python object reached through reticulate.
#' @return `.chr` a character vector, `.num` a numeric vector, `.mat` a numeric
#'   matrix.
#' @keywords internal
#' @name plot_data_coerce
.chr <- function(x) as.character(unlist(reticulate::py_to_r(x)))

#' @rdname plot_data_coerce
.num <- function(x) as.numeric(unlist(reticulate::py_to_r(x)))

#' @rdname plot_data_coerce
.mat <- function(x) {
  m <- reticulate::py_to_r(x)
  if (is.null(dim(m))) matrix(m, nrow = 1) else as.matrix(m)
}

#' Pull the glyph-table data out of a beam run result
#'
#' Reads the fields the funky heatmap and the score heatmap need: the method
#' and metric names, the card-resolved normalized score matrix oriented so
#' higher is better, the composite score, and the pooled ranks. The rows are
#' left in input order; the plot functions sort them.
#'
#' @param run A `beam_run` (a Python `RunResult`).
#' @param metric_groups Optional group label per metric, in `metric_ids` order;
#'   defaults to one group for every metric.
#' @return A list with `methods`, `metrics`, `groups`, `normalized`,
#'   `composite`, `ranks`.
#' @keywords internal
.glyph_data <- function(run, metric_groups = NULL) {
  res <- run$result
  metrics <- .chr(run$metric_ids)
  groups <- if (is.null(metric_groups)) rep("all", length(metrics)) else as.character(metric_groups)
  if (length(groups) != length(metrics)) {
    stop("metric_groups must have one entry per metric", call. = FALSE)
  }
  list(
    methods = .chr(run$tool_names),
    metrics = metrics,
    groups = groups,
    normalized = .mat(res$normalized),
    composite = .num(res$composite),
    ranks = .num(res$ranks)
  )
}

#' Per-method leave-one-dataset-out rank span, or NULL
#'
#' Returns the smallest and largest rank each method takes across the base run
#' and every leave-one-dataset-out run, the span the funky heatmap draws as a
#' bar from best to worst rank. `NULL` when the run carries no
#' leave-one-dataset-out report.
#' @keywords internal
.lodo_span <- function(run) {
  lodo <- run$leave_one_dataset_out
  if (is.null(lodo)) return(NULL)
  loo <- reticulate::py_to_r(lodo$leave_one_out)
  stacked <- rbind(.num(lodo$base$ranks),
                   do.call(rbind, lapply(loo, function(r) .num(r$ranks))))
  list(low = apply(stacked, 2, min), high = apply(stacked, 2, max))
}

#' Per-method SMAA rank-acceptability matrix, or NULL
#'
#' Entry `[a, k]` is the share of sampled weightings that rank method `a` at
#' rank `k`. Drawn as the funky heatmap's stacked acceptability bar. `NULL` when
#' the run carries no SMAA report.
#' @keywords internal
.smaa_matrix <- function(run) {
  sm <- run$smaa
  if (is.null(sm)) return(NULL)
  .mat(sm$rank_acceptability_index)
}

#' Per-method rank span across the aggregation rules, or NULL
#'
#' The smallest and largest rank each method takes across the five aggregations
#' at a fixed weighting, read off the aggregation-agreement report. `NULL` when
#' fewer than two aggregations run on the input.
#' @keywords internal
.aggregation_span <- function(run) {
  report <- tryCatch(.py_plot()$aggregation_agreement_report(run, missing = "available"),
                     error = function(e) NULL)
  if (is.null(report)) return(NULL)
  list(low = .num(report$rank_low), high = .num(report$rank_high))
}
