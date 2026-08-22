# Funky heatmaps and robustness

The funky heatmap is the glyph table used by dynbenchmark/dynverse and OpenProblems. Methods are the rows, sorted best first, and metrics are the columns. Each cell is a circle whose radius grows with the score and whose colour marks the metric group. A last column has the aggregate.

Circle sizes and row order depend on the [normalization](normalization-and-scales.md), usually min-max. beam takes the normalization from the metric cards and adds panels beside the grid.

## Panels

`beam.reporting.funky_heatmap` draws the grid and the optional panels; `beam.reporting.funky_heatmap_from_run` builds the figure from a `beam.rank` `RunResult`.

Leave-one-dataset-out rank span. The span of ranks of each method as each dataset is dropped in turn, with the pooled rank marked: `rank_low`, `rank_high` and `rank_stability` from [`beam.mcda.leave_one_dataset_out`](../reference/leave_one_dataset_out.qmd).

Aggregation-consensus rank span. The span of ranks of each method across the [five aggregations](aggregation-methods.md) under one [weighting](weighting-schemes.md): `rank_low` and `rank_high` from [`beam.mcda.aggregation_agreement`](../reference/aggregation_agreement.qmd). See [Aggregation agreement](choice-agreement.md).

SMAA rank-acceptability bar. The share of random weightings that place each method at rank 1, rank 2, and so on: `smaa_acceptability` from [`beam.mcda.smaa`](../reference/smaa.qmd).

Worth panel. The latent strength per method with confidence intervals, `worth` and `worth_ci`, from [Plackett-Luce](method-by-dataset-heterogeneity.md#plackett-luce-full-rankings) with quasi-standard-errors, Bradley-Terry, or the [mixed-effects](method-by-dataset-heterogeneity.md) marginal means.

Critical-difference cliques. Brackets over the rows the Friedman-Nemenyi test does not separate: `cliques` from [`beam.mcda.critical_difference`](../reference/critical_difference.qmd).

## Usage

`funky_heatmap_from_run(run)` takes the leave-one-dataset-out span, the aggregation consensus and the SMAA panel from the run. The worth intervals and the cliques are passed in, because the worth comes from the R-backed heterogeneity models.

`beam.report` embeds the figure with the panels a run supplies without R; `funky_heatmap=False` drops it.

The [OpenProblems](../../examples/openproblems/openproblems.qmd) and [Duo 2018](../../examples/duo2018/duo2018.qmd) vignettes show the figure on data.
