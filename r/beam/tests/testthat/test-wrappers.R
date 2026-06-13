# MCDA wrappers skip without the Python beam package; native-R heterogeneity
# tests skip without their Suggests package.

skip_if_no_beam <- function() {
  testthat::skip_if_not(
    reticulate::py_module_available("beam.cards"),
    "Python beam package not available; run install_beam_python() first"
  )
}

write_scores <- function() {
  path <- tempfile(fileext = ".csv")
  utils::write.csv(
    data.frame(
      tool = c("a", "b", "c"),
      ari = c(0.81, 0.74, 0.69),
      runtime = c(42, 310, 88)
    ),
    path,
    row.names = FALSE
  )
  path
}

test_that("install_beam_python is an exported function", {
  expect_true(is.function(install_beam_python))
})

test_that("beam_version returns a version string", {
  skip_if_no_beam()
  v <- beam_version()
  expect_type(v, "character")
  expect_match(v, "^\\d+\\.\\d+")
})

test_that("beam_metric_show prints a card and returns it invisibly", {
  skip_if_no_beam()
  expect_invisible(beam_metric_show("ari"))
  out <- capture.output(beam_metric_show("runtime"))
  expect_true(any(grepl("runtime", out)))
  expect_true(any(grepl("polarity", out)))
})

test_that("beam_validate accepts a well-formed score CSV", {
  skip_if_no_beam()
  res <- beam_validate(write_scores())
  expect_true(res$ok)
  expect_true("ari" %in% res$metrics)
})

test_that("beam_validate errors on an unknown metric id", {
  skip_if_no_beam()
  path <- tempfile(fileext = ".csv")
  utils::write.csv(
    data.frame(tool = c("a", "b"), not_a_metric = c(1, 2)),
    path,
    row.names = FALSE
  )
  expect_error(beam_validate(path))
})

test_that("beam_rank ranks all tools under the default pipeline", {
  skip_if_no_beam()
  result <- beam_rank(write_scores(), sensitivity = FALSE)
  expect_false(is.null(result$top_tool))
  expect_equal(length(result$tool_names), 3)
  expect_false(is.null(result$manifest))
})

test_that("beam_rank runs across aggregation methods", {
  skip_if_no_beam()
  scores <- write_scores()
  for (m in c("saw", "topsis", "vikor", "promethee_ii")) {
    result <- beam_rank(scores, method = m, sensitivity = FALSE)
    expect_equal(length(result$tool_names), 3, info = m)
  }
})

test_that("beam_rank runs across objective weight schemes", {
  skip_if_no_beam()
  scores <- write_scores()
  for (w in c("entropy", "std", "critic")) {
    result <- beam_rank(scores, weights = w, sensitivity = FALSE)
    expect_false(is.null(result$top_tool), info = w)
  }
})

test_that("beam_rank with sensitivity produces the sensitivity reports", {
  skip_if_no_beam()
  result <- beam_rank(write_scores(), sensitivity = TRUE, seed = 1L)
  expect_false(is.null(result$smaa))
})

test_that("beam_report writes a self-contained HTML file", {
  skip_if_no_beam()
  result <- beam_rank(write_scores(), sensitivity = FALSE)
  out <- tempfile(fileext = ".html")
  beam_report(result, out)
  expect_true(file.exists(out))
  expect_gt(file.info(out)$size, 0)
})

test_that("beam_run executes a declarative beam.yaml", {
  skip_if_no_beam()
  dir <- tempfile()
  dir.create(dir)
  utils::write.csv(
    data.frame(tool = c("a", "b"), ari = c(0.8, 0.6), runtime = c(10, 5)),
    file.path(dir, "scores.csv"),
    row.names = FALSE
  )
  writeLines(c("inputs:", "  scores: scores.csv"), file.path(dir, "beam.yaml"))
  result <- beam_run(file.path(dir, "beam.yaml"))
  expect_false(is.null(result$top_tool))
})

