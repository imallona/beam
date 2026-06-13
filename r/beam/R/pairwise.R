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
#'   direction in which a higher score means a method outperforms.
#' @param rope The region of practical equivalence in native units; a difference
#'   within it is a tie. Pass the metric's noise floor to count an outperformance
#'   only past the smallest interpretable difference. Default 0.
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


#' Posterior probability that one method is practically better than another
#'
#' Reads a pairwise superiority report and applies the Bayesian sign test of
#' Benavoli et al. (2017) to each pair's outperformance counts. For a pair, it
#' reports the posterior probability that one method is practically better, that
#' the two are practically equivalent within the region of practical equivalence,
#' and that the other is practically better, three numbers that sum to one and
#' read directly as evidence for a choice. This is the posterior companion to the
#' critical-difference test, which reports a p-value rather than the probability
#' that a method is better. Forwards to the Python `beam.mcda.bayesian_sign_comparison`.
#' Plot the result with `beam_plot(report, "bayesian_comparison")`.
#'
#' @param report A Python `PairwiseSuperiorityReport`, as returned by
#'   [beam_pairwise_superiority]. Its region of practical equivalence is reused.
#' @param prior_strength Number of prior pseudo-observations. Default 1.
#' @param prior_placement Where the prior mass sits: `"rope"` (default, on the
#'   equivalence region), `"uniform"`, or `"neutral"`.
#' @param decision_threshold Posterior probability a region must reach for a
#'   decisive per-pair label. Default 0.95.
#' @param n_samples Monte Carlo draws from each posterior. Default 50000.
#' @param seed Seed for the draws. Default 42.
#'
#' @return The Python `BayesianSignReport`. Read its fields with `$`:
#'   `$probability_better`, `$probability_equivalent`, `$standing`, `$order`,
#'   `$per_pair`.
#'
#' @references Benavoli A, Corani G, Demsar J, Zaffalon M. Time for a change: a
#'   tutorial for comparing multiple classifiers through Bayesian analysis.
#'   Journal of Machine Learning Research 2017, 18(77):1-36.
#'
#' @seealso [beam_pairwise_superiority], [beam_pairwise_transitivity],
#'   [beam_critical_difference].
#'
#' @export
beam_bayesian_sign_comparison <- function(report,
                                          prior_strength = 1,
                                          prior_placement = "rope",
                                          decision_threshold = 0.95,
                                          n_samples = 50000,
                                          seed = 42) {
  .require_beam()
  mcda <- reticulate::import("beam.mcda")
  mcda$bayesian_sign_comparison(
    report,
    prior_strength = as.numeric(prior_strength),
    prior_placement = prior_placement,
    decision_threshold = as.numeric(decision_threshold),
    n_samples = as.integer(n_samples),
    seed = as.integer(seed)
  )
}
