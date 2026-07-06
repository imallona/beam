#' Native builders for each beam_plot kind
#'
#' Each function reads the fields it needs off a run or report and hands plain R
#' vectors to a builder in [plot_builders]. [.beam_plot_kinds] is the registry
#' [beam_plot] dispatches on. Kept apart from the dispatch and the builders so a
#' new kind is one entry here.
#'
#' @name plot_kinds
#' @keywords internal
NULL

# Run-based kinds
.k_funky_heatmap <- function(run, ...) beam_funky_heatmap(run, ...)

.k_ranking <- function(run, ground_truth_tool = NULL) {
  d <- .glyph_data(run)
  ord <- order(d$ranks)
  p <- .bar_plot(d$composite, d$methods, order = ord, fill = .beam_palette[1],
                 value_label = "composite score", title = "ranking (rank 1 at top)")
  if (!is.null(ground_truth_tool) && ground_truth_tool %in% d$methods) {
    hit <- factor(ground_truth_tool, levels = rev(d$methods[ord]))
    p <- p + ggplot2::annotate("point", x = d$composite[d$methods == ground_truth_tool],
                               y = hit, shape = 21, size = 4, colour = "#ee6677",
                               fill = NA, stroke = 1.2)
  }
  p
}

.k_normalized_scores <- function(run) {
  d <- .glyph_data(run)
  ord <- order(d$ranks)
  .heatmap_plot(d$normalized[ord, , drop = FALSE], d$methods[ord], d$metrics,
                fill_label = "normalized\nscore", limits = c(0, 1),
                title = "normalized scores (tools by rank)")
}

.k_smaa <- function(run) {
  if (is.null(run$smaa)) {
    stop("this run has no SMAA report; run beam_rank with sensitivity = TRUE", call. = FALSE)
  }
  d <- .glyph_data(run)
  .bar_plot(.num(run$smaa$confidence_factor), d$methods, order = order(d$ranks),
            fill = .beam_palette[3],
            value_label = "share of weightings ranking the tool first",
            title = "SMAA confidence")
}

.k_dataset_stability <- function(run) {
  lodo <- run$leave_one_dataset_out
  if (is.null(lodo)) {
    stop("this run has no leave-one-dataset-out report; it needs a tensor input ",
         "with at least two datasets and sensitivity = TRUE", call. = FALSE)
  }
  d <- .glyph_data(run)
  .bar_plot(.num(lodo$rank_stability), d$methods, order = order(d$ranks),
            fill = .beam_palette[5], value_label = "rank stability (1 is steadiest)",
            title = "leave-one-dataset-out stability")
}

.k_dataset_effect <- function(run) {
  lodo <- run$leave_one_dataset_out
  if (is.null(lodo)) {
    stop("this run has no leave-one-dataset-out report; it needs a tensor input ",
         "with at least two datasets and sensitivity = TRUE", call. = FALSE)
  }
  methods <- .chr(run$tool_names)
  cols <- "all datasets"
  ranks <- list(.num(lodo$base$ranks))
  ev <- .num(lodo$evaluated_datasets)
  names_full <- if (reticulate::py_has_attr(lodo, "dataset_names") &&
                    !is.null(lodo$dataset_names)) .chr(lodo$dataset_names) else NULL
  loo <- reticulate::py_to_r(lodo$leave_one_out)
  for (idx in ev) {
    label <- if (!is.null(names_full)) names_full[idx + 1] else paste("dataset", idx)
    cols <- c(cols, paste("drop", label))
    ranks[[length(ranks) + 1]] <- .num(loo[[as.character(idx)]]$ranks)
  }
  .bump_plot(methods, cols, do.call(cbind, ranks),
             title = "leave-one-dataset-out effect on the ranking")
}

.k_aggregation_effect <- function(run, missing = "error") {
  rep <- .py_plot()$aggregation_agreement_report(run, missing = missing)
  methods <- .chr(rep$methods)
  ranks <- vapply(methods, function(m) .num(rep$ranks_by_method[[m]]),
                  numeric(length(.chr(run$tool_names))))
  .bump_plot(.chr(run$tool_names), methods, ranks,
             title = "aggregation effect on the ranking")
}

