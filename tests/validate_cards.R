#!/usr/bin/env Rscript
# Validate every metric card under metrics/ against the JSON Schema, from R.
# Run from the repo root:
#   Rscript tests/validate_cards.R

suppressPackageStartupMessages({
    library(jsonvalidate)
    library(yaml)
    library(jsonlite)
})

# Resolve the script's directory robustly. When run with Rscript, commandArgs()
# contains a "--file=<path>" entry. When sourced, fall back to the working
# directory.
get_script_dir <- function() {
    args <- commandArgs(trailingOnly = FALSE)
    file_arg <- grep("^--file=", args, value = TRUE)
    if (length(file_arg) > 0L) {
        return(normalizePath(dirname(sub("^--file=", "", file_arg[1L]))))
    }
    NULL
}

script_dir <- get_script_dir()
repo_root <- if (!is.null(script_dir)) {
    normalizePath(file.path(script_dir, ".."))
} else {
    normalizePath(getwd())
}

schema_path <- file.path(repo_root, "schema", "metric_card.schema.json")
metrics_dir <- file.path(repo_root, "metrics")

if (!file.exists(schema_path)) {
    stop(sprintf("schema not found at %s", schema_path))
}

cards <- Sys.glob(file.path(metrics_dir, "*", "v*.yaml"))
if (length(cards) == 0L) {
    stop(sprintf("no metric cards found under %s/*/v*.yaml", metrics_dir))
}

validator <- jsonvalidate::json_validator(schema_path, engine = "ajv")

# Force YAML sequences to R lists. Without this, yaml::read_yaml collapses
# single-element sequences (e.g. "task: [clustering]") into atomic vectors,
# which jsonlite::toJSON(auto_unbox = TRUE) then unwraps to JSON scalars,
# breaking schema validation.
seq_handler <- list(seq = function(x) as.list(x))

failures <- character()
for (card_path in cards) {
    card <- yaml::read_yaml(card_path, handlers = seq_handler)
    card_json <- jsonlite::toJSON(
        card,
        auto_unbox = TRUE,
        null = "null",
        na = "null"
    )
    ok <- validator(card_json, verbose = TRUE, greedy = TRUE)
    if (!isTRUE(ok)) {
        errs <- attr(ok, "errors")
        msg <- sprintf(
            "%s:\n%s",
            card_path,
            paste(utils::capture.output(print(errs)), collapse = "\n")
        )
        failures <- c(failures, msg)
    }
}

if (length(failures) > 0L) {
    cat(
        "R-side card validation FAILED:\n",
        paste(failures, collapse = "\n\n"),
        "\n",
        sep = "",
        file = stderr()
    )
    quit(status = 1L)
} else {
    cat(sprintf("R-side validation OK: %d cards validated\n", length(cards)))
}
