# Weighting schemes

After every metric is [normalized](normalization-and-scales.md) and scaled, the multi-criteria decision analysis (MCDA) pipeline [combines the columns](aggregation-methods.md) into one score per tool. The weights decide how much each metric counts. Weighting strategies belong to two families:

1. Objective schemes read the weights off the score matrix itself, so two analysts handed the same matrix get the same weights. 
2. The subjective scheme AHP asks the analyst for pairwise judgments instead, so the weights carry an explicit opinion about which metrics matter.

## Objective

Objective schemes take the same normalized tool by metric matrix and return a non-negative weight vector that sums to 1. They differ in what they treat as informative.

Equal weights give every metric the same share. This is the default when there is no reason to prefer one metric over another, and it is the baseline the other schemes are measured against. It ignores the data.

Entropy weights, in the Shannon sense, give a metric more weight when its scores spread out across the tools and less weight when the tools score alike. A metric on which every tool scores the same cannot separate the tools, so it receives almost no weight. Entropy first turns each column into a probability mass, so the weights do not change if a single column is rescaled by a positive constant. It fits when the weights follow from the data and the result is unaffected by the units of any one metric.

Standard deviation weights follow the same idea as entropy, that a metric that spreads the tools out should count more, but measure the spread directly with the sample standard deviation. They assume the columns are already on a common scale, which they are after normalization. It suits a plain, readable measure of spread.

CRITIC weights add a second idea on top of spread: conflict. CRITIC stands for CRiteria Importance Through Intercriteria Correlation. A metric increases its weight when its scores spread out and when it disagrees with the other metrics. If two metrics rank the tools the same way, they carry the same information, and counting both at full weight would double count that information. CRITIC measures the disagreement as one minus the correlation between columns and multiplies it by the standard deviation. This downweights redundant metrics that track the same underlying property.

MEREC weights use a different approach. MEREC stands for Method based on the Removal Effects of Criteria. It scores how much the overall ranking changes when each metric is removed. A metric whose removal barely moves the scores provides little information and gets a small weight. A metric whose removal shifts the scores a lot gets a large weight. The aggregate it uses is logarithmic, so it needs strictly positive scores. A column normalized with plain min-max can contain a hard zero, which MEREC cannot take the logarithm of. Pair it with a normalization that stays away from zero, such as the logistic z-score strategy. MEREC fits when a weight should reflect each metric's marginal effect on the result rather than its raw spread.

## Subjective (AHP)

AHP, the Analytic Hierarchy Process, does not read the score matrix. It asks the analyst to compare the metrics in pairs and state how many times more important one is than another, on Saaty's 1 to 9 scale. These judgments (analyst choices) fill a square pairwise comparison matrix that must be reciprocal: if metric A is judged three times as important as B, then B is one third as important as A, and the diagonal is all ones. The weights are the principal eigenvector of this matrix, normalized to sum to 1.

Because the judgments are made one pair at a time, they can contradict each other. If A is rated twice as important as B, and B twice as important as C, then consistency would put A four times as important as C, but the analyst might write something else. AHP measures this with a consistency ratio. A perfectly consistent matrix has a ratio of 0. Saaty's rule is that a ratio above 0.1 means the judgments are too inconsistent and should be revised. beam returns the consistency ratio next to the weights and warns, or raises an exception on request, when it goes above 0.1.

AHP fits when the choice of weights is a stakeholder decision rather than a property of the data, for example when a benchmark must reflect that accuracy matters more than runtime, or the way around. Its cost is that someone has to supply and defend the pairwise judgments, and the consistency check is what keeps those judgments coherent.

## Choosing a scheme

Equal weights are the default baseline. An objective scheme fits when the data sets the weights: entropy or standard deviation for plain spread, CRITIC when metrics may be redundant, MEREC when each metric's marginal effect matters. AHP fits when the weights encode a deliberate value judgment that the objective schemes cannot represent, with the consistency ratio reported.

## See also

- [Rank sensitivity](rank-sensitivity.md)
- [Specification curve](rank-sensitivity.md#the-specification-curve)

## References

- Diakoulaki, D., Mavrotas, G., Papayannakis, L. Determining objective weights in multiple criteria problems: the CRITIC method. Computers and Operations Research 22 (1995). DOI [10.1016/0305-0548(94)00059-H](https://doi.org/10.1016/0305-0548%2894%2900059-H).
- Keshavarz-Ghorabaee, M., Amiri, M., Zavadskas, E. K., Turskis, Z., Antucheviciene, J. Determination of Objective Weights Using a New Method Based on the Removal Effects of Criteria (MEREC). Symmetry 13 (2021). DOI [10.3390/sym13040525](https://doi.org/10.3390/sym13040525).
- Saaty, T. L. The Analytic Hierarchy Process. McGraw-Hill (1980).
