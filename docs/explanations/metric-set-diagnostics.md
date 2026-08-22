# Metric-set diagnostics: validity, reliability, and dimensionality

A benchmark often treats a group of metrics as one criterion. The [scIB integration benchmark](../../examples/openproblems/openproblems.qmd) splits its metrics into biological conservation and batch correction and weights the groups 0.6 and 0.4. beam has three checks on such a grouping, all from one correlation matrix between the metrics.

## Correlation

Each method-by-dataset cell is an observation and the metrics are the variables. Every metric is oriented so that higher is better, with the polarity from the cards. The Spearman correlation is computed for every pair of metrics over the observations they share; a pair with none is NaN.

The grouping is a label per metric, passed as an argument. beam does not read it from the cards.

## Validity

[`beam.mcda.metric_validity`](../reference/metric_validity.qmd) follows Campbell and Fiske (1959). Correlations within a group are the convergent evidence and correlations between groups the discriminant evidence. `discriminant_ok` is true when the mean within-group correlation is higher than the mean between-group correlation.

The report lists:

- Redundant pairs: two metrics in the same group with a correlation of at least 0.9 (default).
- Crossloading metrics: a metric that correlates more, on average, with another group than with its own.

On the [OpenProblems batch integration scores](../../examples/openproblems/openproblems.qmd) the mean within-group correlation is 0.38 and the mean between-group correlation 0.30; 0.45 among the biological metrics and 0.24 among the batch metrics.

## Reliability

[`beam.mcda.metric_reliability`](../reference/metric_reliability.qmd) reports standardized Cronbach's alpha per group (Cronbach 1951):

    alpha = k * r_bar / (1 + (k - 1) * r_bar)

with `k` the number of metrics in the group and `r_bar` their mean inter-item correlation. The standardized form uses correlations, as the metrics have different scales.

Groups with alpha below 0.7 are flagged. Alpha increases with `k`, so the report gives `r_bar` and `k` with each alpha; `r_bar` compares groups of different size.

For a group of three or more metrics the report gives alpha with each metric removed. A metric whose removal raises alpha agrees less with the rest of its group.

Alpha is not a validity check.

On the OpenProblems scores the biological group has alpha 0.85 over seven metrics and the batch group 0.62 over five. Removing `pcr` raises the batch alpha to 0.67.

## Dimensionality

Alpha assumes the group is one factor. [`beam.mcda.metric_dimensionality`](../reference/metric_dimensionality.qmd) counts the factors.

For each group it takes the eigenvalues of the within-group correlation matrix, which sum to `k`. The report has the eigenvalues, the share of variance of the first component, and two counts of factors.

The Kaiser (1960) rule keeps the components with an eigenvalue above one and tends to keep too many. Parallel analysis (Horn 1965) keeps a component when its eigenvalue exceeds the 95th percentile (Glorfeld 1995) of the eigenvalues of random matrices of the same size, drawn with a fixed seed. A group is unidimensional when parallel analysis keeps one component.

A group with too few observations for its size is not scored, and a group with a pair of metrics without enough shared observations is undefined. The correlations are pairwise, so a late eigenvalue can be slightly negative.

On the OpenProblems scores parallel analysis keeps two components for the biological group (the first explains 0.54 of the variance) and one for the batch group.

## References

- Campbell, D. T., Fiske, D. W. Convergent and discriminant validation by the multitrait-multimethod matrix. Psychological Bulletin (1959). DOI [10.1037/h0046016](https://doi.org/10.1037/h0046016).
- Cronbach, L. J. Coefficient alpha and the internal structure of tests. Psychometrika (1951). DOI [10.1007/BF02310555](https://doi.org/10.1007/BF02310555).
- Kaiser, H. F. The application of electronic computers to factor analysis. Educational and Psychological Measurement (1960). DOI [10.1177/001316446002000116](https://doi.org/10.1177/001316446002000116).
- Horn, J. L. A rationale and test for the number of factors in factor analysis. Psychometrika (1965). DOI [10.1007/BF02289447](https://doi.org/10.1007/BF02289447).
- Glorfeld, L. W. An improvement on Horn's parallel analysis methodology for selecting the correct number of factors to retain. Educational and Psychological Measurement (1995). DOI [10.1177/0013164495055003002](https://doi.org/10.1177/0013164495055003002).
