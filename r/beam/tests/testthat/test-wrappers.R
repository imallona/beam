# The wrappers forward to the Python beam package via reticulate. Every test
# that touches Python skips cleanly when the package (with its submodules) is
# not importable, so the suite is a no-op on CRAN and full coverage in CI where
# beam is installed.

skip_if_no_beam <- function() {
  testthat::skip_if_not(
    reticulate::py_module_available("beam.cards"),
    "Python beam package not available; run install_beam_python() first"
  )
}

skip_if_no_r_backend <- function() {
  skip_if_no_beam()
  het <- reticulate::import("beam.heterogeneity")
  testthat::skip_if_not(isTRUE(het$r_available()), "R heterogeneity backend not available")
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
  expect_equal(length(result$ranking), 3)
  expect_false(is.null(result$manifest))
})

test_that("beam_rank runs across aggregation methods", {
  skip_if_no_beam()
  scores <- write_scores()
  for (m in c("saw", "topsis", "vikor", "promethee_ii")) {
    result <- beam_rank(scores, method = m, sensitivity = FALSE)
    expect_equal(length(result$ranking), 3, info = m)
  }
})

test_that("beam_rank runs across objective weight schemes", {
  skip_if_no_beam()
  scores <- write_scores()
  for (w in c("entropy", "standard_deviation", "critic")) {
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

# Heterogeneity wrappers drive R (lme4, psychotree, PlackettLuce) through a
# Python subprocess. They skip unless that backend is installed.

het_matrix <- function() {
  m <- matrix(
    c(0.80, 0.70, 0.60, 0.55,
      0.78, 0.68, 0.58, 0.50,
      0.83, 0.74, 0.61, 0.57,
      0.79, 0.69, 0.59, 0.52,
      0.81, 0.72, 0.62, 0.56),
    nrow = 4
  )
  list(
    scores = m,
    methods = c("a", "b", "c", "d"),
    datasets = c("d1", "d2", "d3", "d4", "d5")
  )
}

test_that("beam_mixed_effects fits when the R backend is present", {
  skip_if_no_r_backend()
  h <- het_matrix()
  report <- beam_mixed_effects(h$scores, h$methods, h$datasets)
  expect_false(is.null(report))
})

test_that("beam_plackett_luce fits when the R backend is present", {
  skip_if_no_beam()
  het <- reticulate::import("beam.heterogeneity")
  skip_if_not(isTRUE(het$plackett_luce_available()), "PlackettLuce not available")
  h <- het_matrix()
  report <- beam_plackett_luce(h$scores, h$methods, h$datasets)
  expect_false(is.null(report))
})

test_that("beam_bradley_terry_tree fits when the R backend is present", {
  skip_if_no_beam()
  het <- reticulate::import("beam.heterogeneity")
  skip_if_not(isTRUE(het$bttree_available()), "psychotree not available")
  h <- het_matrix()
  features <- list(size = c(100, 200, 300, 400, 500))
  report <- beam_bradley_terry_tree(h$scores, h$methods, h$datasets, features)
  expect_false(is.null(report))
})

test_that("beam_source_variance_decomposition fits when the R backend is present", {
  skip_if_no_r_backend()
  methods <- rep(c("a", "b", "c"), times = 4)
  benchmarks <- rep(c("bench1", "bench2"), each = 6)
  datasets <- rep(c("d1", "d2"), each = 3, times = 2)
  scores <- c(0.8, 0.7, 0.6, 0.82, 0.72, 0.62, 0.78, 0.68, 0.58, 0.81, 0.71, 0.61)
  report <- beam_source_variance_decomposition(methods, datasets, benchmarks, scores)
  expect_false(is.null(report))
})
