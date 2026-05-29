# Native R heterogeneity diagnostics: lme4, psychotree, glmmTMB and PlackettLuce
# called directly. Model choices match the Python implementation. The fitting
# packages are Suggests; each function stops if its package is absent.

.require_pkg <- function(pkg) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    stop(
      sprintf("package '%s' is required for this diagnostic; install it from CRAN", pkg),
      call. = FALSE
    )
  }
}

# Score matrix (one metric) or 3D array with `metric` selecting the slice, to a
# long data frame with NaN dropped.
.long_scores <- function(scores, method_names, dataset_names, metric = NULL) {
  scores <- as.array(scores)
  d <- dim(scores)
  if (length(d) == 3L) {
    if (is.null(metric)) {
      stop("metric is required when scores is a 3D tensor", call. = FALSE)
    }
    idx <- if (is.numeric(metric)) as.integer(metric) else match(metric, dimnames(scores)[[3]])
    if (is.na(idx) || idx < 1L || idx > d[3]) {
      stop("metric not found in the third dimension of scores", call. = FALSE)
    }
    scores <- scores[, , idx]
    d <- dim(scores)
  }
  if (length(d) != 2L) {
    stop("scores must be a 2D matrix or a 3D array with a metric selector", call. = FALSE)
  }
  if (length(method_names) != d[1] || length(dataset_names) != d[2]) {
    stop("method_names and dataset_names must match the score matrix dimensions", call. = FALSE)
  }
  cells <- which(!is.na(scores), arr.ind = TRUE)
  data.frame(
    method = factor(method_names[cells[, 1]], levels = method_names),
    dataset = factor(dataset_names[cells[, 2]], levels = dataset_names),
    score = scores[cells],
    stringsAsFactors = FALSE
  )
}

# Per-method marginal means and standard errors via a contrast matrix over the
# fixed-effect coefficients.
.method_marginal_means <- function(fe, V, method_levels) {
  fe_names <- names(fe)
  L <- matrix(0, nrow = length(method_levels), ncol = length(fe_names),
              dimnames = list(method_levels, fe_names))
  L[, "(Intercept)"] <- 1
  for (i in seq_along(method_levels)) {
    col <- paste0("method", method_levels[i])
    if (col %in% fe_names) {
      L[i, col] <- 1
    }
  }
  emm <- as.vector(L %*% fe)
  emm_se <- sqrt(pmax(diag(L %*% V %*% t(L)), 0))
  list(effect = emm, effect_se = emm_se)
}

