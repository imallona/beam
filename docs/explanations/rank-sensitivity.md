# Rank sensitivity and the specification curve

A ranking changes with the data and with the analyst's choices: the [weighting scheme](weighting-schemes.md) and the [aggregation rule](aggregation-methods.md). [`beam.mcda.rank_sensitivity`](../reference/rank_sensitivity.qmd) ranks under every combination of weighting, aggregation and dataset. An analysis of variance splits the rank variance of each tool into a share per factor and a share for their interactions. The shares sum to one.

## Shares

On a balanced full grid of categorical factors the main-effect shares are the first-order variance indices, the categorical form of the Sobol indices. Nothing is sampled, so they are exact.

- A large dataset share: the ranking depends on the dataset, as the [Bradley-Terry tree](method-by-dataset-heterogeneity.md#bradley-terry-trees) and the [mixed-effects decomposition](method-by-dataset-heterogeneity.md) also show.
- A large weighting or aggregation share: the ranking depends on an analyst choice.
- A large interaction share: the effect of the choice differs between datasets.

A tool by metric matrix has two factors, the weighting and the aggregation. A tool by dataset by metric tensor adds the dataset.

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
    missing="worst",
    tool_names=tool_names,
    dataset_names=dataset_names,
)
print(report.dataset_share, report.weighting_share, report.aggregation_share)
```

## On real data

On the [M4 forecasting benchmark](../../examples/m4/m4.qmd) the dataset share is 0.96 and the weighting and aggregation shares are under 0.01 each. On the [Duo 2018 clustering benchmark](../../examples/duo2018/duo2018.qmd) the dataset share is 0.73 and the interaction share 0.20.

## Defaults and limits

The default weightings are equal, entropy, standard deviation, and CRITIC. MEREC takes the logarithm of the scores and refuses a zero, which min_max produces; it needs a normalization with positive scores.

TOPSIS, VIKOR, PROMETHEE II and [COMET](aggregation-methods.md#comet) refuse missing cells, so a tensor with missing cells needs `missing="worst"` or a restriction to the complete cases. A factor level that fails on the input is dropped and named in the report.

COMET is slow with many metrics.

The shares describe these options on this data. A tool with the same rank in every combination has undefined shares.

## The specification curve

[`beam.mcda.specification_curve`](../reference/specification_curve.qmd) lists the ranking of each combination from a `RankSensitivityReport`, without re-ranking (Simonsohn, Simmons and Nelson 2020; Steegen, Tuerlinckx, Gelman and Vanpaemel 2016):

- `specifications`: the factor levels, the tool ordering and the top tool of each combination.
- `most_frequent_top_fraction`: the fraction of combinations with the same top tool.
- `modal_order_fraction`: the fraction with the most common full ordering.
- `n_distinct_top_tools`: the number of tools that are top in at least one combination.
- `curve_order`: the combinations sorted by the rank of the most frequent top tool.

```python
from beam.mcda import specification_curve

curve = specification_curve(report)
print(curve.most_frequent_top_fraction, curve.n_distinct_top_tools)
```

On Duo 2018 with the Adjusted Rand Index, runtime and the Shannon entropy difference, the grid has 240 combinations: four weightings, five aggregations, twelve datasets. Seurat is first in 50 percent and six tools are first in at least one. On M4, with 120 combinations, Smyl is first in 33 percent and five tools are first in at least one.

## See also

- [Attribution synthesis](attribution-synthesis.md)
- [Analysis blinding](analysis-blinding.md)

## References

- Simonsohn, U., Simmons, J. P., Nelson, L. D. Specification curve analysis. Nature Human Behaviour 4, 1208-1214 (2020). DOI [10.1038/s41562-020-0912-z](https://doi.org/10.1038/s41562-020-0912-z).
- Steegen, S., Tuerlinckx, F., Gelman, A., Vanpaemel, W. Increasing transparency through a multiverse analysis. Perspectives on Psychological Science 11, 702-712 (2016). DOI [10.1177/1745691616658637](https://doi.org/10.1177/1745691616658637).
