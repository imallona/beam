#' Check whether the pairwise majority relation gives one consistent order
#'
#' Reads a pairwise superiority report and builds the pairwise majority relation:
#' method i outperforms method j when it does so on more of their shared datasets
#' than j does. It then reports the method preferred to every other one when such
#' a method exists, the cyclic triples of methods (a cycle of pairwise majorities,
#' described by Condorcet in 1785), the coefficient of consistence of Kendall and
#' Babington Smith (1940), and whether the relation is transitive. When the
#' relation has a cycle, no single order agrees with all the pairwise majorities,
#' so the order an aggregation reports depends on the rule. It does no new ranking.
#' Forwards to the Python `beam.mcda.pairwise_transitivity`.
#'
#' @param report A Python `PairwiseSuperiorityReport`, as returned by
#'   [beam_pairwise_superiority].
#'
#' @return The Python `PairwiseTransitivityReport`. Read its fields with `$`:
#'   `$dominance`, `$tied_pairs`, `$condorcet_choice`, `$circular_triads`,
#'   `$n_circular_triads`, `$coefficient_of_consistence`, `$is_transitive`,
#'   `$consistent_order`, `$summary`.
#'
#' @seealso [beam_pairwise_superiority], [beam_critical_difference].
#'
#' @export
beam_pairwise_transitivity <- function(report) {
  .require_beam()
  mcda <- reticulate::import("beam.mcda")
  mcda$pairwise_transitivity(report)
}
