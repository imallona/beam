# Aggregation methods

After normalization the pipeline holds a tool by metric matrix in the unit interval, with every column oriented so higher is better, plus a weight per metric. Aggregation turns that matrix into one preference score per tool, which then becomes a ranking. beam offers four aggregation methods on this page: SAW, TOPSIS, VIKOR and PROMETHEE II (COMET has its own page). They differ in what they compute and in what they assume about the scale of the normalized scores. This page explains each one and the conventions they share.

beam wraps pymcdm for these methods rather than implementing the algorithm math itself. Each beam function calls the matching pymcdm method with an identity normalization, so pymcdm runs on beam's already normalized matrix, and with every metric typed as profit because the matrix is oriented higher is better. beam keeps the shared input and output contract, applies the higher-is-better convention described below, and handles the corner cases (for example a single tool) that pymcdm leaves undefined.

## The shared convention

Every aggregation in beam takes the same two inputs and returns the same kind of output. The input is the normalized matrix, shape (n_tools, n_metrics), values in [0, 1], already oriented so higher is better. The weights are a non-negative vector of length n_metrics. The output is a preference score per tool where higher is better, so that `beam.mcda.rank` (1 = highest score) produces the ranking. Methods whose textbook form is lower is better are negated before they leave the function, so the convention holds everywhere and the caller never has to track orientation per method.

This shared contract lets the pipeline swap one method for another, and lets sensitivity analysis run any of them through the same loop.

## SAW

Simple additive weighting is the dot product of the normalized scores and the weights. The score of a tool is the weighted sum of its per-metric values. It is the most readable method: the contribution of each metric is explicit, and a unit gain on a metric raises the score by exactly that metric's weight. SAW assumes the normalized values are on a common interval scale, so that adding them is meaningful and a gain on one metric trades off linearly against a loss on another. It is the default when a reader wants to see exactly how the ranking was built.

## TOPSIS

TOPSIS measures each tool's distance to two reference points. It weights the matrix, then finds the ideal solution (the best value in each weighted column) and the anti-ideal (the worst). Each tool's score is its relative closeness: the distance to the anti-ideal divided by the sum of the distances to the ideal and the anti-ideal. A tool near the ideal and far from the anti-ideal scores near 1. Like SAW, TOPSIS uses Euclidean distance on the weighted values, so it assumes an interval scale where differences are comparable across metrics. It differs from SAW in one way: a tool is rewarded for being close to the best on every metric at once, not just for a high total. So a balanced tool can rank above a tool with one very high and one very low score, even when their sums match.

## VIKOR

VIKOR ranks tools by a compromise between two competing views of a good tool. The group utility $S$ is the weighted Manhattan distance from the ideal, summed across metrics, so it rewards a tool that does well on the whole set. The individual regret $R$ is the weighted Chebyshev distance, the single worst weighted gap, so it penalizes a tool's weakest metric. The compromise index $Q$ blends them with a parameter $v$ in $[0, 1]$:

$$Q = v \cdot \text{rescaled } S + (1 - v) \cdot \text{rescaled } R$$

With $v = 1$ the index follows $S$ alone, the majority or maximum-group-utility view. With $v = 0$ it follows $R$ alone, the minimum-regret view that protects against a single bad metric. The usual default is $v = 0.5$. Both $S$ and $R$ are rescaled by their own range across tools before they enter $Q$. VIKOR shares the interval-scale assumption of SAW and TOPSIS, since it sums and compares weighted gaps. Its distinctive feature is the explicit $S$ versus $R$ trade-off, which makes it sensitive to a single poor metric in a way SAW is not.

The canonical VIKOR $Q$ is lower is better: the preferred compromise has the smallest $Q$. To match beam's higher-is-better convention, the implementation returns $-Q$. Negation keeps the order exactly, so the tool with the smallest $Q$ has the largest score and ranks first. beam returns $-Q$ rather than a rescaled $1 - Q$ so that a second normalization step does not discard the absolute spacing of the $Q$ values; the ranking is identical either way.

## PROMETHEE II

PROMETHEE II compares every ordered pair of tools rather than scoring each tool against a fixed reference. For each pair and each metric it applies a preference function to the difference in scores, giving a degree of preference for one tool over the other. The default in beam is the Type I (usual) preference function, which expresses strict dominance: a tool is preferred on a metric as soon as it scores higher, by any margin, and an equal score gives no preference. The preferences are weighted and summed across metrics, then averaged over the other tools to give a positive flow (how much a tool outranks the rest) and a negative flow (how much the rest outrank it). The net flow is their difference and is the preference score; it is already higher is better, so it is returned unchanged.

Because the usual preference function looks only at the sign of each difference, PROMETHEE II in this default form is ordinal per metric: it uses the order of the tools on a metric, not the size of the gaps. This makes it the lightest method on scale assumptions of the four. Brans and Vincke define five other preference functions that soften this with indifference and preference thresholds in the metric's own units, which add back the size of the differences. They are a documented extension point in the implementation, not the default, because they need per-metric thresholds the pipeline does not yet carry.

## Choosing among them

SAW is the right choice when transparency matters and the metrics are on a comparable interval scale. TOPSIS and VIKOR both reward balance across metrics, with VIKOR adding an explicit knob for how much a single weak metric should count. PROMETHEE II is the most conservative about scale, since in its default form it reads only the order of the tools on each metric. Running more than one method and comparing the rankings is itself a sensitivity check: a recommendation that holds across methods is more reliable than one that depends on the choice of aggregation.

## References

- Hwang, C.-L. and Yoon, K. Multiple Attribute Decision Making: Methods and Applications. Springer (1981). The origin of TOPSIS. DOI [10.1007/978-3-642-48318-9](https://doi.org/10.1007/978-3-642-48318-9).
- Opricovic, S. Multicriteria optimization of civil engineering systems. Faculty of Civil Engineering, Belgrade (1998).
- Opricovic, S. and Tzeng, G.-H. Compromise solution by MCDM methods: a comparative analysis of VIKOR and TOPSIS. European Journal of Operational Research (2004). DOI [10.1016/S0377-2217(03)00020-1](https://doi.org/10.1016/S0377-2217%2803%2900020-1).
- Brans, J.-P. and Vincke, P. A preference ranking organisation method: the PROMETHEE method for multiple criteria decision-making. Management Science (1985). DOI [10.1287/mnsc.31.6.647](https://doi.org/10.1287/mnsc.31.6.647).
- OECD. Handbook on Constructing Composite Indicators (2008), on weighting and aggregation. DOI [10.1787/9789264043466-en](https://doi.org/10.1787/9789264043466-en).
