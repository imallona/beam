#' Agreement between normalizations on one ranking
#'
#' Re-ranks one tool by metric matrix under several normalizations at a fixed
#' weighting and aggregation and reports their pairwise Kendall agreement, a
#' mean-rank consensus, whether the top tool is unanimous, and each tool's rank
#' span. It shows how much a recommendation depends on the rescaling choice, the
#' companion to [beam_aggregation_agreement] for the aggregation choice. Forwards
#' to the Python `beam.mcda.normalization_agreement`.
#'
#' @param scores A numeric matrix of shape (tools, metrics).
#' @param polarity Character vector, one per metric column, each
#'   `"higher_is_better"` or `"lower_is_better"`.
#' @param weights Either an objective scheme name (`"equal"`, `"entropy"`,
#'   `"std"`, `"critic"`, `"merec"`) or a numeric vector of metric weights.
#'   Default `"equal"`.
#' @param method Aggregation rule, one of `"saw"`, `"topsis"`, `"vikor"`,
#'   `"promethee_ii"`, `"comet"`. Default `"saw"`.
#' @param strategies Optional character vector of normalization names to
#'   compare, each applied to every metric column. The default `NULL` uses the
#'   four scale-agnostic strategies (`min_max`, `log_min_max`, `rank`, `zscore`).
#' @param recommended Optional character vector, one normalization per metric,
#'   added as a candidate labelled `"recommended"`. Pass the card-recommended
#'   normalization so it is compared against the uniform strategies.
#' @param missing Missing-data policy, one of `"error"`, `"available"`,
#'   `"worst"`, `"impute"`. Default `"error"`.
#' @param tool_names Optional character vector of tool labels. Default `NULL`.
#' @param ... Further arguments forwarded to the Python function, for example
#'   `bounds`, `baselines`, `targets` from the card context.
#'
#' @return A `beam_normalization_agreement` object wrapping the Python
#'   `NormalizationAgreementReport`. Read its fields with `$`, print it for a
#'   compact summary, or `plot()` it for the agreement heatmap.
#'
#' @seealso [beam_aggregation_agreement], [beam_rank].
#'
#' @export
beam_normalization_agreement <- function(scores, polarity, weights = "equal",
                                         method = "saw", strategies = NULL,
                                         recommended = NULL, missing = "error",
                                         tool_names = NULL, ...) {
  .require_beam()
  mcda <- reticulate::import("beam.mcda")
  report <- mcda$normalization_agreement(
    scores = scores,
    polarity = as.character(polarity),
    weights = weights,
    method = method,
    strategies = if (is.null(strategies)) NULL else as.character(strategies),
    recommended = if (is.null(recommended)) NULL else as.character(recommended),
    missing = missing,
    tool_names = if (is.null(tool_names)) NULL else as.character(tool_names),
    ...
  )
  .as_beam_report(report, "beam_normalization_agreement")
}
