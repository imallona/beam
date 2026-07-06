#' Draw the funky heatmap for a beam run result
#'
#' Draws the glyph table with beam's rank-robustness panels, all sharing one row
#' axis: methods as rows sorted best first, metrics as circles sized by the
#' card-resolved normalized score and coloured by group, and a composite bar.
#' beam adds the panels that test the row order: model worth with confidence
#' intervals (when passed), the leave-one-dataset-out rank span, the rank span
#' across the aggregation rules, and the SMAA rank-acceptability bar. Each panel
#' answers whether the order survives one reasonable change.
#'
#' @param result A `beam_run` returned by [beam_rank].
#' @param path Optional output path. When given, the figure is saved there (the
#'   extension picks the format) and the path is returned invisibly. When
#'   `NULL`, the patchwork plot object is returned.
#' @param metric_groups Optional group label per metric, in `metric_ids` order;
#'   colours the metric circles by group.
#' @param title Optional figure title.
#' @param worth Optional per-method model worth (Plackett-Luce, Bradley-Terry or
#'   mixed-effects), drawn as points.
#' @param worth_ci Optional per-method half-interval for the worth points.
#' @param worth_label Axis label for the worth panel.
#' @param show_lodo,show_smaa,show_aggregation Draw the leave-one-dataset-out
#'   span, the SMAA acceptability bar, and the aggregation rank span when the run
#'   carries them. Default `TRUE`.
#' @param cliques Optional list of method-name groups from a Friedman-Nemenyi
#'   test (for example `beam_critical_difference(...)$cliques` mapped to names).
#'   Each multi-member group is drawn as an indigo bracket to the left of the
#'   glyphs, joining the methods the test cannot separate.
#' @param ... Reserved for future panels.
#'
#' @return Invisibly the output path when `path` is given, otherwise the
#'   patchwork plot object.
#'
#' @seealso [beam_rank], [beam_plot].
#'
#' @examplesIf reticulate::py_module_available("beam.mcda") && requireNamespace("patchwork", quietly = TRUE)
#' scores <- tempfile(fileext = ".csv")
#' write.csv(
#'   data.frame(tool = c("a", "b", "c"),
#'              ari = c(0.81, 0.74, 0.69),
#'              runtime = c(42, 310, 88)),
#'   scores, row.names = FALSE
#' )
#' result <- beam_rank(scores, sensitivity = FALSE)
#' beam_funky_heatmap(result, tempfile(fileext = ".png"))
#'
#' @export
beam_funky_heatmap <- function(result, path = NULL, metric_groups = NULL,
                               title = NULL, worth = NULL, worth_ci = NULL,
                               worth_label = "model worth",
                               show_lodo = TRUE, show_smaa = TRUE,
                               show_aggregation = TRUE, cliques = NULL, ...) {
  .require_beam()
  .need("patchwork")
  d <- .glyph_data(result, metric_groups)
  order <- order(d$ranks)
  lodo <- if (show_lodo) .lodo_span(result) else NULL
  agg <- if (show_aggregation) .aggregation_span(result) else NULL
  smaa <- if (show_smaa) .smaa_matrix(result) else NULL
  fig <- .funky_figure(
    methods = d$methods[order],
    metrics = d$metrics,
    groups = d$groups,
    normalized = d$normalized[order, , drop = FALSE],
    composite = d$composite[order],
    ranks = d$ranks[order],
    worth = .reorder(worth, order), worth_ci = .reorder(worth_ci, order),
    worth_label = worth_label,
    lodo = .reorder_span(lodo, order),
    agg = .reorder_span(agg, order),
    smaa = if (is.null(smaa)) NULL else smaa[order, , drop = FALSE],
    cliques = .clique_name_list(cliques),
    title = title
  )
  if (is.null(path)) return(fig)
  .beam_save(fig, path)
}

.reorder <- function(x, order) if (is.null(x)) NULL else x[order]
.reorder_span <- function(s, order) {
  if (is.null(s)) NULL else list(low = s$low[order], high = s$high[order])
}

