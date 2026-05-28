#' Install the beam Python package
#'
#' Installs the beam Python package into the active reticulate environment.
#' Call this once after installing the R package, then the R wrappers work
#' directly.
#'
#' @param method One of `"auto"`, `"virtualenv"`, or `"conda"`, passed to
#'   [reticulate::py_install]. Default `"auto"`.
#' @param envname Name of the reticulate environment to install into. Default
#'   `NULL` uses the active environment.
#' @param version Version specifier passed to pip (e.g. `"beam>=0.1.3"`).
#'   Default installs the latest from PyPI; once the Python package is on PyPI,
#'   this resolves to a stable release.
#' @param ... Additional arguments forwarded to [reticulate::py_install].
#'
#' @return Invisibly `TRUE` on success.
#'
#' @examplesIf interactive()
#' install_beam_python()
#'
#' @export
install_beam_python <- function(method = c("auto", "virtualenv", "conda"),
                                 envname = NULL,
                                 version = "beam",
                                 ...) {
  method <- match.arg(method)
  reticulate::py_install(
    packages = version,
    method = method,
    envname = envname,
    pip = TRUE,
    ...
  )
  invisible(TRUE)
}

#' beam Python package version
#'
#' Returns the version string of the Python beam package the R wrappers
#' currently bind to. Useful for diagnostics.
#'
#' @return A character version string.
#'
#' @export
beam_version <- function() {
  py <- .require_beam()
  py$`__version__`
}
