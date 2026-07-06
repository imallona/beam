#' Grouped mean-rank bars, one group of bars per method
#'
#' Draws the per-method rank for two or more series side by side, with the rank
#' axis reversed so rank 1 sits at the top. Built for a same-data contrast, where
#' the same methods are ranked by two pipelines and the grouped bars show where
#' the two orders agree and where they part.
#'
#' @param methods Method labels, one group of bars each.
#' @param series A named list of numeric vectors, each the per-method rank for
#'   one series; the names label the legend.
#' @param ylabel y-axis title.
#' @param title Optional plot title.
#' @param path Optional output path; when `NULL` the ggplot object is returned.
#'
#' @return Invisibly the output path when `path` is given, otherwise the ggplot.
#' @seealso [beam_rank_bump], [beam_plot].
#' @export
beam_rank_bars <- function(methods, series, ylabel = "mean rank (1 ranks first)",
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
  pal <- unname(c(.beam_source_colours[c("data", "analyst", "benchmarker")], "#aa3377"))
  pal <- rep(pal, length.out = length(labels))
  p <- ggplot2::ggplot(df, ggplot2::aes(.data$method, .data$value, fill = .data$series)) +
    ggplot2::geom_col(position = ggplot2::position_dodge(width = 0.8), width = 0.72) +
    ggplot2::scale_fill_manual(values = stats::setNames(pal, labels), name = NULL) +
    ggplot2::scale_y_reverse() +
    ggplot2::labs(x = NULL, y = ylabel, title = title) +
    theme_beam() +
    ggplot2::theme(axis.text.x = ggplot2::element_text(angle = 20, hjust = 1),
                   legend.position = "top")
  fig <- .sized(p, width = 3 + 0.7 * length(methods), height = 3.6)
  if (is.null(path)) return(fig)
  .beam_save(fig, path)
}
