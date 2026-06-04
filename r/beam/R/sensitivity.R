#' Stochastic multicriteria acceptability analysis (SMAA)
#'
#' Samples weights over the simplex and reports, per tool, how often it lands in
#' each rank, the share of weight space where it ranks first, and its central
#' weights. Forwards to the Python `beam.mcda.smaa`.
#'
#' @param scores A numeric matrix of shape (tools, metrics).
#' @param polarity Character vector, one per metric column, each
#'   `"higher_is_better"` or `"lower_is_better"`.
#' @param n_samples Number of weight vectors to sample. Default `1000`.
#' @param method Aggregation method, one of `"saw"`, `"topsis"`, `"vikor"`,
#'   `"promethee_ii"`, `"comet"`. Default `"saw"`.
#' @param seed Optional integer seed for the sampling, so the result reproduces.
#'   Default `NULL`.
#' @param ... Further arguments forwarded to the Python function, for example
#'   `alpha`, `normalization`, `bounds` from the card context.
#'
#' @return The Python `SMAAReport`. Read its fields with `$`.
#'
#' @seealso [beam_rank], [beam_smallest_weight_perturbation].
#'
#' @export
beam_smaa <- function(scores, polarity, n_samples = 1000, method = "saw",
                      seed = NULL, ...) {
  .require_beam()
  mcda <- reticulate::import("beam.mcda")
  mcda$smaa(
    scores = scores,
    polarity = as.character(polarity),
    n_samples = as.integer(n_samples),
    method = method,
    seed = if (is.null(seed)) NULL else as.integer(seed),
    ...
  )
}

#' Rank stability under leaving one metric out
#'
#' Re-ranks the tools with each metric removed in turn and reports how much the
#' ranking moves, naming the most influential metric. Forwards to the Python
#' `beam.mcda.leave_one_metric_out`.
#'
#' @param scores A numeric matrix of shape (tools, metrics).
#' @param polarity Character vector, one per metric column, each
#'   `"higher_is_better"` or `"lower_is_better"`.
#' @param metric_ids Optional character vector of metric labels. Default `NULL`.
#' @param weights Either an objective scheme name or a numeric vector of metric
#'   weights. Default `"equal"`.
#' @param method Aggregation method. Default `"saw"`.
#' @param ... Further arguments forwarded to the Python function, for example
#'   `normalization`, `bounds`, `baselines`, `targets`, `missing`.
#'
#' @return The Python `SensitivityReport`. Read its fields with `$`.
#'
#' @seealso [beam_leave_one_dataset_out], [beam_rank].
#'
#' @export
beam_leave_one_metric_out <- function(scores, polarity, metric_ids = NULL,
                                      weights = "equal", method = "saw", ...) {
  .require_beam()
  mcda <- reticulate::import("beam.mcda")
  mcda$leave_one_metric_out(
    scores = scores,
    polarity = as.character(polarity),
    metric_ids = if (is.null(metric_ids)) NULL else as.character(metric_ids),
    weights = weights,
    method = method,
    ...
  )
}

#' Rank stability under leaving one dataset out
#'
#' Pools a tool by dataset by metric array across datasets, then re-ranks with
#' each dataset removed in turn, reporting per-tool rank stability and the most
#' influential dataset. Forwards to the Python `beam.mcda.leave_one_dataset_out`.
#'
#' @param tensor A numeric 3D array of shape (tools, datasets, metrics).
#' @param polarity Character vector, one per metric, each `"higher_is_better"` or
#'   `"lower_is_better"`.
#' @param reduction_rules Character vector, one cross-dataset reduction per
#'   metric, each `"arithmetic_mean"`, `"geometric_mean"`, `"median"` or
#'   `"rank_mean"`.
#' @param dataset_names Optional character vector of dataset labels. Default
#'   `NULL`.
#' @param metric_ids Optional character vector of metric labels. Default `NULL`.
#' @param weights Either an objective scheme name or a numeric vector of metric
#'   weights. Default `"equal"`.
#' @param method Aggregation method. Default `"saw"`.
#' @param ... Further arguments forwarded to the Python function, for example
#'   `normalization`, `bounds`, `baselines`, `targets`, `missing`.
#'
#' @return The Python `DatasetSensitivityReport`. Read its fields with `$`.
#'
#' @seealso [beam_leave_one_metric_out], [beam_rank].
#'
#' @export
beam_leave_one_dataset_out <- function(tensor, polarity, reduction_rules,
                                       dataset_names = NULL, metric_ids = NULL,
                                       weights = "equal", method = "saw", ...) {
  .require_beam()
  mcda <- reticulate::import("beam.mcda")
  mcda$leave_one_dataset_out(
    tensor = tensor,
    polarity = as.character(polarity),
    reduction_rules = as.character(reduction_rules),
    dataset_names = if (is.null(dataset_names)) NULL else as.character(dataset_names),
    metric_ids = if (is.null(metric_ids)) NULL else as.character(metric_ids),
    weights = weights,
    method = method,
    ...
  )
}

#' Smallest weight change that flips the top tool
#'
#' Finds the smallest single-weight change that moves a different tool into first
#' place, and flags the recommendation as fragile when that change is small.
#' Forwards to the Python `beam.mcda.smallest_weight_perturbation`.
#'
#' @param scores A numeric matrix of shape (tools, metrics).
#' @param polarity Character vector, one per metric column, each
#'   `"higher_is_better"` or `"lower_is_better"`.
#' @param weights Either an objective scheme name or a numeric vector of metric
#'   weights. Default `"equal"`.
#' @param method Aggregation method. Default `"saw"`.
#' @param fragility_threshold Weight change below which the top rank is flagged
#'   as fragile. Default `0.05`.
#' @param ... Further arguments forwarded to the Python function, for example
#'   `bounds`, `normalization`, `baselines`, `search_range`, `tolerance`.
#'
#' @return The Python `WeightPerturbationReport`. Read its fields with `$`.
#'
#' @seealso [beam_smaa], [beam_rank].
#'
#' @export
beam_smallest_weight_perturbation <- function(scores, polarity, weights = "equal",
                                              method = "saw",
                                              fragility_threshold = 0.05, ...) {
  .require_beam()
  mcda <- reticulate::import("beam.mcda")
  mcda$smallest_weight_perturbation(
    scores = scores,
    polarity = as.character(polarity),
    weights = weights,
    method = method,
    fragility_threshold = fragility_threshold,
    ...
  )
}
