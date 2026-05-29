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

#' Install the R packages the heterogeneity diagnostics need
#'
#' The heterogeneity diagnostics (`beam_bradley_terry_tree`,
#' `beam_mixed_effects`, `beam_plackett_luce`,
#' `beam_source_variance_decomposition`) are fit by CRAN packages declared as
#' Suggests, so `install.packages("rbeam")` does not pull them in. Run this once
#' to install the ones you are missing.
#'
#' @param pkgs Character vector of package names to install. Default covers all
#'   four diagnostics.
#' @param ... Additional arguments forwarded to [utils::install.packages].
#'
#' @return Invisibly the names of the packages that were installed.
#'
#' @examplesIf interactive()
#' install_beam_heterogeneity_deps()
#'
#' @export
install_beam_heterogeneity_deps <- function(pkgs = c(
                                              "lme4", "glmmTMB", "psychotree",
                                              "partykit", "PlackettLuce", "qvcalc"
                                            ),
                                            ...) {
  missing <- pkgs[!vapply(pkgs, requireNamespace, logical(1), quietly = TRUE)]
  if (length(missing) == 0L) {
    message("all heterogeneity dependencies already installed")
    return(invisible(character(0)))
  }
  utils::install.packages(missing, ...)
  invisible(missing)
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