test_that("beam.datasets exposes the bundled Duo 2018 benchmark", {
  skip_if_no_beam()
  duo <- reticulate::import("beam.datasets")$load_duo2018()
  expect_equal(length(duo$method_names), 14)
  expect_equal(length(duo$dataset_names), 12)
  expect_equal(length(duo$metric_ids), 4)
})

het_matrix <- function() {
  matrix(
    c(0.80, 0.70, 0.60, 0.55,
      0.78, 0.68, 0.58, 0.50,
      0.83, 0.74, 0.61, 0.57,
      0.79, 0.69, 0.59, 0.52,
      0.81, 0.72, 0.62, 0.56),
    nrow = 4
  )
}

test_that("beam_mixed_effects decomposes the variance with lme4", {
  skip_if_not_installed("lme4")
  fit <- beam_mixed_effects(het_matrix(), c("a", "b", "c", "d"), paste0("d", 1:5))
  expect_s3_class(fit, "beam_mixed_effects")
  expect_length(fit$method_effects, 4)
  expect_true("dataset" %in% names(fit$variance_components))
  expect_true(is.numeric(fit$icc_dataset))
})

test_that("beam_mixed_effects runs the glmmTMB beta engine", {
  skip_if_not_installed("glmmTMB")
  fit <- beam_mixed_effects(het_matrix(), c("a", "b", "c", "d"), paste0("d", 1:5),
                            engine = "glmmtmb", family = "beta")
  expect_s3_class(fit, "beam_mixed_effects")
  expect_equal(fit$scale, "link")
})

test_that("beam_plackett_luce returns a worth per method", {
  skip_if_not_installed("PlackettLuce")
  scores <- matrix(c(0.80, 0.70, 0.60, 0.78, 0.68, 0.58,
                     0.83, 0.74, 0.61, 0.79, 0.69, 0.59), nrow = 3)
  fit <- beam_plackett_luce(scores, c("a", "b", "c"))
  expect_s3_class(fit, "beam_plackett_luce")
  expect_length(fit$worth, 3)
})

test_that("beam_bradley_terry_tree fits a tree", {
  skip_if_not_installed("psychotree")
  set.seed(1)
  scores <- matrix(stats::runif(4 * 8), nrow = 4)
  fit <- beam_bradley_terry_tree(scores, c("a", "b", "c", "d"), paste0("d", 1:8),
                                 features = list(size = seq_len(8)), minsize = 3)
  expect_s3_class(fit, "beam_bradley_terry_tree")
  expect_length(fit$global_worth, 4)
  expect_type(fit$did_split, "logical")
})

test_that("beam_source_variance_decomposition fits the nested model", {
  skip_if_not_installed("lme4")
  methods <- rep(c("a", "b", "c"), times = 4)
  benchmarks <- rep(c("bench1", "bench2"), each = 6)
  datasets <- rep(c("d1", "d2"), each = 3, times = 2)
  scores <- c(0.8, 0.7, 0.6, 0.82, 0.72, 0.62, 0.78, 0.68, 0.58, 0.81, 0.71, 0.61)
  fit <- beam_source_variance_decomposition(methods, datasets, benchmarks, scores)
  expect_s3_class(fit, "beam_source_variance")
  expect_length(fit$method_effects, 3)
})

test_that("beam_network_meta_analysis pools studies into a ranking", {
  skip_if_not_installed("meta")
  skip_if_not_installed("netmeta")
  treatment <- rep(c("a", "b", "c"), times = 4)
  study <- rep(paste0("study", 1:4), each = 3)
  mean <- rep(c(1, 2, 3), times = 4) + rep(0.1 * (0:3), each = 3)
  sd <- rep(0.3, 12)
  n <- rep(4, 12)
  fit <- beam_network_meta_analysis(treatment, study, mean, sd, n)
  expect_s3_class(fit, "beam_network_meta")
  expect_length(fit$pscore, 3)
  # a has the lowest mean rank, so it leads on the P-score.
  expect_equal(fit$treatments[which.max(fit$pscore)], "a")
})