#' Draw a funky heatmap from a raw score matrix
#'
#' The matrix-level entry point behind [beam_funky_heatmap], for a glyph table
#' built outside the beam pipeline: a normalized score matrix, the method and
#' metric names, a composite score and the ranks that order the rows. The
#' cross-benchmark vignette uses it to draw one table per benchmark.
#'
#' @param normalized Numeric matrix, methods by metrics, oriented so higher is
#'   better.
#' @param method_names,metric_names Row and column labels.
#' @param composite Per-method overall score, drawn as the composite bar.
#' @param ranks Per-method ranks, 1 best, used to order the rows.
#' @param metric_groups Optional group label per metric for the circle colour.
#' @param title Optional figure title.
#' @param path Optional output path; when `NULL` the plot object is returned.
#'
#' @return Invisibly the output path when `path` is given, otherwise the
#'   patchwork plot object.
#'
#' @seealso [beam_funky_heatmap].
#' @export
beam_funky_table <- function(normalized, method_names, metric_names, composite,
                             ranks, metric_groups = NULL, title = NULL, path = NULL) {
  .need("patchwork")
  normalized <- as.matrix(normalized)
  groups <- if (is.null(metric_groups)) rep("all", ncol(normalized)) else as.character(metric_groups)
  order <- order(ranks)
  fig <- .funky_figure(
    methods = as.character(method_names)[order],
    metrics = as.character(metric_names),
    groups = groups,
    normalized = normalized[order, , drop = FALSE],
    composite = composite[order], ranks = ranks[order],
    worth = NULL, worth_ci = NULL, worth_label = "model worth",
    lodo = NULL, agg = NULL, smaa = NULL, cliques = NULL, title = title
  )
  if (is.null(path)) return(fig)
  .beam_save(fig, path)
}

# Cliques arrive as an R list of character vectors, a Python sequence of tuples,
# or NULL. Return an R list of character vectors, keeping only the groups with
# more than one member (a singleton draws no bracket).
.clique_name_list <- function(cliques) {
  if (is.null(cliques)) return(NULL)
  if (inherits(cliques, "python.builtin.object")) cliques <- reticulate::py_to_r(cliques)
  groups <- lapply(cliques, function(g) as.character(unlist(g)))
  groups <- Filter(function(g) length(g) > 1, groups)
  if (length(groups) == 0) NULL else groups
}

#' Bump chart of method ranks across columns
#'
#' Each method is a line connecting its rank in each column, rank 1 at the top.
#' The building block for ranks assembled outside a single run, such as reported
#' ranks across benchmarks next to a beam consensus.
#'
#' @param method_names One line per method.
#' @param columns Column labels along the x-axis.
#' @param ranks Numeric matrix, methods by columns, rank 1 best.
#' @param divider_after Optional column index to draw a dashed divider after.
#' @param title Optional plot title.
#' @param path Optional output path; when `NULL` the ggplot object is returned.
#'
#' @return Invisibly the output path when `path` is given, otherwise the ggplot.
#' @export
beam_rank_bump <- function(method_names, columns, ranks, divider_after = NULL,
                           title = NULL, path = NULL) {
  fig <- .bump_plot(as.character(method_names), as.character(columns),
                    as.matrix(ranks), title = title, divider_after = divider_after)
  if (is.null(path)) return(fig)
  .beam_save(fig, path)
}

#' Assemble the funky-heatmap panels into one aligned figure
#'
#' Builds each panel as a ggplot on a shared row axis (method position, best at
#' the top) and stitches them left to right with patchwork, so the rows line up
#' across the glyph grid, the composite bar and the robustness panels. Only the
#' panels with data are drawn.
#' @keywords internal
.funky_figure <- function(methods, metrics, groups, normalized, composite, ranks,
                          worth, worth_ci, worth_label, lodo, agg, smaa, title,
                          cliques = NULL) {
  n <- length(methods)
  pos <- rev(seq_len(n))  # row 1 (best) sits at the top
  ylim <- c(0.4, n + 0.6)

  panels <- list(.glyph_panel(methods, metrics, groups, normalized, pos, ylim, cliques))
  widths <- max(1.6, 0.75 * length(metrics))

  panels <- c(panels, list(.bar_panel(composite, pos, ylim, "overall\ncomposite")))
  widths <- c(widths, 1.0)

  if (!is.null(worth)) {
    panels <- c(panels, list(.worth_panel(worth, worth_ci, pos, ylim, worth_label)))
    widths <- c(widths, 1.6)
  }
  span_legend <- TRUE  # the span colour key is the same for every span panel
  if (!is.null(lodo)) {
    panels <- c(panels, list(.span_panel(lodo$low, lodo$high, ranks, n, pos, ylim,
                                         "rank span across\nleave-one-dataset-out", span_legend)))
    widths <- c(widths, 1.7)
    span_legend <- FALSE
  }
  if (!is.null(agg)) {
    panels <- c(panels, list(.span_panel(agg$low, agg$high, ranks, n, pos, ylim,
                                         "rank span across\naggregations", span_legend)))
    widths <- c(widths, 1.7)
  }
  if (!is.null(smaa)) {
    panels <- c(panels, list(.smaa_panel(smaa, pos, ylim)))
    widths <- c(widths, 2.2)
  }

  fig <- Reduce(`+`, panels) +
    patchwork::plot_layout(widths = widths, guides = "collect") &
    ggplot2::theme(legend.position = "bottom")
  if (!is.null(title)) fig <- fig + patchwork::plot_annotation(title = title)

  n_panels <- length(panels)
  .sized(fig,
         width = 2.0 + sum(widths) * 0.95 + 0.10 * max(nchar(methods)),
         height = 1.6 + 0.34 * n)
}

