# Aggregation methods

After [normalizing](normalization-and-scales.md) the metrics results, beam holds a tool by metric matrix in the unit interval, with every column oriented so higher is better, plus a weight per metric. Aggregation turns that matrix into one preference score per tool, which then becomes a ranking. beam offers five aggregation methods: SAW, TOPSIS, VIKOR, PROMETHEE II and COMET.

beam calls pymcdm for each, with an identity normalization and every metric typed as positive, and handles the single-tool case itself.

## Inputs

The normalized matrix has shape (n_tools, n_metrics) and values in [0, 1]. The weights are a non-negative vector of length n_metrics. The output is a score per tool, higher is better, which [`beam.mcda.rank`](../reference/rank.qmd) ranks.

## SAW

Simple additive weighting (SAW) is the dot product of the normalized scores and the weights. It assumes a common interval scale, where a gain on one metric offsets a loss on another linearly. It is the default.

## TOPSIS

TOPSIS weights the matrix and takes the best value of each column as the ideal and the worst as the anti-ideal. The score of a tool is its Euclidean distance to the anti-ideal divided by the sum of its distances to both. It assumes an interval scale. Unlike SAW, a balanced tool can rank above a tool with one very high and one very low score when their sums are equal.

## VIKOR

The group utility $S$ is the weighted Manhattan distance from the ideal. The individual regret $R$ is the weighted Chebyshev distance, the largest weighted gap of a tool. The index $Q$ combines them with $v$ in $[0, 1]$, by default 0.5:

$$Q = v \cdot \text{rescaled } S + (1 - v) \cdot \text{rescaled } R$$

$S$ and $R$ are rescaled by their range across tools. VIKOR assumes an interval scale and, unlike SAW, is sensitive to one poor metric.

A smaller $Q$ is better, so beam returns $-Q$.

## PROMETHEE II

PROMETHEE II compares every ordered pair of tools. A preference function maps the difference of two tools on a metric to a degree of preference. beam's default is the Type I (usual) function: a tool is preferred on a metric when it scores higher, by any margin. The preferences are weighted, summed over metrics and averaged over the other tools into a positive flow (how much a tool outranks the rest) and a negative flow. The score is the net flow.

With the usual function PROMETHEE II is ordinal per metric. Brans and Vincke define five other preference functions with indifference and preference thresholds in the units of the metric.

## COMET

COMET, the Characteristic Objects Method (Salabun 2015), is free of rank reversal: adding or removing a tool does not change the order of the others. The other four score each tool against the tools present.

The characteristic objects are the Cartesian product of a few values per metric, by default $0$ and $1$; other values such as $0.5$ can be passed. In the original method an expert orders the objects pairwise. beam orders them by the weighted sum of their coordinates. Each tool is scored by triangular fuzzy interpolation between the surrounding objects, in $[0, 1]$.

The number of objects is exponential in the number of metrics: $2^{10} = 1024$ for ten metrics with two values each.

## Choice

SAW is the most transparent. TOPSIS and VIKOR favour balance across metrics, and VIKOR sets how much one weak metric counts. PROMETHEE II with the usual function uses only the order of the tools per metric. COMET keeps the order when tools are added or dropped. [Aggregation agreement](choice-agreement.md) compares the rankings of the five.

## References

- Hwang, C.-L. and Yoon, K. Multiple Attribute Decision Making: Methods and Applications. Springer (1981). The origin of TOPSIS. DOI [10.1007/978-3-642-48318-9](https://doi.org/10.1007/978-3-642-48318-9).
- Opricovic, S. Multicriteria optimization of civil engineering systems. Faculty of Civil Engineering, Belgrade (1998).
- Opricovic, S. and Tzeng, G.-H. Compromise solution by MCDM methods: a comparative analysis of VIKOR and TOPSIS. European Journal of Operational Research (2004). DOI [10.1016/S0377-2217(03)00020-1](https://doi.org/10.1016/S0377-2217%2803%2900020-1).
- Brans, J.-P. and Vincke, P. A preference ranking organisation method: the PROMETHEE method for multiple criteria decision-making. Management Science (1985). DOI [10.1287/mnsc.31.6.647](https://doi.org/10.1287/mnsc.31.6.647).
- Salabun, W. The Characteristic Objects Method: a new distance-based approach to multicriteria decision-making problems. Journal of Multi-Criteria Decision Analysis (2015). DOI [10.1002/mcda.1525](https://doi.org/10.1002/mcda.1525).
- OECD. Handbook on Constructing Composite Indicators (2008), on weighting and aggregation. DOI [10.1787/9789264043466-en](https://doi.org/10.1787/9789264043466-en).
