#!/usr/bin/env Rscript
# Fit a mixed-effects model on benchmark scores and return the variance
# decomposition, per-method marginal means, and residuals as JSON.
#
# Called as a one-shot subprocess by beam.heterogeneity.mixed_effects. The
# input is a JSON object on stdin with arrays method, dataset and score (one
# entry per observation, already free of NaN), a scalar formula_kind (one of
# "auto", "main", "interaction"), a scalar engine ("lmer" or "glmmtmb") and a
# scalar family ("beta", "gaussian" or null). The output is a JSON object on
# stdout. lme4 fits the Gaussian engine and glmmTMB the beta engine for bounded
# metrics.

payload <- jsonlite::fromJSON(file("stdin"))

engine <- if (is.null(payload$engine)) "lmer" else payload$engine
suppressPackageStartupMessages({
    library(jsonlite)
    if (engine == "glmmtmb") library(glmmTMB) else library(lme4)
})

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

# Resolve the glmmTMB family: beta when every score is strictly inside (0, 1)
# and the caller did not force one, gaussian otherwise. The beta family models
# a metric bounded in (0, 1); scores exactly at the bounds are squeezed inside
# with the Smithson-Verkuilen transform so the likelihood is defined.
family <- payload$family
scale <- "response"
if (engine == "glmmtmb") {
    if (is.null(family)) {
        family <- if (all(df$score > 0 & df$score < 1)) "beta" else "gaussian"
    }
    if (family == "beta") {
        n <- nrow(df)
        df$score <- (df$score * (n - 1) + 0.5) / n
        scale <- "link"
    }
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
} else {
    model <- catch(lme4::lmer(form, data = df, REML = TRUE))
    fe <- lme4::fixef(model)
    V <- as.matrix(stats::vcov(model))
    is_singular <- lme4::isSingular(model)
}

# Per-method estimated marginal mean over datasets, on the model scale (the
# link scale for a beta fit). The random effects are mean zero, so the mean for
# method m is the fixed-effect prediction intercept + effect(m). Build a
# contrast matrix L over the fixed-effect coefficients and read the means and
# their standard errors from L beta and diag(L V L').
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

# Variance components on the model scale. lme4 reports the random-effect
# variances plus a Gaussian Residual. glmmTMB reports the random-effect
# variances; the observation-level term is the residual variance for gaussian
# and the dispersion parameter for beta (reported under "dispersion", which is
# the beta precision, not a variance, so it is not comparable to a Gaussian
# residual).
if (engine == "glmmtmb") {
    vc <- glmmTMB::VarCorr(model)$cond
    components <- list()
    for (grp in names(vc)) {
        components[[grp]] <- as.numeric(vc[[grp]][1, 1])
    }
    if (family == "beta") {
        components[["dispersion"]] <- as.numeric(sigma(model))
    } else {
        components[["Residual"]] <- as.numeric(sigma(model))^2
    }
    resids <- unname(stats::residuals(model, type = "pearson"))
} else {
    vc <- as.data.frame(lme4::VarCorr(model))
    components <- as.list(vc$vcov)
    names(components) <- vc$grp
    resids <- unname(stats::residuals(model))
}

out <- list(
    formula = paste(deparse(form), collapse = " "),
    formula_kind = kind,
    engine = engine,
    family = if (engine == "glmmtmb") family else "gaussian",
    scale = scale,
    method_levels = levs,
    method_effect = emm,
    method_effect_se = emm_se,
    variance_components = components,
    residuals = resids,
    n_obs = nrow(df),
    n_methods = nlevels(df$method),
    n_datasets = nlevels(df$dataset),
    has_replicates = has_replicates,
    singular = is_singular,
    loglik = as.numeric(stats::logLik(model)),
    aic = stats::AIC(model),
    warnings = as.list(warns)
)

cat(jsonlite::toJSON(out, auto_unbox = TRUE, digits = NA, null = "null"))
