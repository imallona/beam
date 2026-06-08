#' Audit metric cards against the observed scores
#'
#' Reads the raw scores against the numeric values each metric card declares
#' (range, chance baseline, target, noise floor) and reports where they
#' disagree, before any normalization. Hard contradictions (a score, baseline or
#' target out of range, a non-positive or malformed bound) are violations; data
#' dependent observations (a constant metric, a noise floor wider than the
#' observed spread, an absent metric) are notes. Forwards to the Python
#' `beam.mcda.card_data_consistency`.
#'
#' @param scores A numeric matrix of shape (tools, metrics) of raw scores.
#' @param polarity Character vector, one per metric column, each
#'   `"higher_is_better"`, `"lower_is_better"` or `"target_value"`.
#' @param bounds The declared range per metric, one entry per metric column, each
#'   a length-two list `list(lower, upper)` with `NULL` on a side the card leaves
#'   open. Source it from the cards with the registry.
#' @param baselines Optional chance score per metric, an R list with `NULL` where
#'   the card declares none. Default `NULL`.
#' @param targets Optional target value per metric, an R list with `NULL` where
#'   the card declares none. Default `NULL`.
#' @param noise_floors Optional noise floor per metric, an R list with `NULL`
#'   where the card declares none. Default `NULL`.
#' @param metric_ids Optional character vector of metric labels carried into the
#'   findings. Default `NULL`.
#' @param range_tol Non-negative absolute tolerance on the range edges. Default 0.
#'
#' @return The Python `CardDataConsistencyReport`. Read its fields with `$`:
#'   `$ok`, `$violations`, `$notes`, `$per_metric`.
#'
#' @seealso [beam_beats_random_baseline], [beam_noise_floor_separation],
#'   [beam_rank].
#'
#' @export
beam_card_data_consistency <- function(scores,
                                       polarity,
                                       bounds,
                                       baselines = NULL,
                                       targets = NULL,
                                       noise_floors = NULL,
                                       metric_ids = NULL,
                                       range_tol = 0) {
  .require_beam()
  mcda <- reticulate::import("beam.mcda")
  mcda$card_data_consistency(
    scores = scores,
    polarity = as.character(polarity),
    bounds = bounds,
    baselines = baselines,
    targets = targets,
    noise_floors = noise_floors,
    metric_ids = if (is.null(metric_ids)) NULL else as.character(metric_ids),
    range_tol = as.numeric(range_tol)
  )
}
