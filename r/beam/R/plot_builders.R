#' Reusable ggplot2 builders for the native beam plots
#'
#' The plot kinds dispatched by [beam_plot] share a few shapes: a labelled
#' heatmap, a sorted horizontal bar chart, a stacked-share bar chart, and a rank
#' bump chart. These builders hold the common ggplot2 code so each kind only
#' reads the right fields off its report and picks a builder. They take plain R
#' vectors and matrices, not Python objects.
#'
#' @name plot_builders
#' @keywords internal
NULL

#' Labelled heatmap of a square or rectangular matrix
#'
#' @param values Numeric matrix.
#' @param rows,cols Row and column labels.
#' @param fill_label Legend title.
#' @param title Plot title.
#' @param limits Fill scale limits; `NULL` lets ggplot pick.
#' @param diverging When `TRUE`, centre the fill scale at the midpoint of
#'   `limits` with the diverging ramp; otherwise use the sequential score ramp.
#' @param digits Cell label digits; `NULL` draws no cell labels.
#' @return A ggplot object.
#' @keywords internal
.heatmap_plot <- function(values, rows, cols, fill_label, title = NULL,
                          limits = NULL, diverging = FALSE, digits = 2) {
  df <- expand.grid(row = factor(rows, levels = rev(rows)),
                    col = factor(cols, levels = cols))
  df$value <- as.vector(values)
  ramp <- if (diverging) .beam_ramp("diverging") else .beam_ramp("score")
  mid <- if (!is.null(limits)) mean(limits) else 0
  p <- ggplot2::ggplot(df, ggplot2::aes(.data$col, .data$row, fill = .data$value)) +
    ggplot2::geom_tile(colour = "white", linewidth = 0.4)
  if (!is.null(digits)) {
    p <- p + ggplot2::geom_text(
      ggplot2::aes(label = ifelse(is.na(.data$value), "",
                                  formatC(.data$value, format = "f", digits = digits))),
      size = 3, colour = "#222222"
    )
  }
  scale <- if (diverging) {
    ggplot2::scale_fill_gradient2(low = ramp[1], mid = ramp[ceiling(length(ramp) / 2)],
                                  high = ramp[length(ramp)], midpoint = mid,
                                  limits = limits, name = fill_label, na.value = "#dddddd")
  } else {
    ggplot2::scale_fill_gradientn(colours = ramp, limits = limits,
                                  name = fill_label, na.value = "#dddddd")
  }
  p <- p + scale +
    ggplot2::labs(x = NULL, y = NULL, title = title) +
    theme_beam() +
    ggplot2::theme(axis.text.x = ggplot2::element_text(angle = 45, hjust = 1),
                   panel.grid = ggplot2::element_blank())
  label_in <- 0.07 * max(nchar(rows))
  .sized(p, width = 2.4 + 0.55 * length(cols) + label_in,
         height = 1.5 + 0.42 * length(rows))
}

#' Sorted horizontal bar chart
#'
#' @param values Bar lengths.
#' @param labels Bar labels.
#' @param order Integer order to sort rows by (top first); defaults to value
#'   order, largest on top.
#' @param value_label x-axis title.
#' @param fill Bar fill colour, or a numeric vector to colour by.
#' @param fill_label Legend title when `fill` is numeric.
#' @param title Plot title.
#' @return A ggplot object.
#' @keywords internal
.bar_plot <- function(values, labels, order = NULL, value_label = "value",
                      fill = .beam_palette[1], fill_label = NULL, title = NULL) {
  if (is.null(order)) order <- order(values, decreasing = TRUE)
  labels <- factor(labels[order], levels = rev(labels[order]))
  df <- data.frame(label = labels, value = values[order])
  numeric_fill <- is.numeric(fill) && length(fill) == length(values)
  if (numeric_fill) df$fill <- fill[order]
  p <- ggplot2::ggplot(df, ggplot2::aes(.data$value, .data$label))
  if (numeric_fill) {
    p <- p + ggplot2::geom_col(ggplot2::aes(fill = .data$fill)) +
      ggplot2::scale_fill_gradientn(colours = .beam_ramp("score"), name = fill_label)
  } else {
    p <- p + ggplot2::geom_col(fill = fill)
  }
  p <- p + ggplot2::labs(x = value_label, y = NULL, title = title) + theme_beam()
  .sized(p, width = 5 + 0.06 * max(nchar(as.character(labels))),
         height = 1.4 + 0.34 * length(values))
}

