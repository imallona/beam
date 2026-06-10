# The specification curve

A ranking depends on a few choices: which weighting scheme, which aggregation rule, and, when there is more than one dataset, which dataset you read. If you report one ranking from one set of choices, you cannot see whether a different choice would have changed it. The specification curve runs every combination of the choices and reports the ranking each one gives, so you can read how much they vary (Simonsohn, Simmons and Nelson 2020; Steegen, Tuerlinckx, Gelman and Vanpaemel 2016).

beam already runs the full grid in `beam.mcda.rank_sensitivity`: every combination of the weighting, the aggregation and the dataset. `rank_sensitivity` splits the rank variance into a share per factor, which says which choice moves the ranking. `beam.mcda.specification_curve` reads the same grid, lists the rankings, and counts how often the top method stays the same.

## What it reports

`specification_curve` takes a `RankSensitivityReport` and returns a `SpecificationCurveReport`. It does no new ranking; it post-processes the grid that `rank_sensitivity` already ran.

- `specifications`: one record per combination, with the factor levels that define it, the full tool ordering it produces, and the tool it ranks first.
- `most_frequent_top_fraction`: the fraction of combinations that rank the same tool first. Near 1 means the top is stable across the choices.
- `modal_order_fraction`: the fraction of combinations that produce the single most common ordering of all tools. This is stricter than the top fraction, since it asks the whole order to repeat.
- `n_distinct_top_tools`: how many tools reach the top in at least one combination.
- `curve_order`: the combinations sorted by the rank that the method ranking first most often takes, so a plot reads left to right from its best rank to its worst.

## Choices only, or choices and data

The grid has two factors for a tool-by-metric matrix (the weighting and the aggregation) and three for a tool-by-dataset-by-metric tensor (the dataset joins them). The two forms answer different questions.

Run `rank_sensitivity` on the pooled matrix to get the analyst-choice multiverse: every weighting by every aggregation, on the ranking pooled across datasets. Run it on the tensor to add the dataset, which mixes the choice multiverse with the data heterogeneity. Pass whichever report you want to `specification_curve`.

```python
from beam.mcda import rank_sensitivity, specification_curve, registry_context

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
curve = specification_curve(report)
print(curve.most_frequent_top_fraction, curve.n_distinct_top_tools)
```

## What it says on real data

On Duo 2018 over ARI, runtime and the Shannon entropy difference, the analyst-choice multiverse has 20 combinations: four weightings by five aggregations on the pooled matrix. Seurat ranks first in every one, so the top does not depend on the weighting or the aggregation. The full ordering repeats in only 15 percent of them, so the middle of the table reshuffles with the choice even though the top does not. Add the twelve datasets as a third factor and the grid grows to 240 combinations. Seurat now ranks first in 49 percent, and five tools reach the top in at least one. The drop is the data, not the analyst's freedom. It is the same reading the variance decomposition gives as a large dataset share.

On the M4 forecasting competition the pattern repeats. The 20-combination choice multiverse leaves Pawlikowski first in 90 percent. The 120-combination grid that adds the six frequency bands drops the top tool, Smyl, to 33 percent, with five tools reaching the top. The ranking is stable to how you weight and aggregate, and unstable to which frequency band you read.

The HTML report draws the specification curve for a tensor input, in the same section as the variance decomposition. The top panel plots the rank of the method that ranks first most often, across the combinations sorted from its best to its worst; the panel beneath marks which weighting, aggregation and dataset each combination used.

## References

- Simonsohn, U., Simmons, J. P., Nelson, L. D. Specification curve analysis. Nature Human Behaviour 4, 1208-1214 (2020). DOI [10.1038/s41562-020-0912-z](https://doi.org/10.1038/s41562-020-0912-z).
- Steegen, S., Tuerlinckx, F., Gelman, A., Vanpaemel, W. Increasing transparency through a multiverse analysis. Perspectives on Psychological Science 11, 702-712 (2016). DOI [10.1177/1745691616658637](https://doi.org/10.1177/1745691616658637).