#' Mixed-effects variance decomposition on benchmark scores
#'
#' Fits `score ~ method + (1 | dataset)` (plus a method-by-dataset random effect
#' when cells have replicates) in lme4, or the same structure in glmmTMB with a
#' beta family for a metric bounded in (0, 1). Returns the per-method marginal
#' means, the variance components, the dataset intraclass correlation, and the
#' residuals. Fit natively in R; no Python is involved.
#'
#' @param scores Numeric matrix of shape `(n_methods, n_datasets)` for one
#'   metric, or a 3D array `(n_methods, n_datasets, n_metrics)` with `metric`
#'   selecting the slice.
#' @param method_names,dataset_names Character vectors aligned with the score
#'   axes.
#' @param metric Index or third-dimension name selecting the metric slice when
#'   `scores` is a 3D array; ignored for a 2D matrix.
#' @param engine `"lmer"` (default) or `"glmmtmb"`.
#' @param family For `engine = "glmmtmb"`, one of `"beta"`, `"gaussian"`, or
#'   `NULL` for auto-selection (beta when every score is in (0, 1)).
#' @param formula_kind `"auto"` (default), `"main"`, or `"interaction"`.
#'
#' @return A list of class `beam_mixed_effects` with the method marginal means
#'   and standard errors, variance components, dataset ICC, residuals, the
#'   formula, and fit diagnostics.
#'
#' @seealso [beam_bradley_terry_tree], [beam_plackett_luce].
#'
#' @examplesIf requireNamespace("lme4", quietly = TRUE)
#' scores <- matrix(c(0.80, 0.70, 0.60, 0.55,
#'                    0.78, 0.68, 0.58, 0.50,
#'                    0.83, 0.74, 0.61, 0.57,
#'                    0.79, 0.69, 0.59, 0.52,
#'                    0.81, 0.72, 0.62, 0.56), nrow = 4)
#' fit <- beam_mixed_effects(scores, c("a", "b", "c", "d"),
#'                           c("d1", "d2", "d3", "d4", "d5"))
#' fit$icc_dataset
#'
#' @export
beam_mixed_effects <- function(scores,
                               method_names,
                               dataset_names,
                               metric = NULL,
                               engine = c("lmer", "glmmtmb"),
                               family = NULL,
                               formula_kind = c("auto", "main", "interaction")) {
  engine <- match.arg(engine)
  formula_kind <- match.arg(formula_kind)
  if (!is.null(family) && engine != "glmmtmb") {
    stop("family only applies to engine='glmmtmb'", call. = FALSE)
  }
  if (engine == "glmmtmb") .require_pkg("glmmTMB") else .require_pkg("lme4")

  df <- .long_scores(scores, method_names, dataset_names, metric)
  if (nlevels(droplevels(df$method)) < 2) {
    stop("need at least 2 distinct methods with a non-NaN score", call. = FALSE)
  }
  if (nlevels(droplevels(df$dataset)) < 2) {
    stop("need at least 2 distinct datasets with a non-NaN score", call. = FALSE)
  }
  df$method <- droplevels(df$method)
  df$dataset <- droplevels(df$dataset)

  counts <- table(df$dataset, df$method)
  has_replicates <- any(counts > 1L)
  kind <- if (formula_kind == "auto") {
    if (has_replicates) "interaction" else "main"
  } else {
    formula_kind
  }
  form <- if (kind == "interaction") {
    score ~ method + (1 | dataset) + (1 | dataset:method)
  } else {
    score ~ method + (1 | dataset)
  }

  scale <- "response"
  if (engine == "glmmtmb" && is.null(family)) {
    family <- if (all(df$score > 0 & df$score < 1)) "beta" else "gaussian"
  }
  if (engine == "glmmtmb" && family == "beta") {
    n <- nrow(df)
    df$score <- (df$score * (n - 1) + 0.5) / n
    scale <- "link"
  }

  warns <- character()
  catch <- function(expr) {
    withCallingHandlers(expr, warning = function(w) {
      warns <<- c(warns, conditionMessage(w))
      invokeRestart("muffleWarning")
    })
  }

  if (engine == "glmmtmb") {
    fam <- if (family == "beta") glmmTMB::beta_family() else stats::gaussian()
    model <- catch(glmmTMB::glmmTMB(form, data = df, family = fam, REML = TRUE))
    fe <- glmmTMB::fixef(model)$cond
    V <- as.matrix(stats::vcov(model)$cond)
    is_singular <- isTRUE(!model$sdr$pdHess)
    vc <- glmmTMB::VarCorr(model)$cond
    components <- list()
    for (grp in names(vc)) components[[grp]] <- as.numeric(vc[[grp]][1, 1])
    if (family == "beta") {
      components[["dispersion"]] <- as.numeric(glmmTMB::sigma(model))
    } else {
      components[["Residual"]] <- as.numeric(glmmTMB::sigma(model))^2
    }
    resids <- unname(stats::residuals(model, type = "pearson"))
  } else {
    model <- catch(lme4::lmer(form, data = df, REML = TRUE))
    fe <- lme4::fixef(model)
    V <- as.matrix(stats::vcov(model))
    is_singular <- lme4::isSingular(model)
    vcdf <- as.data.frame(lme4::VarCorr(model))
    components <- as.list(vcdf$vcov)
    names(components) <- vcdf$grp
    resids <- unname(stats::residuals(model))
  }

  levs <- levels(df$method)
  mm <- .method_marginal_means(fe, V, levs)
  total <- sum(unlist(components))
  icc <- if (total == 0) NA_real_ else (components[["dataset"]] %||% 0) / total

  structure(
    list(
      method_names = levs,
      method_effects = mm$effect,
      method_effect_se = mm$effect_se,
      variance_components = components,
      total_variance = total,
      icc_dataset = icc,
      residuals = resids,
      residual_methods = as.character(df$method),
      residual_datasets = as.character(df$dataset),
      formula = paste(deparse(form), collapse = " "),
      formula_kind = kind,
      engine = engine,
      family = if (engine == "glmmtmb") family else "gaussian",
      scale = scale,
      has_replicates = has_replicates,
      singular = is_singular,
      n_obs = nrow(df),
      n_methods = nlevels(df$method),
      n_datasets = nlevels(df$dataset),
      loglik = as.numeric(stats::logLik(model)),
      aic = stats::AIC(model),
      warnings = warns
    ),
    class = "beam_mixed_effects"
  )
}