.k_normalization_effect <- function(run, missing = "error") {
  rep <- .py_plot()$normalization_agreement_report(run, missing = missing)
  labels <- .chr(rep$labels)
  ranks <- vapply(labels, function(l) .num(rep$ranks_by_label[[l]]),
                  numeric(length(.chr(run$tool_names))))
  .bump_plot(.chr(run$tool_names), labels, ranks,
             title = "normalization effect on the ranking")
}

.k_weighting_effect <- function(run, weightings = c("equal", "entropy", "std", "critic", "merec"),
                                missing = "error") {
  mcda <- reticulate::import("beam.mcda")
  ctx <- run$context
  ran <- character(0); rows <- list()
  for (scheme in weightings) {
    res <- tryCatch(
      mcda$run(run$matrix, ctx$polarity, weights = scheme, method = run$result$method,
               missing = missing, normalization = ctx$normalization, bounds = ctx$bounds,
               baselines = ctx$baselines, targets = ctx$targets),
      error = function(e) NULL)
    if (is.null(res)) next
    ran <- c(ran, scheme); rows[[length(rows) + 1]] <- .num(res$ranks)
  }
  if (length(rows) < 2) {
    stop("fewer than two weighting schemes produced a ranking on this input", call. = FALSE)
  }
  .bump_plot(.chr(run$tool_names), ran, do.call(cbind, rows),
             title = "weighting effect on the ranking")
}

# Report-based kinds

# One vertical bar per variance source, coloured by source: the analyst choices
# (weighting, aggregation) in red, the data (dataset) in blue, and the
# interaction in grey, so the bar colours show whether a choice or the data moves
# the ranking. Each bar is labelled with its share.
.k_rank_sensitivity <- function(report) {
  factors <- .chr(report$factors)
  shares <- vapply(factors, function(f) .num(report$factor_shares[[f]]), numeric(1))
  labels <- c(factors, "interaction")
  values <- c(shares, .num(report$interaction_share))
  keep <- is.finite(values)
  labels <- labels[keep]
  values <- values[keep]
  role <- ifelse(labels == "dataset", "data",
                 ifelse(labels == "interaction", "residual", "analyst"))
  df <- data.frame(factor = factor(labels, levels = labels), value = values,
                   fill = unname(.beam_source_colours[role]))
  p <- ggplot2::ggplot(df, ggplot2::aes(.data$factor, .data$value)) +
    ggplot2::geom_col(fill = df$fill) +
    ggplot2::geom_text(ggplot2::aes(label = formatC(.data$value, format = "f", digits = 3)),
                       vjust = -0.4, size = 3, colour = "#555555") +
    ggplot2::coord_cartesian(ylim = c(0, 1), clip = "off") +
    ggplot2::labs(x = NULL, y = "share of rank variance", title = "what moves the ranking") +
    theme_beam() +
    ggplot2::theme(axis.text.x = ggplot2::element_text(angle = 20, hjust = 1))
  .sized(p, width = max(3.5, 1.1 * length(labels) + 1.5), height = 3.6)
}

.k_rank_sensitivity_by_tool <- function(report, title = NULL) {
  factors <- .chr(report$factors)
  profiles <- report$per_tool
  if (inherits(profiles, "python.builtin.object")) {
    profiles <- reticulate::iterate(profiles, simplify = FALSE)
  }
  name_of <- function(p) {
    nm <- p$name
    if (is.null(nm)) paste("tool", .num(p$tool)) else as.character(nm)
  }
  labels <- vapply(profiles, name_of, character(1))
  spans <- vapply(profiles, function(p) .num(p$rank_span), numeric(1))
  shares <- t(vapply(profiles, function(p) {
    c(vapply(factors, function(f) .num(p$factor_shares[[f]]), numeric(1)),
      .num(p$interaction_share))
  }, numeric(length(factors) + 1)))
  ord <- order(-spans, labels)
  .stacked_plot(shares, labels, c(factors, "interaction"), order = ord,
                annotation = paste("span", spans),
                value_label = "share of rank variance",
                title = title %||% "what moves each method's rank")
}

.k_aggregation_agreement <- function(report) {
  if (!reticulate::py_has_attr(report, "tau_matrix")) {
    report <- .py_plot()$aggregation_agreement_report(report)
  }
  .tau_heatmap(report, .chr(report$methods), "aggregation")
}

