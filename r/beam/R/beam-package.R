#' beam: Benchmark Evaluation and Metrics
#'
#' Thin R interface to the beam Python package. beam ships metric cards
#' (YAML, JSON Schema), a multi-criteria decision analysis pipeline with
#' sensitivity primitives, and method-dataset heterogeneity diagnostics.
#' This package exposes the canonical Python implementation via reticulate.
#'
#' @section Setup:
#' After installing the R package, run [install_beam_python()] once to install
#' the Python side into the active reticulate environment. After that, the
#' wrappers ([beam_rank], [beam_report], [beam_validate], [beam_run],
#' [beam_metric_show]) and the heterogeneity entry points work directly.
#'
#' @keywords internal
"_PACKAGE"

.beam <- NULL

.onLoad <- function(libname, pkgname) {
  if (reticulate::py_module_available("beam")) {
    .beam <<- reticulate::import("beam", delay_load = TRUE)
  }
  invisible(NULL)
}

.require_beam <- function() {
  if (!reticulate::py_module_available("beam")) {
    stop(
      "the beam Python package is not available in the active reticulate ",
      "environment. Run install_beam_python() to install it, or point ",
      "reticulate at an existing Python environment that has beam installed ",
      "(see reticulate::use_python or RETICULATE_PYTHON).",
      call. = FALSE
    )
  }
  reticulate::import("beam")
}
