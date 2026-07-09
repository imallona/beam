# Metric-set diagnostics: validity, reliability, and dimensionality

A benchmark often treats a group of metrics as one criterion. The single-cell [scIB integration benchmark](../../examples/openproblems/openproblems.qmd) splits its metrics into biological conservation and batch correction, and weights the two groups 0.6 and 0.4, so each is read as a single composite scale. That grouping is an assumption, and beam has three checks on it, all built from the same oriented correlation between the metrics:

- validity: are same-group metrics more alike than different-group metrics, so the split is the right one?
- reliability: does a group hold together consistently enough to read as one scale?
- dimensionality: is a group really one underlying factor, or several?

## The shared correlation

Each method-by-dataset cell is one observation, and the metrics are the variables. The function orients every metric so that higher means better, reading the polarity from the cards and negating a lower-is-better metric. It then takes the Spearman rank correlation between every pair of metrics over the observations they share. A rank correlation finds association regardless of the metric scale. Pairs with no shared observations are left as NaN.

The grouping itself is a label per metric, passed in as an argument. It is a domain judgement, so beam does not read it from the cards. In the scIB case the labels are biological conservation and batch correction.

## Validity

[`beam.mcda.metric_validity`](../reference/metric_validity.qmd) follows Campbell and Fiske (1959). Correlations within a group are the convergent evidence: metrics that claim to measure one construct should agree. Correlations between groups are the discriminant evidence: metrics that claim to measure different constructs should agree less. `discriminant_ok` is true when the mean within-group correlation is higher than the mean between-group correlation, which is when treating the groups as separate criteria in the [weighting](weighting-schemes.md) has support in the data.

beam reports two kinds of metric discrimination problems or properties:

- A redundant pair is two metrics in the same group whose correlation is at or above a threshold (0.9 by default). They order the methods almost identically, so carrying both adds little and double-counts one construct. One is a candidate to drop.
- A crossloading metric correlates more, on average, with another group than with its own. It behaves more like a different construct than the one its label claims. This is the per-metric form of a discriminant-validity failure, and it points at a metric that is mislabelled or genuinely ambiguous.

On the [OpenProblems batch integration scores](../../examples/openproblems/openproblems.qmd), the bio/batch grouping is supported but weak: mean within-group correlation 0.38 against mean between-group correlation 0.30. The biological metrics agree more among themselves (0.45) than the batch metrics do (0.24), and `graph_connectivity`, a batch metric, correlates more with the biological group than with its own.

## Reliability

[`beam.mcda.metric_reliability`](../reference/metric_reliability.qmd) reports standardized Cronbach's alpha per group, following Cronbach (1951):

    alpha = k * r_bar / (1 + (k - 1) * r_bar)

where `k` is the number of metrics in the group and `r_bar` is their mean inter-item correlation. The standardized form, built from correlations rather than from raw covariances, is appropriate here because the metrics are on different scales. It is the rank-based analogue of classical alpha.

Alpha runs up to 1. A common rule of thumb treats 0.7 as the point above which a group reads as one reliable scale, and `metric_reliability` flags any group below that cutoff. The cutoff is somewhat arbitrary, so the report carries `r_bar` and `k` next to each alpha.

Alpha rises with the mean correlation and with the number of metrics, so a long group can reach a high alpha on modest agreement, and a short group needs stronger agreement to reach the same cutoff. When two groups differ in size, the mean inter-item correlation is the comparison to use, because it does not carry the size effect.

For a group of three or more metrics, the report recomputes the group's alpha with each metric removed in turn. A metric whose removal raises the group's alpha agrees with its labelled construct less than the others do. It is the metric to reconsider first, whether to relabel it, drop it, or treat it as a separate criterion. A metric in a group of two has no alpha-if-dropped entry, because dropping one leaves a single metric and alpha is undefined for one item.

Alpha is not a validity check. A group can be reliable and still measure the wrong thing.

On the OpenProblems scores, where there is an expertly-curated classification of metrics in bio/batch, the biological conservation group is reliable: alpha 0.85 over seven metrics, mean inter-item correlation 0.45. The batch correction group does not reach the cutoff: alpha 0.62 over five metrics, mean inter-item correlation 0.24. Dropping `pcr` is the only batch removal that raises the batch alpha by more than a rounding step, from 0.62 to 0.67, so `pcr` is the batch metric least consistent with the rest of its group.

