# Native plot builders. These need the Python beam package for the run, ggplot2
# for every plot, and patchwork for the funky heatmap panels; each skips when
# its dependency is missing.

skip_if_no_ggplot <- function() {
  testthat::skip_if_not(requireNamespace("ggplot2", quietly = TRUE), "ggplot2 not installed")
}

skip_if_no_patchwork <- function() {
  testthat::skip_if_not(requireNamespace("patchwork", quietly = TRUE), "patchwork not installed")
}

write_tensor <- function() {
  path <- tempfile(fileext = ".csv")
  rows <- expand.grid(tool = c("a", "b", "c", "d"),
                      dataset = c("d1", "d2", "d3"),
                      metric = c("ari", "nmi", "runtime"),
                      stringsAsFactors = FALSE)
  set.seed(1)
  rows$score <- ifelse(rows$metric == "runtime", runif(nrow(rows), 40, 300),
                       runif(nrow(rows), 0.4, 0.9))
  utils::write.csv(rows, path, row.names = FALSE)
  path
}

test_that("beam_funky_heatmap returns a plot object and writes a file", {
  skip_if_no_beam()
  skip_if_no_patchwork()
  run <- beam_rank(write_scores(), sensitivity = FALSE)
  fig <- beam_funky_heatmap(run)
  expect_s3_class(fig, "ggplot")
  out <- tempfile(fileext = ".png")
  beam_funky_heatmap(run, out)
  expect_true(file.exists(out))
})

test_that("run-based ggplot kinds return ggplot objects", {
  skip_if_no_beam()
  skip_if_no_ggplot()
  run <- beam_rank(write_scores(), sensitivity = FALSE)
  for (kind in c("ranking", "normalized_scores")) {
    expect_s3_class(beam_plot(run, kind), "ggplot")
  }
})

test_that("robustness and concordance kinds read a tensor run", {
  skip_if_no_beam()
  skip_if_no_ggplot()
  run <- beam_rank(write_tensor(), sensitivity = TRUE, missing = "available", seed = 1L)
  for (kind in c("smaa", "dataset_stability", "dataset_concordance",
                 "dataset_struggle", "dataset_effect")) {
    expect_s3_class(beam_plot(run, kind), "ggplot")
  }
})

metric_scores <- function() {
  set.seed(2)
  bio <- rnorm(30)
  batch <- rnorm(30)
  cbind(bio + rnorm(30, 0, 0.15), bio + rnorm(30, 0, 0.15), bio + rnorm(30, 0, 0.15),
        batch + rnorm(30, 0, 0.15), batch + rnorm(30, 0, 0.15), batch + rnorm(30, 0, 0.15))
}

test_that("metric-quality kinds draw from their reports", {
  skip_if_no_beam()
  skip_if_no_ggplot()
  scores <- metric_scores()
  pol <- rep("higher_is_better", 6)
  grp <- rep(c("bio", "batch"), each = 3)
  ids <- paste0("m", 1:6)
  val <- beam_metric_validity(scores, pol, grp, metric_ids = ids)
  rel <- beam_metric_reliability(scores, pol, grp, metric_ids = ids)
  dim_ <- beam_metric_dimensionality(scores, pol, grp, metric_ids = ids)
  expect_s3_class(beam_plot(val, "metric_correlation"), "ggplot")
  expect_s3_class(beam_plot(rel, "metric_reliability_dropped"), "ggplot")
  expect_s3_class(beam_plot(dim_, "metric_dimensionality_scree"), "ggplot")
})

test_that("specification curve and critical difference band draw", {
  skip_if_no_beam()
  skip_if_no_patchwork()
  set.seed(3)
  arr <- array(runif(4 * 3 * 2), dim = c(4, 3, 2))
  rs <- beam_rank_sensitivity(arr, c("higher_is_better", "lower_is_better"),
                              tool_names = paste0("t", 1:4),
                              dataset_names = paste0("d", 1:3))
  curve <- beam_specification_curve(rs)
  expect_s3_class(beam_plot(curve, "specification_curve"), "ggplot")

  complete <- matrix(runif(20), nrow = 4, dimnames = list(paste0("t", 1:4), NULL))
  cd <- beam_critical_difference(complete, higher_is_better = TRUE, tool_names = paste0("t", 1:4))
  expect_s3_class(beam_plot(cd, "critical_difference_band"), "ggplot")
})

