# How many factors a metric group carries

A benchmark often reads a group of metrics as one criterion. The scIB integration score groups its metrics into biological conservation and batch correction and weights the two groups 0.6 and 0.4, so each group stands in for a single composite scale. The [reliability](reliability.md) check asks how consistently a group's metrics agree, and reports Cronbach's alpha. Alpha reads a group as one reliable scale when it is high, but that reading rests on an assumption alpha cannot test: that the group is a single factor, one underlying quantity each metric measures with noise. `beam.mcda.metric_dimensionality` tests the assumption directly by counting the factors in the group.

## What it computes

Each method-by-dataset cell is one observation, and the metrics are the variables. The function orients every metric so that higher means better, reading the polarity from the cards, then computes the Spearman rank correlation between every pair of metrics over the observations they share. This is the same oriented correlation that the validity and reliability checks use, so all three diagnostics rest on the same numbers.

For each group the function takes the eigenvalues of the within-group correlation matrix. This is principal component analysis on the correlation matrix. A correlation matrix of `k` metrics has `k` eigenvalues that sum to `k`, its trace. One large eigenvalue with the rest small means a single factor runs through the group. Several eigenvalues of similar size mean several factors. The report carries, per group, the eigenvalues in descending order, the share of variance the first component explains (the first eigenvalue divided by `k`), and two counts of how many factors the group holds.

## Counting the factors

The Kaiser (1960) rule keeps every component whose eigenvalue is above one, the variance of a single standardized metric. It is the quick rule and tends to keep too many components, because in a finite sample the later eigenvalues sit above one by chance alone.

Parallel analysis (Horn 1965) corrects for that. It draws many random matrices of the same size, with no real association between the columns, and reads off the eigenvalues they produce by chance at each rank. A component is kept when its observed eigenvalue is larger than the random level at that rank. `metric_dimensionality` uses the 95th percentile of the random eigenvalues, following Glorfeld (1995), which holds the false-retention rate down where Horn's original mean rule lets noise through. Parallel analysis is the count the report uses for its verdict: a group is reported as unidimensional when parallel analysis keeps exactly one component.

The random draws are seeded, so the report reproduces.

## Reading it against reliability

Dimensionality and reliability answer different questions, and they can disagree. Alpha rises with the mean correlation between the metrics and with the number of metrics. A long group can then reach a high alpha while holding more than one factor, and a short group can sit at a low alpha while holding a single factor its metrics track only weakly. The four combinations all occur: one factor read consistently, one factor read weakly, several factors that happen to agree, several factors that do not.

The case this check exists to surface is a high alpha on a group that turns out to carry two factors. The group is internally consistent enough to pass as one scale, but it is not one thing, and the 0.6/0.4 weighting that treats it as a single criterion is then a coarser modelling choice than the alpha alone suggests.

## What it does not do

Counting factors is not the same as naming them. Parallel analysis says how many dimensions the group holds, not what they are; reading the eigenvectors, or splitting and relabelling the group, is the analyst's next step. The count is also descriptive of the methods and datasets in the input. A small benchmark gives a coarse estimate, and a few observations relative to the number of metrics make the eigenvalues unstable, so the function declines to score a group when the input has too few observations for its size.

The correlations are computed pairwise, over the observations each metric pair shares, so the within-group matrix need not be positive semidefinite and a late eigenvalue can come out slightly negative. The function reports the eigenvalues as they are. When a within-group pair has too few shared observations to correlate, the group cannot be decomposed, and the report lists it as undefined rather than guessing.

## How to read it on real data

On the OpenProblems batch integration scores, with the same bio/batch grouping the validity and reliability checks use, the two groups split apart. The biological group, seven metrics with a high alpha of 0.85, carries two factors by parallel analysis: its first component explains 0.54 of the variance, but a second component stands clear of the chance level, so the high alpha is partly the size of the group rather than a single underlying quantity. The batch group, five metrics with a low alpha of 0.62, carries one factor: its metrics track a single dimension but weakly, which is why the alpha is low while the dimensionality is one. Reliability and dimensionality point in opposite directions on each group, and reading them together says more than either alone.

## References

- Kaiser, H. F.. The application of electronic computers to factor analysis. Educational and Psychological Measurement (1960). DOI [10.1177/001316446002000116](https://doi.org/10.1177/001316446002000116).
- Horn, J. L.. A rationale and test for the number of factors in factor analysis. Psychometrika (1965). DOI [10.1007/BF02289447](https://doi.org/10.1007/BF02289447).
- Glorfeld, L. W.. An improvement on Horn's parallel analysis methodology for selecting the correct number of factors to retain. Educational and Psychological Measurement (1995). DOI [10.1177/0013164495055003002](https://doi.org/10.1177/0013164495055003002).