# each metric group gets a Paul Tol hue; one group falls back to a single colour
.group_colours <- function(groups) {
  levels <- unique(groups)
  stats::setNames(.beam_palette[(seq_along(levels) - 1) %% length(.beam_palette) + 1], levels)
}

# shared look for the non-glyph panels: no y axis, a small panel title from the
# x label, light vertical guides only
.panel_theme <- function() {
  theme_beam(base_size = 10) +
    ggplot2::theme(
      axis.title.y = ggplot2::element_blank(),
      axis.text.y = ggplot2::element_blank(),
      axis.ticks.y = ggplot2::element_blank(),
      axis.title.x = ggplot2::element_text(size = 8),
      panel.grid.major.x = ggplot2::element_line(colour = "#eeeeee")
    )
}

.glyph_panel <- function(methods, metrics, groups, normalized, pos, ylim, cliques = NULL) {
  m <- length(metrics)
  long <- expand.grid(mi = seq_len(m), ri = seq_along(methods))
  long$score <- as.vector(t(normalized))
  long$group <- groups[long$mi]
  long$y <- pos[long$ri]
  brackets <- .clique_brackets(cliques, methods, pos)
  xmin <- if (is.null(brackets)) 0.5 else min(brackets$segments$x) - 0.25
  p <- ggplot2::ggplot(long, ggplot2::aes(.data$mi, .data$y)) +
    ggplot2::geom_point(ggplot2::aes(size = .data$score, fill = .data$group),
                        shape = 21, colour = "#33333366", stroke = 0.3) +
    ggplot2::scale_size_area(max_size = 7, limits = c(0, 1), guide = "none") +
    ggplot2::scale_fill_manual(values = .group_colours(groups), name = NULL) +
    ggplot2::scale_x_continuous(breaks = seq_len(m), labels = metrics, position = "top") +
    ggplot2::scale_y_continuous(breaks = pos, labels = methods, expand = c(0, 0))
  if (!is.null(brackets)) {
    p <- p +
      ggplot2::geom_segment(data = brackets$segments, inherit.aes = FALSE,
                            ggplot2::aes(x = .data$x, xend = .data$x,
                                         y = .data$y, yend = .data$yend),
                            colour = "#332288", linewidth = 0.8) +
      ggplot2::geom_segment(data = brackets$ticks, inherit.aes = FALSE,
                            ggplot2::aes(x = .data$x, xend = .data$xend,
                                         y = .data$y, yend = .data$y),
                            colour = "#332288", linewidth = 0.8)
  }
  p +
    ggplot2::coord_cartesian(xlim = c(xmin, m + 0.5), ylim = ylim) +
    ggplot2::labs(x = NULL, y = NULL) +
    theme_beam(base_size = 10) +
    ggplot2::theme(
      axis.text.x.top = ggplot2::element_text(angle = 45, hjust = 0, size = 8),
      panel.grid = ggplot2::element_blank(),
      legend.position = "bottom"
    )
}

# Turn method-name cliques into the "[" bracket geometry drawn to the left of the
# glyph grid: one vertical segment per clique joining its top and bottom rows,
# with a short horizontal tick at each end. Successive brackets step further left.
.clique_brackets <- function(cliques, methods, pos) {
  if (is.null(cliques) || length(cliques) == 0) return(NULL)
  segs <- list()
  ticks <- list()
  slot <- 0
  for (g in cliques) {
    ys <- pos[match(g, methods)]
    ys <- ys[!is.na(ys)]
    if (length(ys) < 2) next
    x <- 0.30 - 0.42 * slot
    segs[[length(segs) + 1]] <- data.frame(x = x, y = min(ys), yend = max(ys))
    ticks[[length(ticks) + 1]] <- data.frame(x = x, xend = x + 0.16, y = c(min(ys), max(ys)))
    slot <- slot + 1
  }
  if (length(segs) == 0) return(NULL)
  list(segments = do.call(rbind, segs), ticks = do.call(rbind, ticks))
}

