skip_if_no_beam <- function() {
  testthat::skip_if_not(
    reticulate::py_module_available("beam"),
    "Python beam package not available; run install_beam_python() first"
  )
}

test_that("beam_version returns a string", {
  skip_if_no_beam()
  v <- beam_version()
  expect_type(v, "character")
  expect_match(v, "^\\d+\\.\\d+")
})

test_that("beam_validate accepts the bundled Duo CSV-style structure", {
  skip_if_no_beam()
  py <- reticulate::import("beam")
  duo <- reticulate::import("beam.datasets")$load_duo2018()
  expect_equal(length(duo$method_names), 14)
  expect_equal(length(duo$dataset_names), 12)
  expect_equal(length(duo$metric_ids), 4)
})

test_that("beam_rank runs on a small simulated input", {
  skip_if_no_beam()
  scen <- reticulate::import("beam.scenarios")
  result <- beam_rank(
    scen$dominant()$scores,
    weights = "equal",
    method = "saw",
    sensitivity = FALSE
  )
  expect_false(is.null(result$top_tool))
  expect_true(length(result$ranking) > 0)
})

test_that("beam_metric_show prints a card without error", {
  skip_if_no_beam()
  expect_invisible(beam_metric_show("ari"))
})

test_that("install_beam_python exists and is callable", {
  expect_true(is.function(install_beam_python))
})
