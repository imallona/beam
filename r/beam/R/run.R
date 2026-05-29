#' Run beam from a declarative beam.yaml
#'
#' Loads the yaml, resolves paths relative to the file, runs the full pipeline,
#' and writes the requested outputs (HTML report, manifest.json, normalized
#' scores CSV). The yaml is the artefact that travels with a publication; the
#' run is reproducible byte-for-byte where possible (the manifest documents
#' every input hash and software fingerprint).
#'
#' @param path Path to the `beam.yaml` configuration file.
#'
#' @return Invisibly, the Python `RunResult`.
#'
#' @seealso [beam_rank].
#'
#' @examplesIf reticulate::py_module_available("beam.config")
#' dir <- tempfile()
#' dir.create(dir)
#' write.csv(
#'   data.frame(tool = c("a", "b"), ari = c(0.8, 0.6), runtime = c(10, 5)),
#'   file.path(dir, "scores.csv"), row.names = FALSE
#' )
#' writeLines(c("inputs:", "  scores: scores.csv"), file.path(dir, "beam.yaml"))
#' beam_run(file.path(dir, "beam.yaml"))
#'
#' @export
beam_run <- function(path) {
  py <- .require_beam()
  config <- reticulate::import("beam.config")
  invisible(config$run_config(path))
}