.k_normalization_agreement <- function(report) {
  if (!reticulate::py_has_attr(report, "tau_matrix")) {
    report <- .py_plot()$normalization_agreement_report(report)
  }
  .tau_heatmap(report, .chr(report$labels), "normalization")
}

.k_dataset_concordance <- function(report) {
  report <- .concordance_report(report)
  .tau_heatmap(report, .concordance_labels(report), "dataset")
}

.k_dataset_struggle <- function(report) {
  report <- .concordance_report(report)
  dev <- .mat(report$rank_deviation)
  tools <- if (!is.null(report$tool_names)) .chr(report$tool_names) else
    paste0("tool_", seq_len(nrow(dev)))
  lim <- max(abs(dev), na.rm = TRUE)
  .heatmap_plot(dev, tools, .concordance_labels(report),
                fill_label = "rank minus\nmean rank", diverging = TRUE,
                limits = c(-lim, lim), digits = 1,
                title = "where each method places better or worse than usual")
}

.k_bayesian_comparison <- function(report) {
  prob <- .mat(report$probability_better)
  names <- if (!is.null(report$method_names)) .chr(report$method_names) else
    paste0("method_", seq_len(nrow(prob)))
  ord <- .num(report$order) + 1
  rope <- .num(report$rope)
  .heatmap_plot(prob[ord, ord, drop = FALSE], names[ord], names[ord],
                fill_label = "P(row better)", diverging = TRUE, limits = c(0, 1),
                title = sprintf("posterior P(row practically better than column), ROPE %g", rope))
}

.k_dataset_discrimination <- function(report, top = NULL) {
  ord <- .num(report$order) + 1
  spread <- .num(report$spread)
  w <- .num(report$kendall_w)
  ids <- if (!is.null(report$dataset_ids)) .chr(report$dataset_ids) else
    as.character(seq_along(spread))
  keep <- ord[is.finite(spread[ord])]
  if (!is.null(top)) keep <- utils::head(keep, top)
  .bar_plot(spread[keep], ids[keep], order = seq_along(keep), fill = w[keep],
            fill_label = "metric concordance\n(Kendall's W)",
            value_label = "discrimination (spread of method scores)",
            title = "how strongly each dataset separates the methods")
}

.k_pairwise_majority <- function(report) {
  dom <- .mat(report$dominance)
  names <- if (!is.null(report$method_names)) .chr(report$method_names) else
    paste0("method_", seq_len(nrow(dom)))
  ord <- if (!is.null(report$consistent_order)) .num(report$consistent_order) + 1 else
    order(rowSums(dom, na.rm = TRUE), decreasing = TRUE)
  .heatmap_plot(dom[ord, ord, drop = FALSE], names[ord], names[ord],
                fill_label = "row beats\ncolumn", limits = c(0, 1), digits = NULL,
                title = "pairwise majority relation")
}

.k_critical_difference <- function(report) {
  names <- if (!is.null(report$tool_names)) .chr(report$tool_names) else
    paste0("tool_", seq_along(.num(report$average_ranks)))
  ranks <- .num(report$average_ranks)
  cd <- .num(report$critical_difference)
  ord <- order(ranks)
  names_ord <- names[ord]
  row_of <- stats::setNames(seq_along(names_ord), names_ord)
  df <- data.frame(method = factor(names_ord, levels = rev(names_ord)),
                   rank = ranks[ord], y = seq_along(names_ord))
  # a bracket left of the points joins each clique the Nemenyi test cannot
  # separate, the rows whose average ranks lie within one critical difference
  cliques <- reticulate::py_to_r(report$cliques)
  brackets <- list()
  slot <- 0
  for (clique in cliques) {
    members <- row_of[as.character(.clique_names(clique, names))]
    members <- members[!is.na(members)]
    if (length(members) < 2) next
    x <- min(ranks) - 0.4 - 0.5 * slot
    brackets[[length(brackets) + 1]] <- data.frame(
      x = x, ymin = min(members), ymax = max(members))
    slot <- slot + 1
  }
  p <- ggplot2::ggplot(df, ggplot2::aes(.data$rank, .data$y)) +
    ggplot2::geom_point(size = 3, colour = .beam_palette[1]) +
    ggplot2::geom_text(ggplot2::aes(label = .data$method), hjust = -0.2, size = 3) +
    ggplot2::scale_y_reverse(breaks = NULL) +
    ggplot2::scale_x_reverse() +
    ggplot2::expand_limits(x = max(ranks) + 1) +
    ggplot2::labs(x = "average rank (1 best, on the right)", y = NULL,
                  title = sprintf("critical difference %.2f (Nemenyi)", cd)) +
    theme_beam()
  if (length(brackets) > 0) {
    seg <- do.call(rbind, brackets)
    p <- p + ggplot2::geom_segment(data = seg, inherit.aes = FALSE,
                                   ggplot2::aes(x = .data$x, xend = .data$x,
                                                y = .data$ymin, yend = .data$ymax),
                                   colour = "#332288", linewidth = 1.2)
  }
  .sized(p, width = 6.5, height = 1.6 + 0.34 * length(names))
}