test_that("beam_metric_validity is an exported function", {
  expect_true(is.function(beam_metric_validity))
})

test_that("beam_metric_validity separates two clean constructs", {
  skip_if_no_beam()
  set.seed(1)
  bio <- rnorm(40)
  batch <- rnorm(40)
  scores <- cbind(
    bio + rnorm(40, 0, 0.1), bio + rnorm(40, 0, 0.1),
    batch + rnorm(40, 0, 0.1), batch + rnorm(40, 0, 0.1)
  )
  report <- beam_metric_validity(
    scores,
    polarity = rep("higher_is_better", 4),
    groups = c("bio", "bio", "batch", "batch")
  )
  expect_true(report$discriminant_ok)
  expect_gt(report$mean_convergent, report$mean_discriminant)
  expect_equal(report$n_observations, 40L)
})

test_that("metric-set diagnostic wrappers are exported functions", {
  expect_true(is.function(beam_metric_reliability))
  expect_true(is.function(beam_metric_dimensionality))
  expect_true(is.function(beam_metric_diagnostics))
})

test_that("beam_metric_reliability scores one strong factor as reliable", {
  skip_if_no_beam()
  set.seed(1)
  factor <- rnorm(60)
  scores <- cbind(
    factor + rnorm(60, 0, 0.2), factor + rnorm(60, 0, 0.2),
    factor + rnorm(60, 0, 0.2)
  )
  report <- beam_metric_reliability(
    scores,
    polarity = rep("higher_is_better", 3),
    groups = rep("bio", 3)
  )
  expect_gt(report$alpha_by_group$bio, 0.8)
  expect_equal(report$n_observations, 60L)
})

test_that("beam_metric_dimensionality finds one factor in a one-factor group", {
  skip_if_no_beam()
  set.seed(1)
  factor <- rnorm(60)
  scores <- cbind(
    factor + rnorm(60, 0, 0.2), factor + rnorm(60, 0, 0.2),
    factor + rnorm(60, 0, 0.2), factor + rnorm(60, 0, 0.2)
  )
  report <- beam_metric_dimensionality(
    scores,
    polarity = rep("higher_is_better", 4),
    groups = rep("bio", 4)
  )
  expect_true("bio" %in% report$unidimensional_groups)
})

test_that("beam_metric_diagnostics returns the three reports together", {
  skip_if_no_beam()
  set.seed(1)
  bio <- rnorm(60)
  batch <- rnorm(60)
  scores <- cbind(
    bio + rnorm(60, 0, 0.1), bio + rnorm(60, 0, 0.1),
    batch + rnorm(60, 0, 0.1), batch + rnorm(60, 0, 0.1)
  )
  report <- beam_metric_diagnostics(
    scores,
    polarity = rep("higher_is_better", 4),
    groups = c("bio", "bio", "batch", "batch")
  )
  expect_true(report$validity$discriminant_ok)
  expect_false(is.null(report$reliability))
  expect_false(is.null(report$dimensionality))
})

test_that("the remaining MCDA analysis wrappers are exported functions", {
  for (fn in list(
    beam_beats_random_baseline, beam_noise_floor_separation,
    beam_card_data_consistency, beam_rank_sensitivity, beam_pairwise_superiority,
    beam_critical_difference, beam_skillings_mack,
    beam_coverage_aware_critical_difference, beam_aggregation_agreement,
    beam_smaa, beam_leave_one_metric_out, beam_leave_one_dataset_out,
    beam_smallest_weight_perturbation, beam_pairwise_transitivity,
    beam_bayesian_sign_comparison
  )) {
    expect_true(is.function(fn))
  }
})

