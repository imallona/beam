#!/usr/bin/env Rscript
# Fit a cross-benchmark mixed-effects model and return the variance
# decomposition and per-method marginal means as JSON.
#
# Called as a one-shot subprocess by
# beam.heterogeneity.source_variance_decomposition. The input is a JSON object
# on stdin with parallel arrays method, dataset, benchmark and score (one entry
# per observation, free of NaN). The output is a JSON object on stdout. The
# model is score ~ method + (1 | benchmark) + (1 | benchmark:dataset) +
# (1 | method:benchmark): the method-by-benchmark variance is the disagreement
# attributable to the benchmark, dataset is nested in benchmark, and the
# residual absorbs the method-by-dataset interaction and noise (not separable
# with one observation per cell). See docs/adr/0009.

suppressPackageStartupMessages({
    library(jsonlite)
    library(lme4)
})

payload <- jsonlite::fromJSON(file("stdin"))

df <- data.frame(
    method = factor(as.character(payload$method)),
    dataset = factor(as.character(payload$dataset)),
    benchmark = factor(as.character(payload$benchmark)),
    score = as.numeric(payload$score)
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

# Per-method marginal mean over benchmarks and datasets, with standard errors,
# from a contrast matrix over the fixed-effect coefficients.
fe <- lme4::fixef(model)
V <- as.matrix(stats::vcov(model))
fe_names <- names(fe)
levs <- levels(df$method)
L <- matrix(0, nrow = length(levs), ncol = length(fe_names), dimnames = list(levs, fe_names))
L[, "(Intercept)"] <- 1
for (i in seq_along(levs)) {
    col <- paste0("method", levs[i])
    if (col %in% fe_names) {
        L[i, col] <- 1
    }
}
emm <- as.vector(L %*% fe)
emm_se <- sqrt(pmax(diag(L %*% V %*% t(L)), 0))

# Variance components, one per grouping factor plus the residual.
vc <- as.data.frame(lme4::VarCorr(model))
components <- as.list(vc$vcov)
names(components) <- vc$grp

out <- list(
    formula = paste(deparse(form), collapse = " "),
    method_levels = levs,
    method_effect = emm,
    method_effect_se = emm_se,
    variance_components = components,
    n_obs = nrow(df),
    n_methods = nlevels(df$method),
    n_datasets = nlevels(df$dataset),
    n_benchmarks = nlevels(df$benchmark),
    singular = lme4::isSingular(model),
    loglik = as.numeric(stats::logLik(model)),
    aic = stats::AIC(model),
    warnings = as.list(warns)
)

cat(jsonlite::toJSON(out, auto_unbox = TRUE, digits = NA, null = "null"))