# clique entries arrive as integer indices into the tool names or as names;
# normalize to names so the bracket lookup is the same either way
.clique_names <- function(clique, names) {
  vals <- unlist(clique)
  if (is.numeric(vals)) names[vals + 1] else as.character(vals)
}

.k_model_effects <- function(report, xlabel = NULL, title = NULL) {
  names <- .chr(report$method_names)
  eff <- .num(report$method_effects)
  se <- .num(report$method_effect_se)
  ord <- order(eff)
  df <- data.frame(method = factor(names[ord], levels = names[ord]),
                   eff = eff[ord], se = se[ord])
  p <- ggplot2::ggplot(df, ggplot2::aes(.data$eff, .data$method)) +
    ggplot2::geom_errorbarh(ggplot2::aes(xmin = .data$eff - .data$se, xmax = .data$eff + .data$se),
                            height = 0.25, colour = "#88aacc") +
    ggplot2::geom_point(size = 2.6, colour = .beam_palette[1]) +
    ggplot2::labs(x = xlabel %||% "marginal mean over datasets", y = NULL,
                  title = title %||% "method effects, largest first") +
    theme_beam()
  .sized(p, width = 6.5, height = 1.4 + 0.34 * length(names))
}

# Metric-quality kinds
.k_metric_correlation <- function(report, title = NULL) {
  corr <- .mat(report$correlation)
  n <- nrow(corr)
  labels <- if (!is.null(report$metric_ids)) .chr(report$metric_ids) else as.character(seq_len(n))
  groups <- .chr(report$groups)
  ord <- order(match(groups, unique(groups)), seq_along(groups))
  names_ord <- labels[ord]
  .heatmap_plot(corr[ord, ord, drop = FALSE], names_ord, names_ord,
                fill_label = "oriented\nSpearman", diverging = TRUE,
                limits = c(-1, 1), digits = NULL,
                title = title %||% "metric correlation, grouped by construct")
}

.k_metric_reliability_dropped <- function(report, alpha_threshold = 0.7, title = NULL) {
  entries <- reticulate::py_to_r(report$alpha_if_dropped)
  if (length(entries) == 0) {
    stop("no construct group with at least three metrics; alpha-if-dropped is undefined",
         call. = FALSE)
  }
  df <- do.call(rbind, lapply(entries, function(e) {
    data.frame(metric = as.character(e[[1]]), group = as.character(e[[2]]),
               alpha = as.numeric(e[[3]]), stringsAsFactors = FALSE)
  }))
  abg <- reticulate::py_to_r(report$alpha_by_group)
  ref <- data.frame(group = names(abg), group_alpha = as.numeric(unlist(abg)),
                    stringsAsFactors = FALSE)
  ref <- ref[ref$group %in% df$group & is.finite(ref$group_alpha), , drop = FALSE]
  p <- ggplot2::ggplot(df, ggplot2::aes(.data$metric, .data$alpha)) +
    ggplot2::geom_col(fill = .beam_palette[1]) +
    ggplot2::geom_hline(yintercept = alpha_threshold, colour = "#888888", linetype = "dotted")
  if (nrow(ref) > 0) {
    p <- p + ggplot2::geom_hline(data = ref, ggplot2::aes(yintercept = .data$group_alpha),
                                 colour = "#ee6677", linetype = "dashed", linewidth = 1)
  }
  p <- p +
    ggplot2::facet_wrap(~ group, scales = "free_x") +
    ggplot2::labs(x = NULL, y = "alpha if dropped",
                  title = title %||% "Cronbach's alpha if each metric is dropped") +
    theme_beam() +
    ggplot2::theme(axis.text.x = ggplot2::element_text(angle = 90, hjust = 1, vjust = 0.5))
  .sized(p, width = 2 + 1.7 * length(unique(df$group)) + 0.12 * nrow(df), height = 3.8)
}

