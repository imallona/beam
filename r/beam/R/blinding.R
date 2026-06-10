#' Hide tool names for blind analysis
#'
#' Replaces the tool names in a score table with opaque labels and shuffles the
#' rows under a seed, so the analyst can fix the weighting, aggregation and
#' metric set without seeing which method is which. Returns the blinded scores
#' and a seal that maps the labels back to the true names. This is the blind
#' analysis practice from particle physics and clinical trials (MacCoun and
#' Perlmutter 2015; Klein and Roodman 2005). Forwards to the Python `beam.blind`.
#'
#' The blinding is a record, not a guarantee: software cannot stop someone
#' reading the source file. The seal carries a fingerprint that beam writes into
#' the run manifest, so a reviewer can confirm the analysis ran on scores blinded
#' under that exact seal.
#'
#' @param scores A `beam.Scores` object (from `beam_load_scores` or the Python
#'   `beam.load_scores`).
#' @param seed Integer permutation seed. The same seed reproduces the same
#'   blinding. Default `0`.
#'
#' @return A list with `scores` (the blinded `beam.Scores`) and `seal` (the
#'   Python `Seal`).
#'
#' @seealso [beam_unblind], [beam_write_seal], [beam_read_seal].
#'
#' @export
beam_blind <- function(scores, seed = 0) {
  py <- .require_beam()
  result <- py$blind(scores, seed = as.integer(seed))
  list(scores = result[[1]], seal = result[[2]])
}

#' Restore true tool names after a blind analysis
#'
#' Translates the opaque labels in a blinded `beam.Scores` or a `RunResult` back
#' to the true tool names using the seal. The tool rows keep their blinded order;
#' only the names change. Forwards to the Python `beam.unblind`.
#'
#' @param obj A blinded `beam.Scores` or a `RunResult` from ranking one.
#' @param seal The seal returned by [beam_blind].
#'
#' @return The same type as `obj`, with true tool names.
#'
#' @seealso [beam_blind].
#'
#' @export
beam_unblind <- function(obj, seal) {
  py <- .require_beam()
  py$unblind(obj, seal)
}

#' Write a blinding seal to a JSON file
#'
#' @param seal A seal from [beam_blind].
#' @param path Output JSON path.
#'
#' @return Invisibly, the output path.
#'
#' @seealso [beam_blind], [beam_read_seal].
#'
#' @export
beam_write_seal <- function(seal, path) {
  py <- .require_beam()
  py$write_seal(seal, path)
  invisible(path)
}

#' Read a blinding seal written by beam_write_seal
#'
#' @param path Path to the seal JSON.
#'
#' @return The Python `Seal`.
#'
#' @seealso [beam_blind], [beam_write_seal].
#'
#' @export
beam_read_seal <- function(path) {
  py <- .require_beam()
  py$read_seal(path)
}
