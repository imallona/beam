#' Build the specification curve from a rank-sensitivity report
#'
#' Lists the ranking produced by every combination of weighting, aggregation and
#' (for a tensor) dataset, then reports how often the recommendation holds: the
#' fraction of combinations that rank the same tool first, the fraction that
#' produce the single most common ordering, and how many distinct tools ever
#' reach the top. This is the specification-curve view from meta-research
#' (Simonsohn, Simmons and Nelson 2020; Steegen et al. 2016). It post-processes
#' the factorial that [beam_rank_sensitivity] already ran, so it does no new
#' ranking. Forwards to the Python `beam.mcda.specification_curve`.
#'
#' @param report A Python `RankSensitivityReport`, as returned by
#'   [beam_rank_sensitivity].
#'
#' @return The Python `SpecificationCurveReport`. Read its fields with `$`:
#'   `$specifications`, `$curve_order`, `$most_frequent_top_tool`,
#'   `$most_frequent_top_fraction`, `$modal_order`, `$modal_order_fraction`,
#'   `$n_distinct_top_tools`.
#'
#' @seealso [beam_rank_sensitivity].
#'
#' @export
beam_specification_curve <- function(report) {
  .require_beam()
  mcda <- reticulate::import("beam.mcda")
  mcda$specification_curve(report)
}