test_that("beam_pairwise_superiority compares methods across datasets", {
  skip_if_no_beam()
  # method 0 beats 1 beats 2 on every dataset.
  scores <- rbind(c(0.9, 0.8, 0.7), c(0.5, 0.6, 0.4), c(0.2, 0.1, 0.3))
  report <- beam_pairwise_superiority(scores, "higher_is_better",
                                      method_names = c("a", "b", "c"))
  expect_s3_class(report, "python.builtin.object")
  expect_equal(report$probability_superior[1, 2], 1.0)
  expect_equal(as.integer(report$order[1]), 0L)
})

test_that("beam_pairwise_transitivity checks the pairwise majority relation", {
  skip_if_no_beam()
  # A transitive order: method 0 over 1 over 2 on every dataset.
  scores <- rbind(c(0.9, 0.8, 0.7), c(0.5, 0.6, 0.4), c(0.2, 0.1, 0.3))
  sup <- beam_pairwise_superiority(scores, "higher_is_better",
                                   method_names = c("a", "b", "c"))
  trans <- beam_pairwise_transitivity(sup)
  expect_s3_class(trans, "python.builtin.object")
  expect_true(trans$is_transitive)
  expect_equal(as.integer(trans$n_circular_triads), 0L)
  expect_equal(as.integer(trans$condorcet_choice), 0L)
})

test_that("beam_bayesian_sign_comparison reports posterior probabilities", {
  skip_if_no_beam()
  # method 0 beats 1 beats 2 on every one of several datasets.
  scores <- rbind(
    c(0.9, 0.85, 0.8, 0.95, 0.88, 0.9),
    c(0.5, 0.55, 0.45, 0.5, 0.52, 0.48),
    c(0.2, 0.1, 0.3, 0.15, 0.25, 0.2)
  )
  sup <- beam_pairwise_superiority(scores, "higher_is_better",
                                   method_names = c("a", "b", "c"))
  bayes <- beam_bayesian_sign_comparison(sup, seed = 0L)
  expect_s3_class(bayes, "python.builtin.object")
  expect_equal(as.integer(bayes$order[1]), 0L)
  expect_gt(bayes$probability_better[1, 2], 0.9)
})

test_that("reference-level wrappers run on a tool by metric matrix", {
  skip_if_no_beam()
  scores <- rbind(c(0.9, 50), c(0.8, 80), c(0.7, 120))
  polarity <- c("higher_is_better", "lower_is_better")
  beaten <- beam_beats_random_baseline(scores, polarity, baselines = c(0, 200))
  expect_s3_class(beaten, "python.builtin.object")
  separation <- beam_noise_floor_separation(scores, noise_floors = c(0.01, 1))
  expect_s3_class(separation, "python.builtin.object")
})

test_that("beam_card_data_consistency audits cards against the scores", {
  skip_if_no_beam()
  scores <- rbind(c(0.4, 0.6), c(0.9, 0.2), c(0.7, 0.8))
  polarity <- c("higher_is_better", "higher_is_better")
  bounds <- list(list(0, 1), list(0, 1))
  clean <- beam_card_data_consistency(scores, polarity, bounds,
                                      metric_ids = c("ari", "nmi"))
  expect_s3_class(clean, "python.builtin.object")
  expect_true(clean$ok)

  # the second metric reported on a percent scale falls outside its [0, 1] card.
  scores[, 2] <- scores[, 2] * 100
  flagged <- beam_card_data_consistency(scores, polarity, bounds,
                                        metric_ids = c("ari", "nmi"))
  expect_false(flagged$ok)
  expect_length(flagged$violations, 1)
})

test_that("beam_rank_sensitivity attributes a ranking's variance", {
  skip_if_no_beam()
  # a tensor whose two datasets order the tools oppositely: the dataset dominates.
  d0 <- rbind(c(0.9, 0.9), c(0.5, 0.5), c(0.1, 0.1))
  d1 <- rbind(c(0.1, 0.1), c(0.5, 0.5), c(0.9, 0.9))
  tensor <- array(0, dim = c(3, 2, 2))
  tensor[, 1, ] <- d0
  tensor[, 2, ] <- d1
  report <- beam_rank_sensitivity(
    tensor, c("higher_is_better", "higher_is_better"),
    dataset_names = c("d0", "d1")
  )
  expect_s3_class(report, "python.builtin.object")
  expect_equal(report$most_influential_factor, "dataset")
  expect_gt(report$dataset_share, 0.9)
})

