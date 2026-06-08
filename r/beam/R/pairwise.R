#' Compare methods two at a time with a probability of superiority
#'
#' For every pair of methods, counts how often one outperforms the other across
#' the datasets they share, with an equivalence band (the region of practical
#' equivalence) that can be set to the metric's noise floor. The probability of
#' superiority is the fraction of datasets on which one method outperforms the
#' other, a common-language effect size, and a sign test says whether the
#' difference is more than chance. This is the effect-size companion to the
#' critical-difference test, which reports significance but not magnitude. Forwards
#' to the Python `beam.mcda.pairwise_superiority`.
#'
#' @param scores A numeric matrix of shape (methods, datasets) on one metric, in
#'   native units.
#' @param polarity One of `"higher_is_better"` or `"lower_is_better"`, the
#'   direction of a win.
#' @param rope The region of practical equivalence in native units; a difference
#'   within it is a tie. Pass the metric's noise floor to count a win only past
#'   the smallest interpretable difference. Default 0.
#' @param method_names Optional character vector of method labels.
#' @param alpha Significance level for the not-distinguishable pairs. Default 0.05.
#'
#' @return The Python `PairwiseSuperiorityReport`. Read its fields with `$`:
#'   `$probability_superior`, `$standing`, `$order`, `$per_pair`,
#'   `$equivalent_pairs`.
#'
#' @seealso [beam_critical_difference], [beam_noise_floor_separation].
#'
#' @export
beam_pairwise_superiority <- function(scores,
                                      polarity,
                                      rope = 0,
                                      method_names = NULL,
                                      alpha = 0.05) {
  .require_beam()
  mcda <- reticulate::import("beam.mcda")
  mcda$pairwise_superiority(
    scores = scores,
    polarity = polarity,
    rope = as.numeric(rope),
    method_names = if (is.null(method_names)) NULL else as.character(method_names),
    alpha = as.numeric(alpha)
  )
}