.bar_panel <- function(values, pos, ylim, xlab) {
  df <- data.frame(y = pos, value = values)
  ggplot2::ggplot(df, ggplot2::aes(.data$value, .data$y)) +
    ggplot2::geom_col(orientation = "y", width = 0.65, fill = "#888888") +
    ggplot2::scale_x_continuous(n.breaks = 3) +
    ggplot2::scale_y_continuous(expand = c(0, 0)) +
    ggplot2::coord_cartesian(ylim = ylim) +
    ggplot2::labs(x = xlab, y = NULL) + .panel_theme()
}

.worth_panel <- function(worth, ci, pos, ylim, xlab) {
  df <- data.frame(y = pos, worth = worth,
                   lo = worth - (ci %||% 0), hi = worth + (ci %||% 0))
  p <- ggplot2::ggplot(df, ggplot2::aes(.data$worth, .data$y))
  if (!is.null(ci)) {
    p <- p + ggplot2::geom_errorbarh(ggplot2::aes(xmin = .data$lo, xmax = .data$hi),
                                     height = 0.25, colour = "#88aacc")
  }
  p + ggplot2::geom_point(size = 2.4, colour = .beam_palette[1]) +
    ggplot2::scale_y_continuous(expand = c(0, 0)) +
    ggplot2::coord_cartesian(ylim = ylim) +
    ggplot2::labs(x = xlab, y = NULL) + .panel_theme()
}

# a coloured bar from the best to the worst rank a method takes, with a point at
# its pooled rank; green is a narrow span, red a wide one, rank 1 on the left
.span_panel <- function(low, high, pooled, n, pos, ylim, xlab, show_legend = TRUE) {
  span <- high - low
  cat <- cut(span, breaks = c(-Inf, 0.5, 2, Inf),
             labels = c("stable", "shifts", "unstable"))
  df <- data.frame(y = pos, low = low, high = high, pooled = pooled, span = cat)
  ggplot2::ggplot(df) +
    ggplot2::geom_segment(ggplot2::aes(x = .data$low, xend = .data$high,
                                       y = .data$y, yend = .data$y, colour = .data$span),
                          linewidth = 2, lineend = "round", show.legend = show_legend) +
    ggplot2::geom_point(ggplot2::aes(.data$pooled, .data$y), size = 1.6, colour = "#222222") +
    ggplot2::scale_colour_manual(
      values = c(stable = "#228833", shifts = "#ccbb44", unstable = "#ee6677"),
      drop = FALSE, name = "rank span") +
    ggplot2::scale_x_continuous(n.breaks = 4) +
    ggplot2::scale_y_continuous(expand = c(0, 0)) +
    ggplot2::coord_cartesian(xlim = c(0.5, n + 0.5), ylim = ylim) +
    ggplot2::labs(x = paste(xlab, "(1 is best)"), y = NULL) + .panel_theme()
}

# the share of sampled weightings that place a method at each rank, stacked and
# coloured by rank with rank 1 at the bright end
.smaa_panel <- function(acc, pos, ylim) {
  n_ranks <- ncol(acc)
  long <- expand.grid(ri = seq_len(nrow(acc)), rank = seq_len(n_ranks))
  long$share <- as.vector(acc)
  long$y <- pos[long$ri]
  long$brightness <- n_ranks - long$rank + 1
  ggplot2::ggplot(long, ggplot2::aes(.data$share, .data$y, group = .data$rank)) +
    ggplot2::geom_col(ggplot2::aes(fill = .data$brightness), orientation = "y", width = 0.75) +
    ggplot2::scale_fill_gradientn(colours = grDevices::hcl.colors(n_ranks, "viridis"),
                                  breaks = c(1, n_ranks), labels = c("worst", "1"),
                                  name = "rank") +
    ggplot2::scale_y_continuous(expand = c(0, 0)) +
    ggplot2::coord_cartesian(xlim = c(0, 1), ylim = ylim) +
    ggplot2::labs(x = "SMAA rank acceptability\n(share of weightings)", y = NULL) +
    .panel_theme()
}
