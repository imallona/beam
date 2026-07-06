#' beam plotting theme and palette
#'
#' A clean ggplot2 theme shared by every native beam plot: light gridlines on
#' the value axis only, no panel border, a muted background, and the Paul Tol
#' bright palette for categorical fills so the figures read the same in print
#' and on screen. The native R figures replace the matplotlib ones the report
#' and the older R wrappers drew.
#'
#' @param base_size Base font size in points.
#' @return A ggplot2 theme object.
#' @keywords internal
theme_beam <- function(base_size = 11) {
  ggplot2::theme_minimal(base_size = base_size) +
    ggplot2::theme(
      panel.grid.minor = ggplot2::element_blank(),
      panel.grid.major.y = ggplot2::element_blank(),
      axis.ticks = ggplot2::element_line(colour = "#cccccc"),
      plot.title = ggplot2::element_text(face = "plain", size = base_size + 1),
      plot.title.position = "plot",
      legend.position = "right"
    )
}

# Paul Tol bright palette, colour-blind safe, used for categorical fills
# (metric groups, sensitivity factors). Shared with the funky heatmap.
.beam_palette <- c(
  "#4477aa", "#ee6677", "#228833", "#ccbb44", "#66ccee", "#aa3377", "#bbbbbb"
)

# The variance-attribution colours, shared by the rank-sensitivity bars, the
# variance-component highlight and the attribution progression: analyst choice
# is red, the data (dataset) is blue, the benchmarker is green, the residual or
# interaction is grey. Defined here so every plot that splits a ranking's
# variance by source uses the same colours.
.beam_source_colours <- c(
  analyst = "#ee6677", data = "#4477aa", benchmarker = "#228833", residual = "#bbbbbb"
)

#' The beam plotting theme
#'
#' The clean ggplot2 theme every native beam plot uses, exported so a figure that
#' composes beam panels with its own can match their look.
#'
#' @param base_size Base font size in points.
#' @return A ggplot2 theme object.
#' @seealso [beam_palette], [beam_plot].
#' @export
beam_theme <- function(base_size = 11) theme_beam(base_size)

#' The beam categorical palette
#'
#' The Paul Tol bright, colour-blind-safe palette beam uses for categorical
#' fills, exported so a figure can colour its own panels to match. With
#' `roles = TRUE` it instead returns the named variance-attribution colours
#' (analyst, data, benchmarker, residual) the sensitivity and attribution plots
#' use.
#'
#' @param roles When `TRUE`, return the named source-attribution colours instead
#'   of the categorical palette.
#' @return A character vector of hex colours.
#' @seealso [beam_theme].
#' @export
beam_palette <- function(roles = FALSE) {
  if (roles) .beam_source_colours else .beam_palette
}

# a diverging green-to-red ramp for "good to bad" robustness encodings and a
# sequential blue ramp for score magnitudes, returned as colour vectors for the
# ggplot2 gradient scales
.beam_ramp <- function(kind = c("score", "stability", "diverging"), n = 11) {
  kind <- match.arg(kind)
  stops <- switch(kind,
    score = c("#f7fbff", "#6baed6", "#08306b"),
    stability = c("#ee6677", "#ccbb44", "#228833"),
    diverging = c("#3b4cc0", "#f7f7f7", "#b40426")
  )
  grDevices::colorRampPalette(stops)(n)
}

#' Tag a figure with the size it should be saved at
#'
#' Each builder knows its own row and column counts, so it attaches the width
#' and height that keep the glyphs and labels legible. [.beam_save] reads them,
#' which keeps a three-bar chart and a fourteen-row heatmap at proportionate
#' sizes instead of stretching both onto one default canvas.
#'
#' @param plot A ggplot or patchwork object.
#' @param width,height Inches.
#' @return `plot` with the size attributes set.
#' @keywords internal
.sized <- function(plot, width, height) {
  attr(plot, "beam_width") <- width
  attr(plot, "beam_height") <- height
  plot
}

#' Save a ggplot or patchwork figure, the extension picks the format
#'
#' Writes at the size the builder tagged with [.sized], at a fixed resolution so
#' fonts read the same across figures. A `.png`, `.pdf` or `.svg` path all work.
#'
#' @param plot A ggplot or patchwork object.
#' @param path Output path; the extension picks the device.
#' @param width,height Inches; override the tagged size when given.
#' @param dpi Resolution for raster devices.
#' @param ... Forwarded to [ggplot2::ggsave].
#' @return `path`, invisibly.
#' @keywords internal
.beam_save <- function(plot, path, width = NULL, height = NULL, dpi = 140, ...) {
  width <- width %||% attr(plot, "beam_width") %||% 8
  height <- height %||% attr(plot, "beam_height") %||% 5
  ggplot2::ggsave(path, plot, width = width, height = height, dpi = dpi,
                  limitsize = FALSE, ...)
  invisible(path)
}

`%||%` <- function(a, b) if (is.null(a)) b else a

#' Stop unless a plotting package is installed
#'
#' Raises a clear install hint when a plot needs \pkg{ggplot2} or \pkg{patchwork}
#' and it is not present.
#' @keywords internal
.need <- function(pkg) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    stop(sprintf("package '%s' is needed for this plot; install it with install.packages('%s')",
                 pkg, pkg), call. = FALSE)
  }
  invisible(TRUE)
}
