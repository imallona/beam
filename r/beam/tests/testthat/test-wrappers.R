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
