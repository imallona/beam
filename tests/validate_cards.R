#!/usr/bin/env Rscript
# Validate every metric card under metrics/ against the JSON Schema, from R.
# This is the R-side equivalent of tests/test_schema.py. It exists so that the
# metric card format stays usable from R without surprises. Run from the repo
# root with: Rscript tests/validate_cards.R

suppressPackageStartupMessages({
    library(jsonvalidate)
    library(yaml)
    library(jsonlite)
})

repo_root <- normalizePath(file.path(dirname(sys.frame(1)$ofile), ".."))
if (is.na(repo_root) || !file.exists(repo_root)) {
    repo_root <- getwd()
}

schema_path <- file.path(repo_root, "schema", "metric_card.schema.json")
metrics_dir <- file.path(repo_root, "metrics")

cards <- Sys.glob(file.path(metrics_dir, "*", "v*.yaml"))
if (length(cards) == 0L) {
    stop("no metric cards found under metrics/<id>/v*.yaml")
}

failures <- character()
for (card_path in cards) {
    card <- yaml::read_yaml(card_path)
    card_json <- jsonlite::toJSON(card, auto_unbox = TRUE, null = "null")
    schema_str <- paste(readLines(schema_path, warn = FALSE), collapse = "\n")
    result <- jsonvalidate::json_validate(
        json = card_json,
        schema = schema_str,
        engine = "ajv",
        verbose = TRUE,
        greedy = TRUE,
        strict = FALSE
    )
    if (!isTRUE(result)) {
        errs <- attr(result, "errors")
        msg <- sprintf("%s: %s", card_path,
                       paste(capture.output(print(errs)), collapse = " | "))
        failures <- c(failures, msg)
    }
}

if (length(failures) > 0L) {
    cat("R-side card validation FAILED:\n", paste(failures, collapse = "\n"), "\n",
        file = stderr())
    quit(status = 1L)
} else {
    cat(sprintf("R-side validation OK: %d cards validated\n", length(cards)))
}