#' Horizontal stacked-share bar chart, one stack per row
#'
#' @param shares Matrix of shares, rows are bars, columns are stack segments.
#' @param row_labels Bar labels.
#' @param seg_labels Segment labels for the legend.
#' @param order Integer order for the rows (top first).
#' @param annotation Optional per-row text drawn at the end of each bar.
#' @param value_label x-axis title.
#' @param title Plot title.
#' @return A ggplot object.
#' @keywords internal
.stacked_plot <- function(shares, row_labels, seg_labels, order = NULL,
                          annotation = NULL, value_label = "share", title = NULL) {
  if (is.null(order)) order <- seq_along(row_labels)
  row_labels <- row_labels[order]
  shares <- shares[order, , drop = FALSE]
  df <- expand.grid(row = factor(row_labels, levels = rev(row_labels)),
                    segment = factor(seg_labels, levels = seg_labels))
  df$share <- as.vector(shares)
  pal <- stats::setNames(.beam_palette[seq_along(seg_labels)], seg_labels)
  p <- ggplot2::ggplot(df, ggplot2::aes(.data$share, .data$row, fill = .data$segment)) +
    ggplot2::geom_col() +
    ggplot2::scale_fill_manual(values = pal, name = NULL) +
    ggplot2::labs(x = value_label, y = NULL, title = title) + theme_beam()
  if (!is.null(annotation)) {
    ann <- data.frame(row = factor(row_labels, levels = rev(row_labels)),
                      label = annotation[order], total = rowSums(shares))
    p <- p + ggplot2::geom_text(data = ann, inherit.aes = FALSE,
                                ggplot2::aes(x = .data$total, y = .data$row, label = .data$label),
                                hjust = -0.1, size = 3, colour = "#555555") +
      ggplot2::expand_limits(x = max(rowSums(shares)) * 1.18)
  }
  .sized(p, width = 6.5 + 0.05 * max(nchar(as.character(row_labels))),
         height = 1.4 + 0.34 * length(row_labels))
}

#' Rank bump (subway) chart across columns
#'
#' @param method_names Method labels, one line each.
#' @param columns Column labels along the x-axis.
#' @param ranks Matrix of ranks, methods by columns, rank 1 best.
#' @param title Plot title.
#' @param divider_after Optional column index to draw a dashed divider after,
#'   for example to set the reported columns apart from a consensus column.
#' @return A ggplot object.
#' @keywords internal
.bump_plot <- function(method_names, columns, ranks, title = NULL, divider_after = NULL) {
  n_col <- length(columns)
  df <- data.frame(
    method = rep(method_names, times = n_col),
    col = factor(rep(columns, each = length(method_names)), levels = columns),
    rank = as.vector(ranks)
  )
  ends <- df[df$col == columns[n_col], ]
  p <- ggplot2::ggplot(df, ggplot2::aes(.data$col, .data$rank, group = .data$method,
                                        colour = .data$method))
  if (!is.null(divider_after)) {
    p <- p + ggplot2::geom_vline(xintercept = divider_after + 0.5,
                                 linetype = "dashed", colour = "#999999")
  }
  p <- p +
    ggplot2::geom_line(linewidth = 1) +
    ggplot2::geom_point(size = 2.4) +
    ggplot2::geom_text(data = ends, ggplot2::aes(label = .data$method),
                       hjust = -0.15, size = 3) +
    ggplot2::scale_y_reverse(breaks = seq_len(max(ranks))) +
    ggplot2::scale_colour_manual(values = grDevices::colorRampPalette(.beam_palette)(length(method_names)),
                                 guide = "none") +
    ggplot2::expand_limits(x = n_col + 0.6) +
    ggplot2::labs(x = NULL, y = "rank (1 best)", title = title) +
    theme_beam() +
    ggplot2::theme(axis.text.x = ggplot2::element_text(angle = 20, hjust = 1))
  .sized(p, width = 3 + 1.15 * n_col + 0.06 * max(nchar(method_names)),
         height = 1.8 + 0.34 * length(method_names))
}