test_that("critical difference and Skillings-Mack run on a tool by dataset matrix", {
  skip_if_no_beam()
  set.seed(1)
  scores <- matrix(rnorm(4 * 6), nrow = 4)
  cd <- beam_critical_difference(scores)
  expect_s3_class(cd, "python.builtin.object")
  scores[1, 1] <- NA
  sm <- beam_skillings_mack(scores)
  expect_s3_class(sm, "python.builtin.object")
})

test_that("sensitivity and aggregation-agreement wrappers run", {
  skip_if_no_beam()
  set.seed(1)
  scores <- matrix(runif(3 * 3), nrow = 3)
  polarity <- rep("higher_is_better", 3)
  expect_s3_class(
    beam_smaa(scores, polarity, n_samples = 50, seed = 1),
    "python.builtin.object"
  )
  expect_s3_class(
    beam_leave_one_metric_out(scores, polarity),
    "python.builtin.object"
  )
  expect_s3_class(
    beam_smallest_weight_perturbation(scores, polarity),
    "python.builtin.object"
  )
  expect_s3_class(
    beam_aggregation_agreement(scores, polarity),
    "python.builtin.object"
  )
})

test_that("beam_leave_one_dataset_out runs on a tool by dataset by metric array", {
  skip_if_no_beam()
  set.seed(1)
  tensor <- array(runif(3 * 4 * 2), dim = c(3, 4, 2))
  report <- beam_leave_one_dataset_out(
    tensor,
    polarity = rep("higher_is_better", 2),
    reduction_rules = rep("arithmetic_mean", 2)
  )
  expect_s3_class(report, "python.builtin.object")
})

test_that("beam_normalization_agreement returns a classed report and prints", {
  skip_if_no_beam()
  scores <- matrix(c(0.95, 10, 0.80, 20, 0.60, 30, 0.40, 40), ncol = 2, byrow = TRUE)
  polarity <- c("higher_is_better", "lower_is_better")
  report <- beam_normalization_agreement(scores, polarity, tool_names = c("a", "b", "c", "d"))
  expect_s3_class(report, "beam_normalization_agreement")
  expect_s3_class(report, "beam_report")
  out <- capture.output(print(report))
  expect_true(any(grepl("beam_normalization_agreement", out)))
  expect_true(any(grepl("Kendall tau-b", out)))
})

test_that("beam_aggregation_agreement gets the beam_report class", {
  skip_if_no_beam()
  scores <- matrix(c(0.9, 30, 0.7, 50, 0.5, 40, 0.3, 20), ncol = 2, byrow = TRUE)
  report <- beam_aggregation_agreement(scores, c("higher_is_better", "lower_is_better"))
  expect_s3_class(report, "beam_aggregation_agreement")
  expect_s3_class(report, "beam_report")
})

test_that("plot on an agreement report writes a file", {
  skip_if_no_beam()
  scores <- matrix(c(0.9, 30, 0.7, 50, 0.5, 40, 0.3, 20), ncol = 2, byrow = TRUE)
  report <- beam_normalization_agreement(scores, c("higher_is_better", "lower_is_better"))
  path <- tempfile(fileext = ".png")
  plot(report, path = path)
  expect_true(file.exists(path) && file.info(path)$size > 0)
})

test_that("beam_plot draws effect plots from a run", {
  skip_if_no_beam()
  run <- beam_rank(write_scores(), sensitivity = FALSE)
  path <- tempfile(fileext = ".png")
  beam_plot(run, "ranking", path)
  expect_true(file.exists(path) && file.info(path)$size > 0)
  expect_error(beam_plot(run, "not_a_plot"), "unknown plot kind")
})