`%||%` <- function(a, b) if (is.null(a)) b else a

# Per-dataset dense rankings: 1 = best, ties shared, 0 = absent, oriented by polarity.
.rankings_from_matrix <- function(mat, higher_is_better = TRUE) {
  oriented <- if (higher_is_better) mat else -mat
  nd <- ncol(oriented)
  nm <- nrow(oriented)
  out <- matrix(0L, nrow = nd, ncol = nm)
  for (d in seq_len(nd)) {
    col <- oriented[, d]
    obs <- !is.na(col)
    if (sum(obs) < 2) next
    x <- -col[obs]
    out[d, obs] <- match(x, sort(unique(x)))
  }
  out
}

# Per-dataset paired comparisons in psychotools pair order: +1/-1/0 per pair,
# NA when either method is missing.
.paired_comparisons <- function(mat, higher_is_better = TRUE) {
  oriented <- if (higher_is_better) mat else -mat
  nm <- nrow(oriented)
  nd <- ncol(oriented)
  pairs <- list()
  for (j in 2:nm) {
    for (i in seq_len(j - 1L)) {
      pairs[[length(pairs) + 1L]] <- c(i, j)
    }
  }
  comp <- matrix(NA_real_, nrow = nd, ncol = length(pairs))
  for (k in seq_along(pairs)) {
    i <- pairs[[k]][1]
    j <- pairs[[k]][2]
    a <- oriented[i, ]
    b <- oriented[j, ]
    obs <- !(is.na(a) | is.na(b))
    comp[obs, k] <- sign(a[obs] - b[obs])
  }
  comp
}