test_that("difficulty concordance draws from two families", {
  skip_if_no_beam()
  skip_if_no_ggplot()
  set.seed(4)
  arr <- array(runif(4 * 6 * 2), dim = c(4, 6, 2))
  fam <- c("classical", "classical", "dl", "dl")
  dc <- beam_difficulty_concordance(arr, rep("higher_is_better", 2), fam,
                                    dataset_ids = paste0("u", 1:6))
  expect_s3_class(beam_plot(dc, "difficulty_concordance"), "ggplot")
})

test_that("funky heatmap draws clique brackets and a rank-sensitivity bar has coloured sources", {
  skip_if_no_beam()
  skip_if_no_patchwork()
  run <- beam_rank(write_tensor(), sensitivity = TRUE, missing = "available", seed = 1L)
  cliques <- list(c("a", "b"), c("c", "d"))
  expect_s3_class(beam_funky_heatmap(run, cliques = cliques), "ggplot")

  set.seed(5)
  arr <- array(runif(4 * 3 * 2), dim = c(4, 3, 2))
  rs <- beam_rank_sensitivity(arr, c("higher_is_better", "lower_is_better"),
                              tool_names = paste0("t", 1:4), dataset_names = paste0("d", 1:3))
  expect_s3_class(beam_plot(rs, "rank_sensitivity"), "ggplot")
})

test_that("grouped rank bars, variance highlight, theme and palette are exported", {
  bars <- beam_rank_bars(c("a", "b", "c"),
                         list(one = c(1, 2, 3), two = c(2, 1, 3)))
  expect_s3_class(bars, "ggplot")
  expect_s3_class(beam_theme(), "theme")
  expect_type(beam_palette(), "character")
  expect_named(beam_palette(roles = TRUE))
})

test_that("variance components highlight a named component", {
  skip_if_no_beam()
  skip_if_not(requireNamespace("lme4", quietly = TRUE), "lme4 not installed")
  set.seed(6)
  methods <- rep(c("a", "b", "c"), times = 6)
  benchmarks <- rep(c("x", "y"), each = 9)
  datasets <- paste0(benchmarks, rep(rep(1:3, each = 3), 2))
  scores <- runif(length(methods))
  sv <- beam_source_variance_decomposition(methods, datasets, benchmarks, scores)
  expect_s3_class(
    beam_plot(sv, "variance_components", highlight = "method:benchmark", annotation = "note"),
    "ggplot")
})

test_that("heterogeneity kinds draw when their R packages are present", {
  skip_if_no_beam()
  skip_if_no_ggplot()
  set.seed(5)
  ari <- matrix(runif(4 * 6, 0.3, 0.9), nrow = 4,
                dimnames = list(paste0("t", 1:4), paste0("d", 1:6)))
  if (requireNamespace("lme4", quietly = TRUE)) {
    me <- beam_mixed_effects(ari, paste0("t", 1:4), paste0("d", 1:6))
    expect_s3_class(beam_plot(me, "variance_components"), "ggplot")
  }
  if (requireNamespace("psychotree", quietly = TRUE)) {
    bt <- beam_bradley_terry_tree(ari, paste0("t", 1:4), paste0("d", 1:6),
                                  features = list(size = seq_len(6)), minsize = 3L)
    expect_s3_class(beam_plot(bt, "bradley_terry_leaves"), "ggplot")
  }
})

test_that("an unknown kind is rejected", {
  skip_if_no_beam()
  run <- beam_rank(write_scores(), sensitivity = FALSE)
  expect_error(beam_plot(run, "not_a_kind"), "unknown plot kind")
})

test_that("beam_rank_bump draws from a raw rank matrix and tags its size", {
  skip_if_no_ggplot()
  ranks <- matrix(c(1, 2, 3, 2, 1, 3), nrow = 3,
                  dimnames = list(c("a", "b", "c"), c("col1", "col2")))
  fig <- beam_rank_bump(rownames(ranks), colnames(ranks), ranks, divider_after = 1)
  expect_s3_class(fig, "ggplot")
  expect_true(is.numeric(attr(fig, "beam_width")))
})

test_that("beam_funky_table draws from a raw score matrix", {
  skip_if_no_patchwork()
  norm <- matrix(runif(6), nrow = 3, dimnames = list(c("a", "b", "c"), c("m1", "m2")))
  fig <- beam_funky_table(norm, rownames(norm), colnames(norm),
                          composite = rowMeans(norm), ranks = c(1, 2, 3))
  expect_s3_class(fig, "ggplot")
})
