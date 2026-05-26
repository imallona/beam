#!/usr/bin/env Rscript
# Fit a Bradley-Terry tree on per-dataset paired method comparisons and return
# the tree structure, per-leaf Bradley-Terry strengths, and the leaf assignment
# per dataset as JSON.
#
# Called as a one-shot subprocess by beam.heterogeneity.bradley_terry_tree. The
# input is a JSON object on stdin with:
#   objects               method labels, the objects being compared
#   comparisons           n_datasets by n_pairs matrix of paired outcomes, in
#                         psychotools pair order (1,2),(1,3),...,(2,3),...;
#                         +1 first method better, -1 second better, 0 tie,
#                         null when the comparison is missing
#   features_numeric      named list of numeric covariates, one value per dataset
#   features_categorical  named list of categorical covariates, one per dataset
#   minsize               minimal number of datasets in a node
#   alpha                 significance level for the parameter-stability split test
# The output is a JSON object on stdout. See the docstring of bradley_terry.py
# and docs/adr/0010-bradley-terry-trees.md for the model and the design.

suppressPackageStartupMessages({
    library(jsonlite)
    library(psychotree)
})

payload <- jsonlite::fromJSON(file("stdin"), simplifyVector = TRUE, simplifyMatrix = FALSE)

objects <- as.character(payload$objects)

# Rebuild the comparison matrix, mapping JSON null to NA and tolerating either a
# list-of-vectors or a list-of-lists shape from the JSON parser.
to_numeric_row <- function(row) {
    vapply(row, function(e) if (is.null(e)) NA_real_ else as.numeric(e), numeric(1))
}
comparisons <- do.call(rbind, lapply(payload$comparisons, to_numeric_row))
pc <- psychotools::paircomp(comparisons, labels = objects)

n_datasets <- nrow(comparisons)
df <- data.frame(preference = pc)
for (nm in names(payload$features_numeric)) {
    df[[nm]] <- as.numeric(payload$features_numeric[[nm]])
}
for (nm in names(payload$features_categorical)) {
    df[[nm]] <- factor(as.character(payload$features_categorical[[nm]]))
}
feature_names <- c(names(payload$features_numeric), names(payload$features_categorical))

minsize <- if (is.null(payload$minsize)) 5L else as.integer(payload$minsize)
alpha <- if (is.null(payload$alpha)) 0.05 else as.numeric(payload$alpha)

# Worth parameters (strengths summing to one) and their standard errors for the
# Bradley-Terry model fit to one subset of the paired comparisons. Aligned to
# the global object order; an object never compared in the subset is NA.
worth_of <- function(subset_pc) {
    out <- list(worth = rep(NA_real_, length(objects)), worth_se = rep(NA_real_, length(objects)))
    fit <- tryCatch(psychotools::btmodel(subset_pc), error = function(e) NULL)
    if (is.null(fit)) {
        return(out)
    }
    ip <- tryCatch(psychotools::itempar(fit), error = function(e) NULL)
    if (is.null(ip)) {
        return(out)
    }
    se <- tryCatch(sqrt(diag(vcov(ip))), error = function(e) rep(NA_real_, length(ip)))
    pos <- match(names(ip), objects)
    out$worth[pos] <- as.numeric(ip)
    out$worth_se[pos] <- as.numeric(se)
    out
}

warns <- character()
tree <- withCallingHandlers(
    psychotree::bttree(
        stats::as.formula(paste("preference ~", paste(feature_names, collapse = " + "))),
        data = df,
        minsize = minsize,
        alpha = alpha
    ),
    warning = function(w) {
        warns <<- c(warns, conditionMessage(w))
        invokeRestart("muffleWarning")
    }
)

# Terminal node membership per dataset, in input order.
leaf_assignment <- as.integer(predict(tree, type = "node"))
all_ids <- as.integer(partykit::nodeids(tree))
terminal_ids <- as.integer(partykit::nodeids(tree, terminal = TRUE))
did_split <- length(terminal_ids) > 1L

# Read the split variable, breakpoint, and parameter-stability p-values for one
# inner node, defensively: partykit's accessors differ across versions, so each
# risky read degrades to NULL rather than aborting the whole fit.
inner_split_info <- function(id) {
    node <- tryCatch(partykit::node_party(tree[[id]]), error = function(e) NULL)
    if (is.null(node)) {
        return(list(split_variable = NULL, split_breakpoint = NULL, p_values = NULL))
    }
    sp <- tryCatch(partykit::split_node(node), error = function(e) NULL)
    varname <- NULL
    brk <- NULL
    if (!is.null(sp)) {
        varid <- tryCatch(partykit::varid_split(sp), error = function(e) NULL)
        if (!is.null(varid)) {
            varname <- names(df)[varid]
        }
        breaks <- tryCatch(partykit::breaks_split(sp), error = function(e) NULL)
        if (!is.null(breaks)) {
            brk <- as.numeric(breaks)[1]
        }
    }
    info <- tryCatch(partykit::info_node(node), error = function(e) NULL)
    pvals <- NULL
    if (!is.null(info) && !is.null(info$test)) {
        test <- info$test
        if ("p.value" %in% rownames(test)) {
            pv <- test["p.value", ]
            pvals <- as.list(as.numeric(pv))
            names(pvals) <- colnames(test)
        }
    }
    list(split_variable = varname, split_breakpoint = brk, p_values = pvals)
}

nodes <- list()
for (id in all_ids) {
    is_terminal <- id %in% terminal_ids
    if (is_terminal) {
        members <- which(leaf_assignment == id)
        w <- worth_of(pc[members])
        nodes[[length(nodes) + 1L]] <- list(
            id = id,
            terminal = TRUE,
            n = length(members),
            split_variable = NULL,
            split_breakpoint = NULL,
            p_values = NULL,
            worth = w$worth,
            worth_se = w$worth_se
        )
    } else {
        si <- inner_split_info(id)
        kids <- tryCatch(
            as.integer(partykit::nodeids(tree[[id]]))[-1],
            error = function(e) integer(0)
        )
        nodes[[length(nodes) + 1L]] <- list(
            id = id,
            terminal = FALSE,
            n = NA_integer_,
            split_variable = si$split_variable,
            split_breakpoint = si$split_breakpoint,
            p_values = si$p_values,
            worth = NULL,
            worth_se = NULL
        )
    }
}

# Global Bradley-Terry strengths over all datasets, the reference ranking the
# tree qualifies.
global <- worth_of(pc)

out <- list(
    objects = objects,
    n_datasets = n_datasets,
    n_methods = length(objects),
    split = did_split,
    nodes = nodes,
    leaf_assignment = leaf_assignment,
    global_worth = global$worth,
    global_worth_se = global$worth_se,
    feature_names = feature_names,
    minsize = minsize,
    alpha = alpha,
    warnings = warns
)

cat(jsonlite::toJSON(out, auto_unbox = TRUE, digits = NA, null = "null", na = "null"))
