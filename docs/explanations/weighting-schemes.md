# Weighting schemes

After every metric is normalized to the unit interval, the MCDA pipeline combines the columns into one score per tool. The weights decide how much each metric counts. The schemes split into two families. Objective schemes read the weights off the score matrix itself, so two analysts handed the same matrix get the same weights. The subjective scheme, AHP, asks the analyst for pairwise judgments instead, so the weights carry an explicit opinion about which metrics matter.

## The objective schemes

All objective schemes take the same normalized tool by metric matrix and return a non-negative weight vector that sums to 1. They differ in what they treat as informative.

Equal weights give every metric the same share. This is the honest default when there is no reason to prefer one metric over another, and it is the baseline the other schemes are measured against. It ignores the data entirely.

Entropy weights, in the Shannon sense, give a metric more weight when its scores spread out across the tools and less weight when the tools score alike. A metric on which every tool scores the same cannot separate the tools, so it earns almost no weight. Entropy first turns each column into a probability mass, so the weights do not change if a single column is rescaled by a positive constant. Use it when you want the data to decide and you want the result to be insensitive to the units of any one metric.

Standard deviation weights follow the same idea as entropy, a metric that spreads the tools out should count more, but measure the spread directly with the sample standard deviation rather than through a probability mass. They are simpler to read and they assume the columns are already on a common scale, which they are after normalization. Use it when you want a plain, transparent measure of spread.

CRITIC weights add a second idea on top of spread: conflict. CRITIC stands for CRiteria Importance Through Intercriteria Correlation. A metric earns weight when its scores spread out and when it disagrees with the other metrics. If two metrics rank the tools the same way, they carry the same information, and counting both at full weight would double count that information. CRITIC measures the disagreement as one minus the correlation between columns and multiplies it by the standard deviation. Use it when several metrics may be measuring the same underlying property and you want the redundant ones discounted.

MEREC weights take a different route. MEREC stands for Method based on the Removal Effects of Criteria. It scores how much the overall ranking changes when each metric is removed. A metric whose removal barely moves the scores carries little information and gets a small weight. A metric whose removal shifts the scores a lot gets a large weight. The aggregate it uses is logarithmic, so it needs strictly positive scores. A column normalized with plain min-max can contain a hard zero, which MEREC cannot take the logarithm of. Pair it with a normalization that stays away from zero, such as the logistic z-score strategy. Use MEREC when you want a weight that reflects each metric's marginal effect on the result rather than its raw spread.

## The subjective scheme: AHP

AHP, the Analytic Hierarchy Process, does not read the score matrix. It asks the analyst to compare the metrics in pairs and state how many times more important one is than another, on Saaty's 1 to 9 scale. These judgments fill a square pairwise comparison matrix that must be reciprocal: if metric A is judged three times as important as B, then B is one third as important as A, and the diagonal is all ones. The weights are the principal eigenvector of this matrix, normalized to sum to 1.

Because the judgments are made one pair at a time, they can contradict each other. If A is rated twice as important as B, and B twice as important as C, then consistency would put A four times as important as C, but the analyst might write something else. AHP measures this with a consistency ratio. A perfectly consistent matrix has a ratio of 0. Saaty's rule is that a ratio above 0.1 means the judgments are too incoherent to trust and should be revised. beam returns the consistency ratio alongside the weights and warns, or raises on request, when it exceeds 0.1.

Use AHP when the choice of weights is a stakeholder decision rather than a property of the data, for example when a benchmark must reflect that accuracy matters more than runtime by an agreed amount. Its cost is that someone has to supply and defend the pairwise judgments, and the consistency check is what keeps those judgments honest.

## Choosing a scheme

Start with equal weights as the baseline. Move to an objective scheme when you want the data to set the weights: entropy or standard deviation for plain spread, CRITIC when metrics may be redundant, MEREC when you care about each metric's marginal effect. Reach for AHP only when the weights encode a deliberate value judgment that the objective schemes cannot represent, and report the consistency ratio so the judgment can be audited.

## References

- Diakoulaki, D., Mavrotas, G., Papayannakis, L. Determining objective weights in multiple criteria problems: the CRITIC method. Computers and Operations Research 22 (1995).
- Keshavarz-Ghorabaee, M., Amiri, M., Zavadskas, E. K., Turskis, Z., Antucheviciene, J. Determination of Objective Weights Using a New Method Based on the Removal Effects of Criteria (MEREC). Symmetry 13 (2021).
- Saaty, T. L. The Analytic Hierarchy Process. McGraw-Hill (1980).
