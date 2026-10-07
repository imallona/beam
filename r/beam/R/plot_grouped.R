#' Per-method ranks from several series, as dots
#'
#' Draws the rank of each method under two or more series as one dot per series,
#' joined by a grey line, with rank 1 at the top. Built for a same-data
#' contrast, where the same methods are ranked by two pipelines and the length of
#' the line shows how far the two orders differ for each method.
#'
#' @param methods Method labels, one group of dots each.
#' @param series A named list of numeric vectors, each the per-method rank for
#'   one series; the names label the legend.
#' @param ylabel y-axis title.
#' @param title Optional plot title.
#' @param path Optional output path; when `NULL` the ggplot object is returned.
#'
#' @return Invisibly the output path when `path` is given, otherwise the ggplot.
#' @seealso [beam_rank_bump], [beam_plot].
#' @export
beam_rank_dots <- function(methods, series, ylabel = "mean rank (1 ranks first)",
                           title = NULL, path = NULL) {
  .need("ggplot2")
  methods <- as.character(methods)
  labels <- names(series)
  if (is.null(labels)) labels <- paste("series", seq_along(series))
  df <- do.call(rbind, Map(function(lab, vals) {
    data.frame(method = factor(methods, levels = methods), series = lab,
               value = as.numeric(vals), stringsAsFactors = FALSE)
  }, labels, series))
  df$series <- factor(df$series, levels = labels)
  span <- do.call(rbind, lapply(split(df, df$method), function(d) {
    data.frame(method = d$method[1], low = min(d$value), high = max(d$value))
  }))
  pal <- unname(c(.beam_source_colours[c("data", "analyst", "benchmarker")], "#aa3377"))
  pal <- rep(pal, length.out = length(labels))
  p <- ggplot2::ggplot(df, ggplot2::aes(.data$method, .data$value)) +
    ggplot2::geom_linerange(data = span, inherit.aes = FALSE,
                            ggplot2::aes(x = .data$method, ymin = .data$low, ymax = .data$high),
                            colour = "#bbbbbb", linewidth = 1) +
    ggplot2::geom_point(ggplot2::aes(colour = .data$series), size = 2.6) +
    ggplot2::scale_colour_manual(values = stats::setNames(pal, labels), name = NULL) +
    ggplot2::scale_y_reverse(breaks = seq_len(length(methods))) +
    ggplot2::expand_limits(y = c(1, length(methods))) +
    ggplot2::labs(x = NULL, y = ylabel, title = title) +
    theme_beam() +
    ggplot2::theme(axis.text.x = ggplot2::element_text(angle = 20, hjust = 1),
                   legend.position = "top")
  fig <- .sized(p, width = 3 + 0.7 * length(methods), height = 3.6)
  if (is.null(path)) return(fig)
  .beam_save(fig, path)
}
