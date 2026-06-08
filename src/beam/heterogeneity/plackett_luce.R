#!/usr/bin/env Rscript
# Fit a Plackett-Luce model on per-dataset method rankings and return the worth
# parameters, quasi-standard-errors, and fit statistics as JSON.
#
# Called as a one-shot subprocess by beam.heterogeneity.plackett_luce. The
# input is a JSON object on stdin with:
#   objects    method labels, the items being ranked
#   rankings   n_rankings by n_objects matrix of rank integers, 1 = best on
#              that dataset, ties shared, 0 = item absent from that ranking
#   npseudo    number of pseudo-rankings (the package device for connectivity)
# The output is a JSON object on stdout.

suppressPackageStartupMessages({
    library(jsonlite)
    library(PlackettLuce)
    library(qvcalc)
})

payload <- jsonlite::fromJSON(file("stdin"), simplifyVector = TRUE, simplifyMatrix = FALSE)

objects <- as.character(payload$objects)
ranks <- do.call(rbind, lapply(payload$rankings, function(r) as.integer(unlist(r))))
colnames(ranks) <- objects
npseudo <- if (is.null(payload$npseudo)) 0.5 else as.numeric(payload$npseudo)

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

# Log-worth (reference item at zero) and the unit-sum worth, aligned to the
# global object order. We read these from coef rather than itempar because
# itempar refits the model through its Poisson form, which fails on rankings
# that mix ties with partial coverage; coef is the stable path and gives the
# same worth after the unit-sum normalisation. An object never ranked is NA.
lw <- stats::coef(model, log = TRUE)
lw <- lw[names(lw) %in% objects]  # drop tie parameters (named "tie2" etc.)
log_worth <- rep(NA_real_, length(objects))
log_worth[match(names(lw), objects)] <- as.numeric(lw)

w <- exp(lw) / sum(exp(lw))
worth <- rep(NA_real_, length(objects))
worth[match(names(w), objects)] <- as.numeric(w)

# Quasi-standard errors give a reference-free comparison of any two methods.
# qvcalc shares itempar's Poisson refit, so it can fail on ties with partial
# rankings; when it does, report NA quasi-SE and a warning rather than aborting.
quasi_se <- rep(NA_real_, length(objects))
qv <- tryCatch(qvcalc::qvcalc(model), error = function(e) NULL)
if (is.null(qv)) {
    warns <- c(warns, "quasi-standard errors unavailable (ties with partial rankings)")
} else {
    qframe <- qv$qvframe
    rn <- rownames(qframe)
    keep <- rn %in% objects
    quasi_se[match(rn[keep], objects)] <- as.numeric(qframe$quasiSE[keep])
}

ll <- stats::logLik(model)

out <- list(
    objects = objects,
    worth = worth,
    log_worth = log_worth,
    quasi_se = quasi_se,
    n_rankings = length(R),
    connected = if (is.na(connected)) FALSE else connected,
    npseudo = npseudo,
    loglik = as.numeric(ll),
    df = as.integer(attr(ll, "df")),
    aic = stats::AIC(model),
    warnings = as.list(warns)
)

cat(jsonlite::toJSON(out, auto_unbox = TRUE, digits = NA, null = "null", na = "null"))
