#' Rank methods on a benchmark score matrix
#'
#' Runs the full beam MCDA pipeline: load, normalize by metric card, weight,
#' aggregate, rank, and run the default sensitivity primitives on the same
#' normalization context. Returns a Python `RunResult` object holding the
#' ranking, the sensitivity reports, and the reproducibility manifest.
#'
#' This is the R interface to `beam.rank`. See the Python docstring for the
#' full contract; this wrapper forwards arguments unchanged.
#'
#' @param scores Path to a CSV, a `beam.Scores` object, or a 2D numeric matrix
#'   with column names equal to metric ids. A long-format tensor with a dataset
#'   column is supported too; see `beam.load_scores` in the Python docs.
#' @param weights One of `"equal"`, `"entropy"`, `"standard_deviation"`,
#'   `"critic"`, `"merec"`, `"ahp"`, or a numeric vector of length n_metrics.
#'   Default `"equal"`.
#' @param method One of `"saw"`, `"topsis"`, `"vikor"`, `"promethee_ii"`,
#'   `"comet"`. Default `"saw"`.
#' @param sensitivity Logical, default `TRUE`. Runs SMAA, leave-one-metric-out,
#'   smallest-weight-perturbation, and (for tensor inputs) leave-one-dataset-out.
#' @param missing One of `"error"`, `"available"`, `"worst"`, `"impute"`.
#'   Default `"error"` refuses any NaN with a named error. `"available"` is
#'   available-case SAW; `"worst"` treats a missing cell as the worst score;
#'   `"impute"` is a discouraged mean-imputation opt-in. See the Python
#'   docs/explanations/missing-data.md for the rationale.
#' @param seed Integer seed for SMAA. Default `NULL`.
#' @param ... Other keyword arguments forwarded to `beam.rank`.
#'
#' @return A Python `RunResult` object (use `result$ranking`, `result$top_tool`,
#'   `result$smaa`, `result$leave_one_metric_out`, `result$manifest`, etc.).
#'
#' @seealso [beam_report] to render the result to a self-contained HTML file.
#'
#' @examplesIf reticulate::py_module_available("beam.mcda")
#' scores <- tempfile(fileext = ".csv")
#' write.csv(
#'   data.frame(tool = c("a", "b", "c"),
#'              ari = c(0.81, 0.74, 0.69),
#'              runtime = c(42, 310, 88)),
#'   scores, row.names = FALSE
#' )
#' result <- beam_rank(scores, method = "topsis", sensitivity = FALSE)
#' print(result$top_tool)
#'
#' @export
beam_rank <- function(scores,
                      weights = "equal",
                      method = "saw",
                      sensitivity = TRUE,
                      missing = "error",
                      seed = NULL,
                      ...) {
  py <- .require_beam()
  result <- py$rank(
    scores,
    weights = weights,
    method = method,
    sensitivity = sensitivity,
    missing = missing,
    seed = seed,
    ...
  )
  class(result) <- c("beam_run", class(result))
  result
}
