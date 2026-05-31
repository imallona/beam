#!/usr/bin/env Rscript
# Fit a frequentist network meta-analysis over benchmark results and return the
# pooled treatment effects, the treatment ranking (P-scores), and the
# heterogeneity and inconsistency statistics as JSON.
#
# Called as a one-shot subprocess by
# beam.heterogeneity.network_meta_analysis. The input is a JSON object on stdin
# with parallel arrays treatment, study, mean, sd and n (one entry per study arm,
# free of NaN, each study with at least two arms), plus an optional reference
# treatment and the summary measure sm (default "MD"). The arms are the methods;
# the studies are the (benchmark, dataset) blocks; the within-arm mean and sd are
# taken over the metrics. meta::pairwise turns the arm-level means into
# study-level contrasts, and netmeta pools the direct and indirect evidence into
# one coherent ranking. Lower scores are better (a rank of 1 is best), so the
# P-score treats small values as desirable. See docs/adr/0009 for the R boundary.

suppressPackageStartupMessages({
    library(jsonlite)
    library(meta)
    library(netmeta)
})

payload <- jsonlite::fromJSON(file("stdin"))

df <- data.frame(
    treatment = as.character(payload$treatment),
    study = as.character(payload$study),
    mean = as.numeric(payload$mean),
    sd = as.numeric(payload$sd),
    n = as.numeric(payload$n),
    stringsAsFactors = FALSE
)
sm <- if (is.null(payload$sm)) "MD" else as.character(payload$sm)
reference <- if (is.null(payload$reference)) NA_character_ else as.character(payload$reference)

warns <- character()
withW <- function(expr) {
    withCallingHandlers(
        expr,
        warning = function(w) {
            warns <<- c(warns, conditionMessage(w))
            invokeRestart("muffleWarning")
        }
    )
}

# pairwise and netmeta print progress tables to stdout; send that to stderr so
# only the JSON result lands on stdout for the caller to parse.
sink(stderr(), type = "output")

# Arm-level means to study-level contrasts (every pair within each study).
contrasts <- withW(meta::pairwise(
    treat = df$treatment,
    n = df$n,
    mean = df$mean,
    sd = df$sd,
    studlab = df$study,
    sm = sm
))

# netmeta expects an empty string, not NULL, to pick its own reference.
ref_arg <- if (is.na(reference)) "" else reference
net <- withW(netmeta::netmeta(
    TE = contrasts$TE,
    seTE = contrasts$seTE,
    treat1 = contrasts$treat1,
    treat2 = contrasts$treat2,
    studlab = contrasts$studlab,
    sm = sm,
    common = FALSE,
    random = TRUE,
    reference.group = ref_arg
))

treatments <- net$trts
ref <- net$reference.group
if (is.null(ref) || length(ref) == 0 || ref == "") {
    ref <- treatments[1]
}

# Pooled random-effects effect of each treatment relative to the reference,
# with its standard error and 95% confidence interval.
effect <- as.numeric(net$TE.random[, ref])
effect_se <- as.numeric(net$seTE.random[, ref])
effect_lower <- as.numeric(net$lower.random[, ref])
effect_upper <- as.numeric(net$upper.random[, ref])

# P-scores: the treatment ranking. Lower benchmark ranks are better, so small
# values are desirable; a higher P-score means a better-ranked method.
rank <- netmeta::netrank(net, small.values = "desirable")
pscore <- as.numeric(rank$ranking.random[treatments])

# Heterogeneity and, where the design supports it, the split into within-design
# heterogeneity and between-design inconsistency.
q_inconsistency <- NA_real_
df_inconsistency <- NA_real_
pval_inconsistency <- NA_real_
q_heterogeneity <- NA_real_
df_heterogeneity <- NA_real_
pval_heterogeneity <- NA_real_
decomp <- tryCatch(suppressWarnings(netmeta::decomp.design(net)), error = function(e) NULL)
if (!is.null(decomp)) {
    wd <- decomp$Q.decomp
    if (!is.null(wd) && "Q" %in% colnames(wd)) {
        if ("Within designs" %in% rownames(wd)) {
            q_heterogeneity <- as.numeric(wd["Within designs", "Q"])
            df_heterogeneity <- as.numeric(wd["Within designs", "df"])
            pval_heterogeneity <- as.numeric(wd["Within designs", "pval"])
        }
        if ("Between designs" %in% rownames(wd)) {
            q_inconsistency <- as.numeric(wd["Between designs", "Q"])
            df_inconsistency <- as.numeric(wd["Between designs", "df"])
            pval_inconsistency <- as.numeric(wd["Between designs", "pval"])
        }
    }
}

sink(NULL, type = "output")

out <- list(
    sm = sm,
    reference = ref,
    treatments = treatments,
    effect = effect,
    effect_se = effect_se,
    effect_lower = effect_lower,
    effect_upper = effect_upper,
    pscore = pscore,
    tau = as.numeric(net$tau),
    tau2 = as.numeric(net$tau2),
    i2 = as.numeric(net$I2),
    q_total = as.numeric(net$Q),
    df_total = as.numeric(net$df.Q),
    pval_total = as.numeric(net$pval.Q),
    q_heterogeneity = q_heterogeneity,
    df_heterogeneity = df_heterogeneity,
    pval_heterogeneity = pval_heterogeneity,
    q_inconsistency = q_inconsistency,
    df_inconsistency = df_inconsistency,
    pval_inconsistency = pval_inconsistency,
    n_studies = as.integer(net$k),
    n_treatments = as.integer(net$n),
    n_comparisons = as.integer(net$m),
    warnings = as.list(warns)
)

cat(jsonlite::toJSON(out, auto_unbox = TRUE, digits = NA, null = "null", na = "null"))