.k_metric_dimensionality_scree <- function(report, title = NULL) {
  ev <- reticulate::py_to_r(report$eigenvalues_by_group)
  pc <- reticulate::py_to_r(report$parallel_components_by_group)
  df <- do.call(rbind, lapply(names(ev), function(g) {
    v <- as.numeric(unlist(ev[[g]]))
    data.frame(component = seq_along(v), eigenvalue = v,
               group = sprintf("%s (parallel analysis: %s)", g, pc[[g]]),
               stringsAsFactors = FALSE)
  }))
  colours <- grDevices::colorRampPalette(.beam_palette)(length(ev))
  p <- ggplot2::ggplot(df, ggplot2::aes(.data$component, .data$eigenvalue, colour = .data$group)) +
    ggplot2::geom_line(linewidth = 1) +
    ggplot2::geom_point(size = 2.4) +
    ggplot2::geom_hline(yintercept = 1, linetype = "dashed", colour = "#888888") +
    ggplot2::scale_x_continuous(breaks = seq_len(max(df$component))) +
    ggplot2::scale_colour_manual(values = colours, name = NULL) +
    ggplot2::labs(x = "component", y = "eigenvalue",
                  title = title %||% "scree plot per metric group (Kaiser cutoff at 1)") +
    theme_beam()
  .sized(p, width = 6, height = 3.8)
}

# Heterogeneity kinds
# `highlight` names one or more components to colour as the benchmarker (green),
# the disagreement that is a benchmarker choice rather than the method or the
# data; the rest are data (blue) and the residual grey. `annotation` adds a
# caption, for example how a highlighted share moves as sources are added.
.k_variance_components <- function(report, title = NULL, highlight = NULL, annotation = NULL) {
  vc <- reticulate::py_to_r(report$variance_components)
  names_ <- names(vc)
  vals <- as.numeric(unlist(vc))
  total <- sum(vals[is.finite(vals) & vals > 0])
  shares <- if (total > 0) vals / total else vals
  role <- ifelse(tolower(names_) %in% c("residual", "dispersion"), "residual",
                 ifelse(!is.null(highlight) & names_ %in% highlight, "benchmarker", "data"))
  df <- data.frame(component = factor(names_, levels = names_), share = shares, role = role)
  p <- ggplot2::ggplot(df, ggplot2::aes(.data$component, .data$share, fill = .data$role)) +
    ggplot2::geom_col(show.legend = FALSE) +
    ggplot2::scale_fill_manual(values = .beam_source_colours) +
    ggplot2::ylim(0, 1) +
    ggplot2::labs(x = "component", y = "share of variance",
                  title = title %||% "variance components", caption = annotation) +
    theme_beam() +
    ggplot2::theme(axis.text.x = ggplot2::element_text(angle = 20, hjust = 1))
  .sized(p, width = max(4, 1.1 * length(names_) + 1.5), height = 3.6)
}

.k_bradley_terry_leaves <- function(report, title = NULL) {
  ttl <- title %||% "Bradley-Terry tree leaves (method ranking first)"
  methods <- as.character(report$method_names)
  global_first <- methods[which.max(as.numeric(report$global_worth))]
  first_of <- function(worth) {
    w <- as.numeric(worth)
    if (length(w) == 0 || all(is.na(w))) global_first else methods[which.max(w)]
  }
  term <- Filter(function(n) isTRUE(n$terminal), report$nodes)
  if (length(term) == 0) {
    n_datasets <- length(as.character(report$dataset_names))
    return(.bar_plot(n_datasets, sprintf("all datasets: %s", global_first), order = 1,
                     fill = .beam_palette[3], value_label = "datasets in the leaf",
                     title = ttl))
  }
  sizes <- vapply(term, function(n) as.numeric(n$n), numeric(1))
  labels <- vapply(term, function(n) sprintf("leaf %d: %s", as.integer(n$id), first_of(n$worth)),
                   character(1))
  .bar_plot(sizes, labels, order = seq_along(sizes), fill = .beam_palette[3],
            value_label = "datasets in the leaf", title = ttl)
}