#' Plackett-Luce model on per-dataset rankings of methods
#'
#' Reads each dataset column of a method by dataset matrix as a ranking of the
#' methods (best first, after orienting by polarity, ties shared, missing cells
#' left out) and fits a Plackett-Luce model in R's PlackettLuce. Returns a worth
#' per method summing to one, the log-worth, and reference-free
#' quasi-standard-errors. Fit natively in R.
#'
#' @param scores Numeric matrix of shape `(n_methods, n_datasets)` on one
#'   metric.
#' @param method_names Character vector of length `n_methods`, the items ranked.
#' @param higher_is_better Logical: whether a higher score ranks first.
#' @param npseudo Number of pseudo-rankings for connectivity (default 0.5).
#'
#' @return A list of class `beam_plackett_luce` with the worth, log-worth,
#'   quasi-standard-errors, connectivity flag, and fit statistics.
#'
#' @seealso [beam_bradley_terry_tree].
#'
#' @examplesIf requireNamespace("PlackettLuce", quietly = TRUE)
#' scores <- matrix(c(0.80, 0.70, 0.60,
#'                    0.78, 0.68, 0.58,
#'                    0.83, 0.74, 0.61,
#'                    0.79, 0.69, 0.59), nrow = 3)
#' fit <- beam_plackett_luce(scores, c("a", "b", "c"))
#' fit$worth
#'
#' @export
beam_plackett_luce <- function(scores,
                               method_names,
                               higher_is_better = TRUE,
                               npseudo = 0.5) {
  .require_pkg("PlackettLuce")
  scores <- as.matrix(scores)
  if (nrow(scores) != length(method_names)) {
    stop("method_names must match the number of matrix rows", call. = FALSE)
  }
  if (npseudo < 0) stop("npseudo must be non-negative", call. = FALSE)

  ranks <- .rankings_from_matrix(scores, higher_is_better)
  keep <- rowSums(ranks > 0) >= 2
  ranks <- ranks[keep, , drop = FALSE]
  if (nrow(ranks) < 2) {
    stop("need at least 2 datasets with two or more ranked methods", call. = FALSE)
  }
  colnames(ranks) <- method_names

  R <- PlackettLuce::as.rankings(ranks, input = "rankings")
  connected <- tryCatch(PlackettLuce::connectivity(R)$no == 1L, error = function(e) NA)

  warns <- character()
  model <- withCallingHandlers(
    PlackettLuce::PlackettLuce(R, npseudo = npseudo),
    warning = function(w) {
      warns <<- c(warns, conditionMessage(w))
      invokeRestart("muffleWarning")
    }
  )

  lw <- stats::coef(model, log = TRUE)
  lw <- lw[names(lw) %in% method_names]
  log_worth <- rep(NA_real_, length(method_names))
  log_worth[match(names(lw), method_names)] <- as.numeric(lw)
  w <- exp(lw) / sum(exp(lw))
  worth <- rep(NA_real_, length(method_names))
  worth[match(names(w), method_names)] <- as.numeric(w)

  quasi_se <- rep(NA_real_, length(method_names))
  if (requireNamespace("qvcalc", quietly = TRUE)) {
    qv <- tryCatch(qvcalc::qvcalc(model), error = function(e) NULL)
    if (is.null(qv)) {
      warns <- c(warns, "quasi-standard errors unavailable (ties with partial rankings)")
    } else {
      qframe <- qv$qvframe
      rn <- rownames(qframe)
      keep_rn <- rn %in% method_names
      quasi_se[match(rn[keep_rn], method_names)] <- as.numeric(qframe$quasiSE[keep_rn])
    }
  }

  ll <- stats::logLik(model)
  structure(
    list(
      method_names = method_names,
      worth = worth,
      log_worth = log_worth,
      quasi_se = quasi_se,
      n_rankings = length(R),
      connected = if (is.na(connected)) FALSE else connected,
      npseudo = npseudo,
      loglik = as.numeric(ll),
      df = as.integer(attr(ll, "df")),
      aic = stats::AIC(model),
      warnings = warns
    ),
    class = "beam_plackett_luce"
  )
}

.bt_worth <- function(subset_pc, method_names) {
  out <- list(worth = rep(NA_real_, length(method_names)),
              worth_se = rep(NA_real_, length(method_names)))
  fit <- tryCatch(psychotools::btmodel(subset_pc), error = function(e) NULL)
  if (is.null(fit)) return(out)
  ip <- tryCatch(psychotools::itempar(fit), error = function(e) NULL)
  if (is.null(ip)) return(out)
  se <- tryCatch(sqrt(diag(stats::vcov(ip))), error = function(e) rep(NA_real_, length(ip)))
  pos <- match(names(ip), method_names)
  out$worth[pos] <- as.numeric(ip)
  out$worth_se[pos] <- as.numeric(se)
  out
}

