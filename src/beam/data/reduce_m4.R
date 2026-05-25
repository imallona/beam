# Reduce the GPL-3 M4comp2018 data to a small method-by-frequency results table.
#
# Source: M4comp2018 (GPL-3), github.com/carlanetto/M4comp2018, commit
# 3c75dcd25c72c631f04bff1a017d9917d0e7251c (data pulled via git-lfs).
# pt_ff holds the point forecasts of the top 25 methods (by OWA rank); xx is the
# truth; submission_info[1:25, ] gives the method labels in the same rank order.
#
# Metrics (Makridakis, Spiliotis, Assimakopoulos 2020, IJF):
#   sMAPE_i = mean_t 2*|F-A| / (|F|+|A|) * 100
#   MASE_i  = mean_t |F-A| / ( (1/(n-m)) sum_{t=m+1}^n |Y_t - Y_{t-m}| )
# with seasonal period m = 1 (Yearly, Weekly, Daily), 4 (Quarterly), 12
# (Monthly), 24 (Hourly). Writes a few-KB CSV; the 458 MB source is never shipped.

base <- "/home/imallona/tmp/M4comp2018/data"
load(file.path(base, "submission_info.rda"))
load(file.path(base, "M4.rda"))

n_methods <- nrow(M4[[1]]$pt_ff)
author <- as.character(submission_info[["Author(s)"]])[seq_len(n_methods)]
label <- sub(" - .*$", "", author)
label <- sub("[,&].*$", "", label)
label <- make.unique(trimws(label), sep = "_")

period_levels <- levels(M4[[1]]$period)
seasonal_m <- c(Daily = 1, Hourly = 24, Monthly = 12, Quarterly = 4, Weekly = 1, Yearly = 1)
n_periods <- length(period_levels)

sum_smape <- matrix(0, n_methods, n_periods, dimnames = list(label, period_levels))
sum_mase <- matrix(0, n_methods, n_periods, dimnames = list(label, period_levels))
cnt <- matrix(0L, n_methods, n_periods, dimnames = list(label, period_levels))

for (s in M4) {
  A <- s$xx
  F <- s$pt_ff
  h <- length(A)
  Amat <- matrix(A, nrow = n_methods, ncol = h, byrow = TRUE)
  smape <- rowMeans(2 * abs(F - Amat) / (abs(F) + abs(Amat)), na.rm = TRUE) * 100
  m <- seasonal_m[[as.character(s$period)]]
  denom <- mean(abs(diff(as.numeric(s$x), lag = m)))
  mase <- rowMeans(abs(F - Amat), na.rm = TRUE) / denom
  p <- as.integer(s$period)
  valid <- is.finite(smape) & is.finite(mase)
  sum_smape[valid, p] <- sum_smape[valid, p] + smape[valid]
  sum_mase[valid, p] <- sum_mase[valid, p] + mase[valid]
  cnt[valid, p] <- cnt[valid, p] + 1L
}

mean_smape <- sum_smape / cnt
mean_mase <- sum_mase / cnt

rows <- list()
for (i in seq_len(n_methods)) {
  for (p in period_levels) {
    rows[[length(rows) + 1]] <- data.frame(
      method = label[i], frequency = p,
      smape = round(mean_smape[i, p], 4), mase = round(mean_mase[i, p], 4),
      n_series = cnt[i, p], stringsAsFactors = FALSE
    )
  }
}
out <- do.call(rbind, rows)
write.csv(out, "/home/imallona/tmp/m4_by_frequency.csv", row.names = FALSE)

# Validate against published overall figures (winner sMAPE ~ 11.37, MASE ~ 1.54).
overall_smape <- rowSums(sum_smape) / rowSums(cnt)
overall_mase <- rowSums(sum_mase) / rowSums(cnt)
cat("series per frequency:\n"); print(colSums(cnt) / n_methods)
cat("\noverall (all 100k series), top 5 methods by rank:\n")
for (i in 1:5) cat(sprintf("  %-16s sMAPE=%.3f  MASE=%.3f\n", label[i], overall_smape[i], overall_mase[i]))
cat("\nper-frequency sMAPE, top 3 methods and the 3 benchmarks tail:\n")
print(round(mean_smape[c(1:3, (n_methods - 2):n_methods), ], 2))