.k_difficulty_concordance <- function(report, title = NULL) {
  fams <- .chr(report$family_names)
  if (length(fams) != 2) {
    stop("the difficulty_concordance plot needs exactly two families", call. = FALSE)
  }
  fs <- .mat(report$family_score)
  xa <- fs[1, ]
  xb <- fs[2, ]
  keep <- is.finite(xa) & is.finite(xb)
  xa <- xa[keep]
  xb <- xb[keep]
  rho <- .mat(report$concordance)[1, 2]
  lims <- range(c(xa, xb))
  p <- ggplot2::ggplot(data.frame(a = xa, b = xb), ggplot2::aes(.data$a, .data$b)) +
    ggplot2::geom_abline(slope = 1, intercept = 0, linetype = "dashed", colour = "#888888") +
    ggplot2::geom_point(size = 2.6, alpha = 0.7, colour = .beam_palette[1]) +
    ggplot2::coord_equal(xlim = lims, ylim = lims) +
    ggplot2::labs(x = sprintf("%s score (higher = easier)", fams[1]),
                  y = sprintf("%s score (higher = easier)", fams[2]),
                  title = sprintf("%s\nSpearman %.2f",
                                  title %||% sprintf("do %s and %s find the same datasets hard?",
                                                     fams[1], fams[2]), rho)) +
    theme_beam()
  .sized(p, width = 5, height = 5)
}

.k_network_forest <- function(report, title = NULL) {
  treat <- .chr(report$treatments)
  eff <- .num(report$effect)
  lo <- .num(report$effect_lower)
  hi <- .num(report$effect_upper)
  ps <- .num(report$pscore)
  ref <- as.character(reticulate::py_to_r(report$reference))
  ord <- order(eff)
  df <- data.frame(method = factor(treat[ord], levels = rev(treat[ord])),
                   eff = eff[ord], lo = lo[ord], hi = hi[ord], ps = ps[ord])
  span <- max(hi) - min(lo)
  p <- ggplot2::ggplot(df, ggplot2::aes(.data$eff, .data$method)) +
    ggplot2::geom_vline(xintercept = 0, colour = "#cc3311", linetype = "dashed") +
    ggplot2::geom_errorbarh(ggplot2::aes(xmin = .data$lo, xmax = .data$hi),
                            height = 0.2, colour = .beam_palette[1], linewidth = 1) +
    ggplot2::geom_point(size = 2.6, colour = "#222222") +
    ggplot2::geom_text(ggplot2::aes(x = .data$hi, label = sprintf("P=%.2f", .data$ps)),
                       hjust = -0.2, size = 2.8, colour = "#555555") +
    ggplot2::expand_limits(x = max(hi) + 0.18 * (span + 1e-9)) +
    ggplot2::labs(x = sprintf("mean-rank difference vs %s (smaller is better)", ref), y = NULL,
                  title = title %||% "network meta-analysis forest plot") +
    theme_beam()
  .sized(p, width = 6.5, height = 1.4 + 0.4 * length(treat))
}

# Ranking-stability kinds
.k_critical_difference_band <- function(report) {
  ranks <- .num(report$average_ranks)
  names <- if (!is.null(report$tool_names)) .chr(report$tool_names) else
    paste0("tool_", seq_along(ranks))
  cd <- .num(report$critical_difference)
  ord <- order(ranks)
  names_ord <- names[ord]
  df <- data.frame(method = factor(names_ord, levels = rev(names_ord)), rank = ranks[ord])
  top <- ranks[ord][1]
  p <- ggplot2::ggplot(df, ggplot2::aes(.data$rank, .data$method)) +
    ggplot2::annotate("rect", xmin = top, xmax = top + cd, ymin = -Inf, ymax = Inf,
                      fill = "#cccccc", alpha = 0.5) +
    ggplot2::geom_point(size = 3, colour = "#222222") +
    ggplot2::labs(x = "average rank across datasets (rank 1 ranks first)", y = NULL,
                  title = sprintf("critical difference band %.2f (ties with the top tool)", cd)) +
    theme_beam()
  .sized(p, width = 6.5, height = 1.4 + 0.34 * length(names))
}

