# Shared test helpers, loaded by testthat before every test file. MCDA wrappers
# skip without the Python beam package; native-R heterogeneity tests skip
# without their Suggests package.

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
