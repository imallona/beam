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

# Run-based kinds -------------------------------------------------------------

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

# Report-based kinds ----------------------------------------------------------

.k_rank_sensitivity <- function(report) {
  factors <- .chr(report$factors)
  shares <- vapply(factors, function(f) .num(report$factor_shares[[f]]), numeric(1))
  labels <- c(factors, "interaction")
  values <- c(shares, .num(report$interaction_share))
  fill <- c(rep(.beam_palette[1], length(factors)), .beam_palette[7])
  .bar_plot(values, labels, order = seq_along(labels), fill = fill,
            value_label = "share of rank variance", title = "what moves the ranking")
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

# Helpers ---------------------------------------------------------------------

.py_plot <- function() reticulate::import("beam.plot")

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
  model_effects = .k_model_effects
)
