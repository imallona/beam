#' rbeam: Benchmark Evaluation and Metrics (R Interface)
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
#' @importFrom ggplot2 .data
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
  .warn_reticulate_numpy()
  reticulate::import("beam")
}

# Guard against a known-bad pair: reticulate before 1.40 cannot convert numpy 2.x
# arrays and recurses until the C stack overflows, which crashes every plot that
# reads a score matrix. The check runs once per session and only warns, so a
# working setup has no cost.
.beam_state <- new.env(parent = emptyenv())

.warn_reticulate_numpy <- function() {
  if (isTRUE(.beam_state$pydeps_checked)) return(invisible())
  .beam_state$pydeps_checked <- TRUE
  if (utils::packageVersion("reticulate") >= "1.40") return(invisible())
  numpy_new <- tryCatch(
    reticulate::py_module_available("numpy") &&
      numeric_version(reticulate::import("numpy")$`__version__`) >= "2",
    error = function(e) FALSE
  )
  if (numpy_new) {
    warning(
      "reticulate ", utils::packageVersion("reticulate"), " with numpy 2.x ",
      "crashes when converting arrays (C stack overflow), which breaks the beam ",
      "plots. Upgrade reticulate to 1.40 or newer, or pin numpy below 2 in the ",
      "Python environment.",
      call. = FALSE
    )
  }
  invisible()
}
