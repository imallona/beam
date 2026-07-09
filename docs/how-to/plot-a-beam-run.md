# Plot a beam run

`beam.plot` returns matplotlib figures you can show in a notebook, drop into a Quarto vignette, or write to a file. Every function returns a `matplotlib.figure.Figure`, so you can adjust it before saving. The figure code is shared with the [HTML report](../reference/report.qmd), so a plot you draw here is the same one the report embeds.

This recipe covers the plot families and how to save them.

## Get a run

Every plot starts from a [`RunResult`](../reference/RunResult.qmd).

```python
import beam
from beam import plot

run = beam.rank("scores.csv", weights="entropy", method="topsis")
```

## Ranking and stability

These take the run and draw the headline result and its stability checks.

```python
plot.ranking(run)            # composite score per tool, rank 1 at the top
plot.normalized_scores(run)  # the normalized score heatmap
plot.smaa(run)               # share of random weightings that rank each tool first
plot.dataset_stability(run)  # leave-one-dataset-out rank stability (tensor input)
plot.funky_heatmap(run)      # the glyph table with the rank-robustness panels
```

[`smaa`](../reference/smaa.qmd) and `dataset_stability` need the matching sensitivity report; they raise a clear error when the run was made with `sensitivity=False` or, for the dataset plots, on a single-dataset input.

## Effect dissection

These show how the ranking moves when one choice or the data changes, drawn as a bump chart so you can follow each tool. They re-rank the run's matrix, holding every other choice fixed and varying only the named one.

```python
plot.weighting_effect(run)       # across the weighting schemes
plot.aggregation_effect(run)     # across the five aggregation rules
plot.normalization_effect(run)   # across the normalization strategies
plot.dataset_effect(run)         # across the leave-one-dataset-out runs
```

A line that stays flat means that tool's rank does not depend on the choice; lines that cross mean the choice reorders the tools. A level that cannot run on the input (for example `log_min_max` on a column with a zero) is dropped from the plot.

## Agreement and consistency

These summarize a choice or the pairwise evidence. The agreement heatmaps accept either the run (the report is computed for you) or the matching analysis report.

```python
plot.aggregation_agreement(run)     # tau-b heatmap across aggregations
plot.normalization_agreement(run)   # tau-b heatmap across normalizations

from beam.mcda import rank_sensitivity, specification_curve, pairwise_transitivity, critical_difference
plot.rank_sensitivity(report)       # share of rank variance per factor
plot.specification_curve(report)    # rank of the top tool across every combination
plot.pairwise_majority(report)       # the pairwise majority relation and its cycles
plot.critical_difference(report)    # canonical Friedman-Nemenyi clique-bar diagram
plot.critical_difference_band(report)  # the shaded-band alternative
```

The [critical-difference plot](../explanations/critical-difference.md) is the canonical Demsar diagram: each tool at its average rank, with a blue bar joining each clique the Nemenyi test cannot separate.

## Grids, heterogeneity, and building blocks

```python
plot.rank_heatmap(ranks, row_names, col_names, col_label="config")  # labelled rank grid
plot.score_heatmap(values, row_names, col_names, highlight_best_per_col=True)  # raw scores, NaN-aware
plot.rank_bump(method_names, columns, ranks)   # bump chart of ranks across columns

# heterogeneity reports (need the R toolchain to produce, plain matplotlib to draw)
plot.model_effects(mixed_effects_report)       # per-method effects with error bars
plot.variance_components(mixed_effects_report) # variance-component shares
plot.bradley_terry_leaves(bradley_terry_report)  # datasets per leaf, labelled by the method ranking first
```

## Save a figure

`plot.save` writes the figure; the file extension picks the format.

```python
fig = plot.normalization_effect(run)
plot.save(fig, "normalization_effect.png")
plot.save(fig, "normalization_effect.pdf")
```

## Dissect one effect in the funky heatmap

The [funky heatmap](../explanations/funky-heatmaps-and-robustness.md) can carry an extra rank-span panel per choice so you can read several effects in one figure. The normalization panel is off by default to keep the figure narrow; turn it on when you want it.

```python
plot.funky_heatmap(
    run,
    show_aggregation_consensus=True,
    show_normalization_consensus=True,
)
```

## From R

The R package mirrors this through S3 `plot` methods on the run and on each report; see [Use beam from R](use-beam-from-r.md).
