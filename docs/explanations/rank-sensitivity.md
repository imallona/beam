# Rank sensitivity and the specification curve

A ranking can move for two reasons. One is the data: a method that ranks first on one dataset can trail on another. The other is the analyst's choices: which [weighting scheme](weighting-schemes.md) sets the weights, and which [aggregation rule](aggregation-methods.md) combines the scores.
[`beam.mcda.rank_sensitivity`](../reference/rank_sensitivity.qmd) measures both at once. The weighting, the aggregation, and the dataset are each a small set of options, so beam runs every combination instead of sampling. For each tool this gives a table of its rank over the full grid. An analysis of variance then splits the rank variance into a share for each factor and a share for their interactions. The shares sum to one.

## The shares

For a deterministic function of a few categorical factors over a balanced full grid, the main-effect shares are the first-order variance indices, the categorical form of the Sobol indices. They are exact here, not estimated, because nothing is sampled.

The headline is the share each factor carries, pooled over the tools:

- A large dataset share means the ranking depends on which dataset you use. That is method heterogeneity, the same thing the [Bradley-Terry tree](method-by-dataset-heterogeneity.md#bradley-terry-trees) and the [mixed-effects decomposition](method-by-dataset-heterogeneity.md) read in other ways.
- A large weighting or aggregation share means the ranking depends on a choice the analyst could make differently. That is a degree of freedom the report should disclose.
- A large interaction share means the choice matters more on some datasets than others.

## Two factors or three

A 2D tool-by-metric matrix has two factors: the weighting and the aggregation. A 3D tool-by-dataset-by-metric tensor adds the dataset as a third factor. The tensor form is the useful one, because it puts the data question and the choice questions in the same decomposition.

```python
from beam.mcda import rank_sensitivity, registry_context

ctx = registry_context(metric_ids, "saw")
report = rank_sensitivity(
    tensor,                       # (n_tools, n_datasets, n_metrics)
    ctx.polarity,
    normalization=list(ctx.normalization),
    bounds=list(ctx.bounds),
    baselines=list(ctx.baselines),
    targets=list(ctx.targets),
    missing="worst",              # complete partial coverage, or drop to a feasible subset
    tool_names=tool_names,
    dataset_names=dataset_names,
)
print(report.dataset_share, report.weighting_share, report.aggregation_share)
```

## What it says on real data

On the [M4 forecasting benchmark](../../examples/m4/m4.qmd) the dataset accounts for about 0.96 of the rank variance. The weighting and aggregation choices carry under 0.01 each. The headline method ranks first on some frequencies and near last on others. The order is almost entirely a question of which frequency you evaluate on, not how you aggregate.

On the [Duo 2018 clustering benchmark](../../examples/duo2018/duo2018.qmd) the dataset accounts for about 0.71, with a larger interaction term. The 0.71 is close to the dataset variance share an independent mixed-effects model finds on the same data, which is a cross-check: two different methods, the same reading.

## Defaults and limits

The default weightings are equal, entropy, standard deviation, and CRITIC. MEREC is left out by default because it takes the logarithm of the scores and refuses a zero, and the default min_max normalization maps each column minimum to zero. Pass MEREC explicitly with a normalization that keeps the scores positive.

Every combination must produce a ranking. The distance and outranking aggregations (TOPSIS, VIKOR, PROMETHEE II, [COMET](aggregation-methods.md#comet)) refuse a slice with missing cells, so a tensor with gaps needs `missing="worst"` to complete the matrix, or a restriction to the feasible subset. A factor level that still fails on the input is dropped, and the report names what it dropped.

COMET is slow on a metric-rich benchmark. It builds characteristic objects whose count grows fast with the number of metrics, so on a task with a dozen metrics the other four aggregations are the practical choice.

The shares describe this set of options on this data. They are not an inference back to a population of datasets or a population of analysts. A tool that holds the same rank in every combination has no variance to split, so its per-tool shares are undefined and reported as such.

## The specification curve

The shares say which choice moves the ranking. The specification curve reads the same grid a different way: it lists the ranking each combination produces and counts how often the top method stays the same (Simonsohn, Simmons and Nelson 2020; Steegen, Tuerlinckx, Gelman and Vanpaemel 2016). [`beam.mcda.specification_curve`](../reference/specification_curve.qmd) takes the `RankSensitivityReport` and post-processes it, without re-ranking:

- `specifications`: one record per combination, with its factor levels, the full tool ordering, and the top-ranked tool.
- `most_frequent_top_fraction`: the fraction of combinations that rank the same tool first. Near 1 means the top is stable across the choices.
- `modal_order_fraction`: the fraction that produce the single most common ordering of all tools. This is stricter, since it asks the whole order to repeat.
- `n_distinct_top_tools`: how many tools rank first in at least one combination.
- `curve_order`: the combinations sorted by the rank the most-frequent top method takes, so a plot reads left to right from its best rank to its worst.

```python
from beam.mcda import specification_curve

curve = specification_curve(report)   # report from rank_sensitivity above
print(curve.most_frequent_top_fraction, curve.n_distinct_top_tools)
```

On [Duo 2018](../../examples/duo2018/duo2018.qmd) over the Adjusted Rand Index, runtime and the Shannon entropy difference, the analyst-choice grid has 20 combinations: four weightings by five aggregations on the pooled matrix. Seurat ranks first in every one, so the top does not depend on the weighting or the aggregation, but the full ordering repeats in only 15 percent, so the middle of the table reshuffles. Adding the twelve datasets as a third factor grows the grid to 240 combinations: Seurat now ranks first in 49 percent, and five tools rank first in at least one, which is the data contribution on top of the analyst's freedom. On the [M4 forecasting competition](../../examples/m4/m4.qmd) the 20-combination choice grid leaves Pawlikowski first in 90 percent, and the 120-combination grid that adds the six frequency bands drops the top tool, Smyl, to 33 percent with five tools reaching the top.

The HTML report plots the specification curve for a tensor input, in the same section as the variance decomposition. The top panel plots the rank of the most-frequent top method across the combinations sorted from its best to its worst; the panel beneath marks which weighting, aggregation and dataset each used.

## See also

- [Attribution synthesis](attribution-synthesis.md)
- [Analysis blinding](analysis-blinding.md)

## References

- Simonsohn, U., Simmons, J. P., Nelson, L. D. Specification curve analysis. Nature Human Behaviour 4, 1208-1214 (2020). DOI [10.1038/s41562-020-0912-z](https://doi.org/10.1038/s41562-020-0912-z).
- Steegen, S., Tuerlinckx, F., Gelman, A., Vanpaemel, W. Increasing transparency through a multiverse analysis. Perspectives on Psychological Science 11, 702-712 (2016). DOI [10.1177/1745691616658637](https://doi.org/10.1177/1745691616658637).
