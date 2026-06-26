# Convergent and discriminant validity of a metric set

Most benchmarks use different performance metrics to score the methods and, in some cases,  metrics are grouped depending on the meaning. The single-cell [scIB integration benchmark](../../examples/openproblems/openproblems.qmd) scores groups its metrics into biological conservation and batch correction. The grouping carries an assumption: the metrics in one group measure the same thing, and the metrics in different groups measure different things. `beam.mcda.metric_validity` tests that assumption against the scores, following Campbell and Fiske (1959).

## Implementation

Each method-by-dataset cell is one observation, and the metrics are the variables. The function updates every metric so that higher means better, reading the polarity from the cards and negating a lower-is-better metric. It then computes the Spearman rank correlation between every pair of metrics over the observations they share.

Spearman, a rank correlation, allows to search for association no matter the metric scale.  The correlation is pairwise-complete, and left as NaN otherwise.

## Usage

The function requires a label per metric, supplied by the user This is a domain judgement, so beam takes it as an argument rather than reading it from the cards. Typically, labels reflect computational characteristics (max set size, wallclock time; and biology-driven metrics). Grouping the correlations by that label splits them in two.

Within-group correlations are the convergent evidence. Metrics that claim to measure one construct should agree with each other. Between-group correlations are the discriminant evidence. Metrics that claim to measure different constructs should agree less. When the mean within-group correlation is higher than the mean between-group correlation, the grouping holds up, and treating the groups as separate criteria in the [weighting](weighting-schemes.md) is supported by the data rather than asserted. `discriminant_ok` records that comparison.

beam reports two kinds of metric discrimination problems or properties:
- A redundant pair is two metrics in the same group whose correlation is at or above a threshold (0.9 by default). They order the methods almost identically, so carrying both adds little and double-counts one construct. One is a candidate to drop.
- A crossloading metric correlates more, on average, with another group than with its own. It behaves more like a different construct than the one its label claims. This is the per-metric form of a discriminant-validity failure, and it points at a metric that is mislabelled or genuinely ambiguous.

## Example

On the [OpenProblems batch integration scores](../../examples/openproblems/openproblems.qmd), the bio/batch grouping is supported but weak: mean within-group correlation 0.38 against mean between-group correlation 0.30. The biological metrics agree more among themselves (0.45) than the batch metrics do (0.24), and `graph_connectivity`, a batch metric, correlates more with the biological group than with its own. The reading is that the two axes are separable rather than cleanly distinct.

## See also

- [Reliability](reliability.md)
- [Dimensionality](dimensionality.md)

## References

- Campbell, D. T., Fiske, D. W.. Convergent and discriminant validation by the multitrait-multimethod matrix. Psychological Bulletin (1959). DOI [10.1037/h0046016](https://doi.org/10.1037/h0046016).