.k_specification_curve <- function(report, compact = TRUE) {
  .need("patchwork")
  specs <- .py_list(report$specifications)
  ord <- .num(report$curve_order) + 1
  n <- length(ord)
  tool_names <- if (!is.null(report$tool_names)) .chr(report$tool_names) else
    paste0("tool_", seq_along(.num(specs[[1]]$ranks)))
  n_tools <- length(tool_names)
  top_idx <- .num(report$most_frequent_top_tool) + 1
  ranks_mat <- t(vapply(ord, function(p) .num(specs[[p]]$ranks), numeric(n_tools)))
  xs <- seq_len(n)

  bg <- data.frame(x = rep(xs, times = n_tools), rank = as.vector(ranks_mat),
                   tool = rep(tool_names, each = n))
  topdf <- data.frame(x = xs, rank = ranks_mat[, top_idx])
  top <- ggplot2::ggplot() +
    ggplot2::geom_line(data = bg, ggplot2::aes(.data$x, .data$rank, group = .data$tool),
                       colour = "#e3e3e3", linewidth = 0.4) +
    ggplot2::geom_line(data = topdf, ggplot2::aes(.data$x, .data$rank),
                       colour = "#cc3311", linewidth = 1) +
    ggplot2::scale_y_reverse() +
    ggplot2::labs(x = NULL, y = "rank (1 ranks first)",
                  title = sprintf("specification curve: rank of %s across %d specifications",
                                  tool_names[top_idx], n)) +
    theme_beam()

  weightings <- .chr(report$weightings)
  methods <- .chr(report$methods)
  datasets <- if (!is.null(report$dataset_names)) .chr(report$dataset_names) else character(0)
  spec_w <- vapply(ord, function(p) as.character(reticulate::py_to_r(specs[[p]]$weighting)), character(1))
  spec_a <- vapply(ord, function(p) as.character(reticulate::py_to_r(specs[[p]]$aggregation)), character(1))
  spec_d <- vapply(ord, function(p) {
    d <- specs[[p]]$dataset
    if (is.null(d)) NA_character_ else as.character(reticulate::py_to_r(d))
  }, character(1))

  dataset_strip <- compact && length(datasets) > 0
  rows <- c(sprintf("weighting: %s", weightings), sprintf("aggregation: %s", methods))
  dots <- c(
    lapply(weightings, function(w) data.frame(x = xs[spec_w == w], row = sprintf("weighting: %s", w))),
    lapply(methods, function(a) data.frame(x = xs[spec_a == a], row = sprintf("aggregation: %s", a)))
  )
  if (length(datasets) > 0 && !dataset_strip) {
    rows <- c(rows, sprintf("dataset: %s", datasets))
    dots <- c(dots, lapply(datasets, function(dd)
      data.frame(x = xs[which(spec_d == dd)], row = sprintf("dataset: %s", dd))))
  }
  dotdf <- do.call(rbind, dots)
  dotdf$row <- factor(dotdf$row, levels = rev(rows))
  mid <- ggplot2::ggplot(dotdf, ggplot2::aes(.data$x, .data$row)) +
    ggplot2::geom_point(size = 0.8, colour = "#222222") +
    ggplot2::labs(x = "specification (sorted by the top tool's rank)", y = "choice") +
    theme_beam()

  if (dataset_strip) {
    strip_df <- data.frame(x = xs, dataset = factor(spec_d, levels = datasets))
    strip <- ggplot2::ggplot(strip_df, ggplot2::aes(.data$x, y = 1L, fill = .data$dataset)) +
      ggplot2::geom_tile() +
      ggplot2::scale_fill_manual(values = grDevices::colorRampPalette(.beam_palette)(length(datasets)),
                                 name = "dataset") +
      ggplot2::labs(x = "specification (sorted by the top tool's rank)", y = NULL) +
      theme_beam() +
      ggplot2::theme(axis.text.y = ggplot2::element_blank())
    mid <- mid + ggplot2::labs(x = NULL)
    fig <- patchwork::wrap_plots(top, mid, strip, ncol = 1,
                                 heights = c(2.4, max(1, 0.16 * length(rows) + 0.4), 0.5))
  } else {
    fig <- patchwork::wrap_plots(top, mid, ncol = 1,
                                 heights = c(2.4, max(1, 0.16 * length(rows) + 0.4)))
  }
  .sized(fig, width = max(7, min(13, 0.03 * n + 6)),
         height = max(4, 0.18 * (n_tools + length(rows)) + 2))
}