## Dimensionality

Alpha reads a group as one scale when it is high, but that rests on an assumption alpha cannot test: that the group is a single factor, one underlying quantity each metric measures with noise. [`beam.mcda.metric_dimensionality`](../reference/metric_dimensionality.qmd) tests it directly by counting the factors.

For each group the function takes the eigenvalues of the within-group correlation matrix. This is principal component analysis on the correlation matrix. A correlation matrix of `k` metrics has `k` eigenvalues that sum to `k`. One large eigenvalue with the rest small means a single factor underlies the group. Several eigenvalues of similar size mean several factors. The report carries, per group, the eigenvalues in descending order, the share of variance the first component explains (the first eigenvalue divided by `k`), and two counts of how many factors the group holds.

The Kaiser (1960) rule keeps every component whose eigenvalue is above one, the variance of a single standardized metric. It is the quick rule and tends to keep more components than the data supports, because in a finite sample the later eigenvalues sit above one by chance alone. Parallel analysis (Horn 1965) corrects for that. It draws many random matrices of the same size, with no real association between the columns, and reads off the eigenvalues they produce by chance at each rank. A component is kept when its observed eigenvalue is larger than the random level at that rank. `metric_dimensionality` uses the 95th percentile of the random eigenvalues, following Glorfeld (1995), which holds the false-retention rate down where Horn's original mean rule lets noise through. Parallel analysis is the count the report uses for its verdict: a group is reported as unidimensional when parallel analysis keeps only one component. The random draws have a fixed seed for reproducibility.

Dimensionality and reliability answer different questions and can disagree. A long group can reach a high alpha while holding more than one factor, and a short group can sit at a low alpha while holding a single factor its metrics track only weakly. The case this check exists to surface is a high alpha on a group that turns out to carry two factors. The group is internally consistent enough to pass as one scale, but it is not one thing, and the 0.6/0.4 weighting that treats it as a single criterion is then a coarser modelling choice than the alpha alone suggests.

Counting factors is not naming them: parallel analysis says how many dimensions a group has, not what they are. Reading the eigenvectors, or splitting and relabelling the group, is left to the user. The count is descriptive of the methods and datasets in the input: a small benchmark gives a coarse estimate, and a few observations relative to the number of metrics make the eigenvalues unstable, so the function declines to score a group when the input has too few observations for its size. The correlations are computed pairwise, so the within-group matrix need not be positive semidefinite and a late eigenvalue can come out slightly negative; the function reports the eigenvalues as they are. When a within-group pair has too few shared observations to correlate, the group cannot be decomposed, and the report lists it as undefined rather than guessing.

On the OpenProblems scores, with the same bio/batch grouping, the two groups come apart. The biological group has seven metrics and a high alpha of 0.85, but parallel analysis finds two factors: the first component explains 0.54 of the variance and a second component still stands clear of the chance level, so part of that alpha is the size of the group rather than one underlying quantity. The batch group has five metrics and a low alpha of 0.62, yet it reads as a single factor whose metrics track one dimension weakly.

## References

- Campbell, D. T., Fiske, D. W. Convergent and discriminant validation by the multitrait-multimethod matrix. Psychological Bulletin (1959). DOI [10.1037/h0046016](https://doi.org/10.1037/h0046016).
- Cronbach, L. J. Coefficient alpha and the internal structure of tests. Psychometrika (1951). DOI [10.1007/BF02310555](https://doi.org/10.1007/BF02310555).
- Kaiser, H. F. The application of electronic computers to factor analysis. Educational and Psychological Measurement (1960). DOI [10.1177/001316446002000116](https://doi.org/10.1177/001316446002000116).
- Horn, J. L. A rationale and test for the number of factors in factor analysis. Psychometrika (1965). DOI [10.1007/BF02289447](https://doi.org/10.1007/BF02289447).
- Glorfeld, L. W. An improvement on Horn's parallel analysis methodology for selecting the correct number of factors to retain. Educational and Psychological Measurement (1995). DOI [10.1177/0013164495055003002](https://doi.org/10.1177/0013164495055003002).
