#' How many tools beat the chance baseline, per metric
#'
#' Reads raw scores against the per-metric random baseline declared on the cards
#' (`semantics.score_of_random_baseline`) and reports, for each metric, how many
#' tools score better than chance, plus the tools that beat chance on no metric.
#' Forwards to the Python `beam.mcda.beats_random_baseline`.
#'
#' @param scores A numeric matrix of shape (tools, metrics) of raw scores.
#' @param polarity Character vector, one per metric column, each
#'   `"higher_is_better"` or `"lower_is_better"`.
#' @param baselines The chance score per metric, one per metric column. Use an R
#'   list with `NULL` for a metric that has no declared baseline, or a numeric
#'   vector when every metric has one. Source it from the cards with
#'   `beam.cards` in the registry.
#' @param metric_ids Optional character vector of metric labels carried into the
#'   report. Default `NULL`.
#'
#' @return The Python `RandomBaselineReport`. Read its fields with `$`.
#'
#' @seealso [beam_noise_floor_separation], [beam_rank].
#'
#' @export
beam_beats_random_baseline <- function(scores, polarity, baselines, metric_ids = NULL) {
  .require_beam()
  mcda <- reticulate::import("beam.mcda")
  mcda$beats_random_baseline(
    scores = scores,
    polarity = as.character(polarity),
    baselines = baselines,
    metric_ids = if (is.null(metric_ids)) NULL else as.character(metric_ids)
  )
}

#' Tool pairs no metric separates above the noise floor
#'
#' Compares every pair of tools on the raw scores and flags the pairs that no
#' metric separates by its declared noise floor (`comparability.noise_floor`),
#' the pairs the metric set cannot tell apart, and whether the two top-ranked
#' tools sit within the floor. Forwards to the Python
#' `beam.mcda.noise_floor_separation`.
#'
#' @param scores A numeric matrix of shape (tools, metrics) of raw scores.
#' @param noise_floors The noise floor per metric, one per metric column. Use an
#'   R list with `NULL` for a metric that has no declared floor, or a numeric
#'   vector when every metric has one.
#' @param ranks Optional integer vector, the rank of each tool, used to report
#'   whether the top two are within the floor. Default `NULL`.
#'
#' @return The Python `NoiseFloorReport`. Read its fields with `$`.
#'
#' @seealso [beam_beats_random_baseline], [beam_rank].
#'
#' @export
beam_noise_floor_separation <- function(scores, noise_floors, ranks = NULL) {
  .require_beam()
  mcda <- reticulate::import("beam.mcda")
  mcda$noise_floor_separation(
    scores = scores,
    noise_floors = noise_floors,
    ranks = if (is.null(ranks)) NULL else as.integer(ranks)
  )
}