# Attribution kind
.k_attribution_progression <- function(report, title = NULL) {
  settings <- .py_list(report$settings)
  labels <- vapply(settings, function(s) as.character(reticulate::py_to_r(s$label)), character(1))
  shares <- cbind(
    `analyst choice` = vapply(settings, function(s) .num(s$analyst_choice_share), numeric(1)),
    dataset = vapply(settings, function(s) .num(s$dataset_share), numeric(1)),
    benchmarker = vapply(settings, function(s) .num(s$benchmarker_share), numeric(1))
  )
  .stacked_plot(shares, labels, colnames(shares), order = seq_along(labels),
                value_label = "share of rank-variance budget",
                title = title %||% "attribution across settings")
}

# Helpers
.py_plot <- function() reticulate::import("beam.plot")

# A Python sequence reached through `$` is sometimes handed back as an R list of
# Python objects and sometimes as a live Python iterable; return an R list either
# way so the kind can index it.
.py_list <- function(x) {
  if (inherits(x, "python.builtin.object")) reticulate::iterate(x, simplify = FALSE) else as.list(x)
}

.tau_heatmap <- function(report, labels, choice_label) {
  tau <- .mat(report$tau_matrix)
  mean_tau <- .num(report$mean_pairwise_tau)
  .heatmap_plot(tau, labels, labels, fill_label = "Kendall\ntau-b",
                diverging = TRUE, limits = c(-1, 1), digits = 2,
                title = sprintf("%s agreement on method ordering (mean tau-b %.2f)",
                                choice_label, mean_tau))
}

.concordance_report <- function(report) {
  if (reticulate::py_has_attr(report, "dataset_concordance")) {
    report <- report$dataset_concordance
  }
  if (is.null(report)) {
    stop("no dataset_concordance report; the run needs a tensor with at least two datasets",
         call. = FALSE)
  }
  report
}

.concordance_labels <- function(report) {
  ev <- .num(report$evaluated_datasets)
  if (!is.null(report$dataset_names)) {
    dn <- .chr(report$dataset_names)
    if (length(dn) >= max(ev) + 1) return(dn[ev + 1])
    return(dn)
  }
  paste0("dataset_", ev)
}

#' Registry mapping plot kinds to native builders
#' @keywords internal
.beam_plot_kinds <- list(
  funky_heatmap = .k_funky_heatmap,
  ranking = .k_ranking,
  normalized_scores = .k_normalized_scores,
  smaa = .k_smaa,
  dataset_stability = .k_dataset_stability,
  dataset_effect = .k_dataset_effect,
  aggregation_effect = .k_aggregation_effect,
  normalization_effect = .k_normalization_effect,
  weighting_effect = .k_weighting_effect,
  rank_sensitivity = .k_rank_sensitivity,
  rank_sensitivity_by_tool = .k_rank_sensitivity_by_tool,
  aggregation_agreement = .k_aggregation_agreement,
  normalization_agreement = .k_normalization_agreement,
  dataset_concordance = .k_dataset_concordance,
  dataset_struggle = .k_dataset_struggle,
  dataset_discrimination = .k_dataset_discrimination,
  bayesian_comparison = .k_bayesian_comparison,
  pairwise_majority = .k_pairwise_majority,
  critical_difference = .k_critical_difference,
  critical_difference_band = .k_critical_difference_band,
  specification_curve = .k_specification_curve,
  model_effects = .k_model_effects,
  variance_components = .k_variance_components,
  bradley_terry_leaves = .k_bradley_terry_leaves,
  difficulty_concordance = .k_difficulty_concordance,
  metric_correlation = .k_metric_correlation,
  metric_reliability_dropped = .k_metric_reliability_dropped,
  metric_dimensionality_scree = .k_metric_dimensionality_scree,
  network_forest = .k_network_forest,
  attribution_progression = .k_attribution_progression
)
