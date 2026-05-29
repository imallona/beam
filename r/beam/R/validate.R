#' Validate a score CSV against the metric registry
#'
#' Loads the CSV, looks up each metric id in the bundled metric card registry,
#' and reports any unknown metric id or any scale-type/aggregation-method
#' incompatibility. This is the gate before running [beam_rank].
#'
#' @param path Path to the score CSV.
#' @param metrics Optional character vector restricting validation to a subset
#'   of metric columns. Default `NULL` validates every metric column in the CSV.
#' @param method The MCDA aggregation method that downstream code intends to
#'   call, used to check scale-type compatibility. One of `"saw"`, `"topsis"`,
#'   `"vikor"`, `"promethee_ii"`, `"comet"`. Default `"saw"`.
#'
#' @return A list with at least `ok` (logical), `errors` (character vector),
#'   and `metrics` (character vector of validated metric ids). On error,
#'   raises an R error rather than returning the structure quietly, so callers
#'   can wrap in `tryCatch` for diagnostics.
#'
#' @seealso [beam_rank], [beam_metric_show].
#'
#' @examplesIf reticulate::py_module_available("beam.mcda")
#' scores <- tempfile(fileext = ".csv")
#' write.csv(
#'   data.frame(tool = c("a", "b"), ari = c(0.8, 0.6), runtime = c(10, 5)),
#'   scores, row.names = FALSE
#' )
#' beam_validate(scores)
#'
#' @export
beam_validate <- function(path, metrics = NULL, method = "saw") {
  py <- .require_beam()
  scores <- py$load_scores(path)
  ctx <- reticulate::import("beam.mcda")
  ctx$registry_context(scores$metric_ids, method = method)
  list(
    ok = TRUE,
    errors = character(0),
    metrics = if (is.null(metrics)) unlist(scores$metric_ids) else metrics
  )
}
