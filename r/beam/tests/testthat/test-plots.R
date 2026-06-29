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
