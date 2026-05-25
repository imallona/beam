#!/usr/bin/env Rscript
# Fit a mixed-effects model on benchmark scores and return the variance
# decomposition, per-method marginal means, and residuals as JSON.
#
# Called as a one-shot subprocess by beam.heterogeneity.mixed_effects. The
# input is a JSON object on stdin with arrays method, dataset and score (one
# entry per observation, already free of NaN) and a scalar formula_kind, one
# of "auto", "main" or "interaction". The output is a JSON object on stdout.
# See docs/adr/0009-heterogeneity-mixed-effects-via-r.md for the model choice.

suppressPackageStartupMessages({
    library(jsonlite)
    library(lme4)
})

payload <- jsonlite::fromJSON(file("stdin"))

df <- data.frame(
    method = factor(as.character(payload$method)),
    dataset = factor(as.character(payload$dataset)),
    score = as.numeric(payload$score)
)

# A replicate is more than one observation in a (dataset, method) cell. With
# one observation per cell the method-by-dataset interaction is confounded
# with the residual and cannot be fit as a separate variance component, so
# "auto" falls back to the main-effects model in that case.
counts <- table(df$dataset, df$method)
has_replicates <- any(counts > 1L)

kind <- payload$formula_kind
if (is.null(kind)) {
    kind <- "auto"
}
if (kind == "auto") {
    kind <- if (has_replicates) "interaction" else "main"
}

form <- if (kind == "interaction") {
    score ~ method + (1 | dataset) + (1 | dataset:method)
} else {
    score ~ method + (1 | dataset)
}

warns <- character()
model <- withCallingHandlers(
    lme4::lmer(form, data = df, REML = TRUE),
    warning = function(w) {
        warns <<- c(warns, conditionMessage(w))
        invokeRestart("muffleWarning")
    }
)

# Per-method estimated marginal mean over datasets. The random dataset (and
# interaction) effects are mean zero, so the marginal mean for method m is the
# fixed-effect prediction intercept + effect(m). Build a contrast matrix L over
# the fixed-effect coefficients and read the means and their standard errors
# from L beta and diag(L V L').
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
emm_var <- diag(L %*% V %*% t(L))
emm_se <- sqrt(pmax(emm_var, 0))

# Variance components, one per grouping factor plus the residual. For random
# intercepts var2 is NA and vcov holds the variance.
vc <- as.data.frame(lme4::VarCorr(model))
components <- as.list(vc$vcov)
names(components) <- vc$grp

out <- list(
    formula = paste(deparse(form), collapse = " "),
    formula_kind = kind,
    method_levels = levs,
    method_effect = emm,
    method_effect_se = emm_se,
    variance_components = components,
    residuals = unname(stats::residuals(model)),
    n_obs = nrow(df),
    n_methods = nlevels(df$method),
    n_datasets = nlevels(df$dataset),
    has_replicates = has_replicates,
    singular = lme4::isSingular(model),
    loglik = as.numeric(stats::logLik(model)),
    aic = stats::AIC(model),
    warnings = warns
)

cat(jsonlite::toJSON(out, auto_unbox = TRUE, digits = NA, null = "null"))
