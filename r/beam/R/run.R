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
#' @examplesIf reticulate::py_module_available("beam")
#' beam_run("beam.yaml")
#'
#' @export
beam_run <- function(path) {
  py <- .require_beam()
  config <- reticulate::import("beam.config")
  invisible(config$run_config(path))
}
