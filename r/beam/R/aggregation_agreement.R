#' Agreement between aggregation methods on one ranking
#'
#' Re-ranks one tool by metric matrix under the five aggregations at a fixed
#' weighting and reports their pairwise Kendall agreement, a mean-rank consensus,
#' whether the top tool is unanimous, and each tool's rank span. It shows how
#' much a recommendation depends on the aggregation choice. Forwards to the
#' Python `beam.mcda.aggregation_agreement`.
#'
#' @param scores A numeric matrix of shape (tools, metrics).
#' @param polarity Character vector, one per metric column, each
#'   `"higher_is_better"` or `"lower_is_better"`.
#' @param weights Either an objective scheme name (`"equal"`, `"entropy"`,
#'   `"std"`, `"critic"`, `"merec"`) or a numeric vector of metric weights.
#'   Default `"equal"`.
#' @param methods Optional character vector of aggregation names to compare. The
#'   default `NULL` uses all five.
#' @param missing Missing-data policy, one of `"error"`, `"available"`,
#'   `"worst"`, `"impute"`. Default `"error"`.
#' @param tool_names Optional character vector of tool labels. Default `NULL`.
#' @param ... Further arguments forwarded to the Python function, for example
#'   `normalization`, `bounds`, `baselines`, `targets` from the card context.
#'
#' @return The Python `AggregationAgreementReport`. Read its fields with `$`.
#'
#' @seealso [beam_rank].
#'
#' @export
beam_aggregation_agreement <- function(scores, polarity, weights = "equal",
                                       methods = NULL, missing = "error",
                                       tool_names = NULL, ...) {
  .require_beam()
  mcda <- reticulate::import("beam.mcda")
  mcda$aggregation_agreement(
    scores = scores,
    polarity = as.character(polarity),
    weights = weights,
    methods = if (is.null(methods)) NULL else as.character(methods),
    missing = missing,
    tool_names = if (is.null(tool_names)) NULL else as.character(tool_names),
    ...
  )
}
