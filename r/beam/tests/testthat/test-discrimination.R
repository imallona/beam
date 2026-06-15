test_that("beam_dataset_discrimination and beam_difficulty_concordance are exported", {
  expect_true(is.function(beam_dataset_discrimination))
  expect_true(is.function(beam_difficulty_concordance))
})

test_that("beam_dataset_discrimination ranks the separating dataset first", {
  skip_if_no_beam()
  # Three methods, two datasets, one metric. Dataset 1 spreads the methods
  # (0.1, 0.5, 0.9); dataset 2 ties them (0.5 each).
  scores <- array(c(0.1, 0.5, 0.9, 0.5, 0.5, 0.5), dim = c(3, 2, 1))
  report <- beam_dataset_discrimination(
    scores,
    polarity = "higher_is_better",
    dataset_ids = c("spread", "tied")
  )
  expect_equal(report$most_discriminating, "spread")
  expect_equal(report$least_discriminating, "tied")
  expect_gt(report$spread[1], report$spread[2])
})

test_that("beam_difficulty_concordance scores shared difficulty as concordant", {
  skip_if_no_beam()
  # Four methods, four datasets, one metric. Every method follows the same
  # per-dataset difficulty profile, so the two families agree.
  base <- c(0.2, 0.4, 0.6, 0.8)
  scores <- array(rep(base, each = 4), dim = c(4, 4, 1))
  report <- beam_difficulty_concordance(
    scores,
    polarity = "higher_is_better",
    families = c("A", "A", "B", "B"),
    dataset_ids = c("w", "x", "y", "z")
  )
  expect_equal(as.character(report$family_names), c("A", "B"))
  expect_gt(report$mean_pairwise_concordance, 0.9)
})