#' Bradley-Terry tree on per-dataset paired method comparisons
#'
#' Builds per-dataset paired comparisons from a method by dataset matrix and
#' fits a Bradley-Terry tree (psychotree::bttree) that partitions the datasets
#' by their features, so each leaf has its own Bradley-Terry ranking. Returns
#' the tree nodes, the per-dataset leaf assignment, and the global flat ranking.
#' Fit natively in R.
#'
#' @param scores Numeric matrix of shape `(n_methods, n_datasets)` on one
#'   metric.
#' @param method_names,dataset_names Character vectors aligned with the score
#'   axes.
#' @param features Named list of dataset-level feature vectors (numeric or
#'   character), each of length `n_datasets`.
#' @param higher_is_better Logical: whether a higher score is preferred.
#' @param minsize Minimal number of datasets in a node (default 5).
#' @param alpha Significance level for the parameter-stability split test
#'   (default 0.05).
#'
#' @return A list of class `beam_bradley_terry_tree` with the global worth, the
#'   per-dataset leaf assignment, whether a split was found, and one entry per
#'   tree node (split variable, breakpoint, per-leaf worth).
#'
#' @seealso [beam_plackett_luce].
#'
#' @examplesIf requireNamespace("psychotree", quietly = TRUE)
#' scores <- matrix(stats::runif(4 * 8), nrow = 4)
#' fit <- beam_bradley_terry_tree(
#'   scores, c("a", "b", "c", "d"), paste0("d", 1:8),
#'   features = list(size = seq_len(8)), minsize = 3
#' )
#' fit$did_split
#'
#' @export
beam_bradley_terry_tree <- function(scores,
                                    method_names,
                                    dataset_names,
                                    features,
                                    higher_is_better = TRUE,
                                    minsize = 5L,
                                    alpha = 0.05) {
  .require_pkg("psychotree")
  scores <- as.matrix(scores)
  if (nrow(scores) != length(method_names) || ncol(scores) != length(dataset_names)) {
    stop("method_names and dataset_names must match the score matrix dimensions", call. = FALSE)
  }
  if (!is.list(features) || is.null(names(features)) || any(names(features) == "")) {
    stop("features must be a named list of per-dataset vectors", call. = FALSE)
  }

  comparisons <- .paired_comparisons(scores, higher_is_better)
  pc <- psychotools::paircomp(comparisons, labels = method_names)

  df <- data.frame(preference = pc)
  for (nm in names(features)) {
    v <- features[[nm]]
    df[[nm]] <- if (is.numeric(v)) as.numeric(v) else factor(as.character(v))
  }
  feature_names <- names(features)

  warns <- character()
  tree <- withCallingHandlers(
    psychotree::bttree(
      stats::as.formula(paste("preference ~", paste(feature_names, collapse = " + "))),
      data = df, minsize = as.integer(minsize), alpha = alpha
    ),
    warning = function(w) {
      warns <<- c(warns, conditionMessage(w))
      invokeRestart("muffleWarning")
    }
  )

  leaf_assignment <- as.integer(stats::predict(tree, type = "node"))
  all_ids <- as.integer(partykit::nodeids(tree))
  terminal_ids <- as.integer(partykit::nodeids(tree, terminal = TRUE))
  did_split <- length(terminal_ids) > 1L

  nodes <- list()
  for (id in all_ids) {
    if (id %in% terminal_ids) {
      members <- which(leaf_assignment == id)
      w <- .bt_worth(pc[members], method_names)
      nodes[[length(nodes) + 1L]] <- list(
        id = id, terminal = TRUE, n = length(members),
        worth = w$worth, worth_se = w$worth_se
      )
    } else {
      node <- tryCatch(partykit::node_party(tree[[id]]), error = function(e) NULL)
      varname <- NULL
      brk <- NULL
      if (!is.null(node)) {
        sp <- tryCatch(partykit::split_node(node), error = function(e) NULL)
        if (!is.null(sp)) {
          varid <- tryCatch(partykit::varid_split(sp), error = function(e) NULL)
          if (!is.null(varid)) varname <- names(df)[varid]
          breaks <- tryCatch(partykit::breaks_split(sp), error = function(e) NULL)
          if (!is.null(breaks)) brk <- as.numeric(breaks)[1]
        }
      }
      nodes[[length(nodes) + 1L]] <- list(
        id = id, terminal = FALSE, n = NA_integer_,
        split_variable = varname, split_breakpoint = brk
      )
    }
  }

  global <- .bt_worth(pc, method_names)
  structure(
    list(
      method_names = method_names,
      dataset_names = dataset_names,
      nodes = nodes,
      leaf_assignment = leaf_assignment,
      global_worth = global$worth,
      global_worth_se = global$worth_se,
      did_split = did_split,
      feature_names = feature_names,
      minsize = as.integer(minsize),
      alpha = alpha,
      warnings = warns
    ),
    class = "beam_bradley_terry_tree"
  )
}

