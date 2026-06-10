# COMET

COMET, the Characteristic Objects METhod (Salabun 2015), is one of the aggregation methods in the MCDA pipeline. It takes the same input as the others, a matrix of tools by metrics already normalized to the unit interval and oriented so higher is better, plus a weight per metric, and returns one preference value per tool. What sets it apart is that its ranking is rank reversal free: adding or removing a tool cannot change the order of the others. This page explains how it reaches that property and when it is the better choice over weighted sum or TOPSIS.

beam wraps pymcdm for COMET rather than implementing the method itself. beam supplies the characteristic values and the expert rule described below, and pymcdm builds the Matrix of Expert Judgement, the preference of each characteristic object, and the fuzzy interpolation that scores the tools.

## The rank reversal problem

Most aggregation methods score a tool by comparing it to the other tools in the table. TOPSIS measures distance to the best and worst observed values, so the scale it uses depends on which tools are present. Weighted sum is closer to safe, but once a normalization step rescales each column to the observed minimum and maximum, the same dependence returns. The practical consequence is rank reversal: drop a poor method from the comparison, recompute, and two of the survivors can swap places even though nothing about them changed. For a leaderboard that grows over time, or a sensitivity analysis that drops one method at a time, this is a real problem. The order is supposed to describe the methods, not which other methods are present.

## Characteristic objects

COMET avoids the problem by never fitting its model on the tools. Instead it fits on a fixed grid of reference points called characteristic objects, and the tools are scored afterward against that fixed grid.

The grid is built per criterion. For each metric the method picks a few characteristic values that span its scale. beam uses the endpoints of the normalized scale by default, $0$ and $1$, which is two characteristic values per metric. A caller can pass three values per metric, for example $0$, $0.5$ and $1$, to give the model an interior anchor. The characteristic objects are the Cartesian product of these per-metric values: with two metrics and the endpoints, the four objects are the four corners of the unit square; with three values each, the nine points of a $3 \times 3$ grid. The grid does not depend on the tools, so it does not move when a tool is added or removed. That is the source of the rank reversal free property.

## The expert and the Matrix of Expert Judgement

COMET still needs to know which characteristic objects are better. In its original form a human expert compares every pair of objects and records the judgement in a matrix, the Matrix of Expert Judgement (MEJ). Entry $(i, j)$ is $1$ when object $i$ is preferred to object $j$, $0.5$ when they are judged equal, and $0$ when $j$ is preferred. The row sums of this matrix give the Summed Judgement (SJ) of each object. Grouping objects by distinct SJ value and spreading those groups evenly across the unit interval gives each object a preference $P$, from $0$ for the lowest group to $1$ for the top.

A benchmarking pipeline has no human expert in the loop, so beam supplies a deterministic one. The expert rule here is the weighted sum of a characteristic object's coordinates: object a is preferred to object b when its weighted sum is larger, equal when the two weighted sums are equal. beam passes this rule to pymcdm as the expert function, and pymcdm builds the MEJ from it. This is simple additive weighting used as a pairwise judge of the reference grid. It is auditable, it reproduces, and it lets the method run without a person rating object pairs. The choice of expert is the one design decision a COMET user makes that the other methods do not expose, and beam states it plainly rather than hiding a default human-elicitation step that cannot run unattended.

## Scoring a tool

Once every characteristic object has a preference $P$, a tool is scored by fuzzy interpolation between the surrounding objects. Each characteristic value of a metric carries a triangular fuzzy number peaked at that value: membership is $1$ at the value, falls linearly to $0$ at the neighbouring characteristic values, and is $0$ beyond them. A tool's score on one metric turns into a set of membership degrees, one per characteristic value, that sum to $1$ and say how close the tool sits to each anchor on that metric. The membership degrees for a whole characteristic object are the product of the per-metric memberships across criteria, the tensor product over the grid. The tool's preference is the sum over all characteristic objects of that object's preference $P$ weighted by the tool's membership in it. A tool sitting exactly on a corner of the grid inherits that corner's preference; a tool in between is a blend of the surrounding corners. The result is in $[0, 1]$ and higher is better.

Because the preferences $P$ are fixed before any tool is scored, two tools always receive the same scores no matter which other tools are in the table. That is what makes the method rank reversal free.

## When to prefer COMET

COMET costs more than weighted sum or TOPSIS, in two senses. The number of characteristic objects grows as the product of the per-metric value counts, so it is exponential in the number of metrics: ten metrics with two values each is already $2^{10} = 1024$ objects. And the scores are harder to read off by hand than a weighted sum. So it is not the default.

It is the right tool when rank stability matters more than simplicity. Pick COMET when the comparison set changes over time, as in a continuous benchmark where methods are added between runs, or when a sensitivity analysis drops methods one at a time and the ranking among the survivors must not move for that reason alone. When the tool set is fixed and small and you want a transparent score, weighted sum is clearer; when you want distance to an ideal and accept that the ideal is set by the observed tools, TOPSIS is lighter. COMET trades both of those for a ranking that depends only on the methods themselves.

## Reference

Salabun, W. (2015). The Characteristic Objects Method: A New Distance-based Approach to Multicriteria Decision-making Problems. Journal of Multi-Criteria Decision Analysis, 22(1-2), 37-50.

## References

- Salabun, W.. The Characteristic Objects Method: a new distance-based approach to multicriteria decision-making problems. Journal of Multi-Criteria Decision Analysis (2015). DOI [10.1002/mcda.1525](https://doi.org/10.1002/mcda.1525).
