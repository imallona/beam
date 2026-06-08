#' Split a ranking's variance between the choices and the data
#'
#' Attributes a ranking's instability to the weighting scheme, the aggregation
#' rule and (for a tensor input) the dataset, by running the full factorial of
#' every combination and decomposing each tool's rank variance with an analysis
#' of variance. The shares sum to one. A large dataset share means the ranking
#' depends on which dataset you use; a large weighting or aggregation share means
#' it depends on a choice the analyst could make differently. Forwards to the
#' Python `beam.mcda.rank_sensitivity`.
#'
#' @param scores A numeric matrix of shape (tools, metrics), or a 3D array of
#'   shape (tools, datasets, metrics) to add the dataset as a third factor.
#' @param polarity Character vector, one per metric, each `"higher_is_better"` or
#'   `"lower_is_better"`.
#' @param weightings Optional character vector of weighting schemes to vary.
#'   Default `NULL` uses equal, entropy, std and critic. MEREC is left out by
#'   default because it cannot run on min_max-normalized zeros.
#' @param methods Optional character vector of aggregations to vary. Default
#'   `NULL` uses the five beam aggregations.
#' @param normalization,bounds,baselines,targets Optional per-metric
#'   normalization context, as returned by the Python `registry_context`. Pass
#'   them so the decomposition rests on the same normalized matrix as the ranking.
#' @param missing Missing-data policy forwarded to every run. Default `"error"`;
#'   use `"worst"` to complete a tensor with gaps.
#' @param tool_names Optional character vector of tool labels.
#' @param dataset_names Optional character vector of dataset labels for a tensor.
#'
#' @return The Python `RankSensitivityReport`. Read its fields with `$`:
#'   `$factor_shares`, `$interaction_share`, `$most_influential_factor`,
#'   `$headline_tool`, `$headline_rank_by_dataset`.
#'
#' @seealso [beam_aggregation_agreement], [beam_smaa], [beam_rank].
#'
#' @export
beam_rank_sensitivity <- function(scores,
                                  polarity,
                                  weightings = NULL,
                                  methods = NULL,
                                  normalization = NULL,
                                  bounds = NULL,
                                  baselines = NULL,
                                  targets = NULL,
                                  missing = "error",
                                  tool_names = NULL,
                                  dataset_names = NULL) {
  .require_beam()
  mcda <- reticulate::import("beam.mcda")
  mcda$rank_sensitivity(
    scores = scores,
    polarity = as.character(polarity),
    weightings = if (is.null(weightings)) NULL else as.character(weightings),
    methods = if (is.null(methods)) NULL else as.character(methods),
    normalization = normalization,
    bounds = bounds,
    baselines = baselines,
    targets = targets,
    missing = missing,
    tool_names = if (is.null(tool_names)) NULL else as.character(tool_names),
    dataset_names = if (is.null(dataset_names)) NULL else as.character(dataset_names)
  )
}