#' Cross-benchmark variance decomposition
#'
#' Fits `score ~ method + (1 | benchmark) + (1 | benchmark:dataset) +
#' (1 | method:benchmark)` in lme4, with dataset nested in benchmark. Reports
#' the method-by-benchmark variance share, the disagreement attributable to the
#' benchmark rather than the method, with restricted likelihood-ratio tests for
#' each random term. Fit natively in R.
#'
#' @param methods,datasets,benchmarks,scores Parallel vectors of equal length,
#'   one entry per (benchmark, dataset, method) observation. Rows with a NaN
#'   score are dropped.
#'
#' @return A list of class `beam_source_variance` with the method marginal
#'   means, the variance components, and the per-term likelihood-ratio tests.
#'
#' @export
beam_source_variance_decomposition <- function(methods, datasets, benchmarks, scores) {
  .require_pkg("lme4")
  scores <- as.numeric(scores)
  if (length(methods) != length(scores) ||
      length(datasets) != length(scores) ||
      length(benchmarks) != length(scores)) {
    stop("methods, datasets, benchmarks and scores must have the same length", call. = FALSE)
  }
  keep <- !is.na(scores)
  df <- data.frame(
    method = factor(as.character(methods)[keep]),
    dataset = factor(as.character(datasets)[keep]),
    benchmark = factor(as.character(benchmarks)[keep]),
    score = scores[keep],
    stringsAsFactors = FALSE
  )

  form <- score ~ method + (1 | benchmark) + (1 | benchmark:dataset) + (1 | method:benchmark)
  warns <- character()
  model <- withCallingHandlers(
    lme4::lmer(form, data = df, REML = TRUE),
    warning = function(w) {
      warns <<- c(warns, conditionMessage(w))
      invokeRestart("muffleWarning")
    }
  )

  fe <- lme4::fixef(model)
  V <- as.matrix(stats::vcov(model))
  levs <- levels(df$method)
  mm <- .method_marginal_means(fe, V, levs)

  vcdf <- as.data.frame(lme4::VarCorr(model))
  components <- as.list(vcdf$vcov)
  names(components) <- vcdf$grp

  reduced_forms <- list(
    "benchmark" = score ~ method + (1 | benchmark:dataset) + (1 | method:benchmark),
    "benchmark:dataset" = score ~ method + (1 | benchmark) + (1 | method:benchmark),
    "method:benchmark" = score ~ method + (1 | benchmark) + (1 | benchmark:dataset)
  )
  ll_full <- as.numeric(stats::logLik(model))
  lrt_statistic <- list()
  lrt_pvalue <- list()
  for (term in names(reduced_forms)) {
    reduced <- tryCatch(
      suppressWarnings(lme4::lmer(reduced_forms[[term]], data = df, REML = TRUE)),
      error = function(e) NULL
    )
    if (is.null(reduced)) {
      lrt_statistic[[term]] <- NA_real_
      lrt_pvalue[[term]] <- NA_real_
      next
    }
    stat <- max(0, 2 * (ll_full - as.numeric(stats::logLik(reduced))))
    lrt_statistic[[term]] <- stat
    lrt_pvalue[[term]] <- 0.5 * stats::pchisq(stat, df = 1, lower.tail = FALSE)
  }

  structure(
    list(
      formula = paste(deparse(form), collapse = " "),
      method_names = levs,
      method_effects = mm$effect,
      method_effect_se = mm$effect_se,
      variance_components = components,
      lrt_statistic = lrt_statistic,
      lrt_pvalue = lrt_pvalue,
      n_obs = nrow(df),
      n_methods = nlevels(df$method),
      n_datasets = nlevels(df$dataset),
      n_benchmarks = nlevels(df$benchmark),
      singular = lme4::isSingular(model),
      loglik = ll_full,
      aic = stats::AIC(model),
      warnings = warns
    ),
    class = "beam_source_variance"
  )
}
