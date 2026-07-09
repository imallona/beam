# Funky heatmaps and robustness

The funky heatmap is the glyph table that dynbenchmark/dynverse, OpenProblems and other benchmarking platforms use to summarize a multi-metric benchmark at a glance. Methods are the rows, sorted best first. Metrics are the columns. Each cell is a circle whose radius grows with the score, with its colour marking the metric group, and a final overall column carries the aggregate. It is a dense summary.

Read on its own the table can pass for a settled ranking, but the order is not fixed. The circle sizes and the row order both depend on the [normalization](normalization-and-scales.md), which is usually min-max, and changing it moves the circles and can reorder the rows. beam reads the normalization from the metric cards instead of fixing min-max, and it adds panels next to the grid that show how far the order would hold under a different analysis.

## The glyph grid and its overlays

`beam.reporting.funky_heatmap` draws the glyph grid and the optional robustness panels beside it; `beam.reporting.funky_heatmap_from_run` builds the whole figure from a `beam.rank` `RunResult`. Each panel is fed by one beam primitive and probes the order in a different way.

Leave-one-dataset-out rank span. For each method it draws the span of ranks the method takes as each dataset is dropped in turn, with the pooled rank marked. The values are `rank_low`, `rank_high` and `rank_stability` from [`beam.mcda.leave_one_dataset_out`](../reference/leave_one_dataset_out.qmd). A single point means the rank holds whatever dataset is dropped; a wide span means the order depends on which datasets are in the pool.

Aggregation-consensus rank span. Holding the [weighting](weighting-schemes.md) fixed, it draws the span of ranks a method takes across the [five aggregations](aggregation-methods.md): SAW, TOPSIS, VIKOR, PROMETHEE II and [COMET](aggregation-methods.md#comet). The values are `consensus_low` and `consensus_high`, the `rank_low` and `rank_high` of [`beam.mcda.aggregation_agreement`](../reference/aggregation_agreement.qmd), which also reports the Kendall tau-b agreement behind the span (see [Aggregation agreement](choice-agreement.md)). A wide span means the aggregation rule, not the methods, is setting the order.

SMAA rank-acceptability bar. Stochastic multicriteria acceptability analysis samples random weightings; for each method the stacked bar shows the share that place it at rank 1, rank 2, and so on. The values are `smaa_acceptability` from [`beam.mcda.smaa`](../reference/smaa.qmd). It is the full rank distribution under weight uncertainty rather than a single confidence number.

Worth panel. It draws the latent strength per method as points with horizontal confidence intervals, `worth` and `worth_ci`, from [Plackett-Luce](method-by-dataset-heterogeneity.md#plackett-luce-full-rankings) with reference-free quasi-standard-errors, Bradley-Terry, or the [mixed-effects](method-by-dataset-heterogeneity.md) marginal means. Two adjacent intervals that overlap mark methods the aggregate bar cannot tell apart.

Critical-difference cliques. Brackets group the rows the Friedman-Nemenyi test cannot separate, the `cliques` from [`beam.mcda.critical_difference`](../reference/critical_difference.qmd). A bracket over the top rows says those methods are not distinguishable from the data at hand.

Between them the panels ask whether the row order would survive dropping a dataset, choosing a different aggregation, resampling the weights, or accounting for model uncertainty. The plain funky heatmap answers none of these.

## How to use it

Call `funky_heatmap_from_run(run)` on a `RunResult`. The leave-one-dataset-out span, the aggregation consensus and the SMAA panel come from the run. The worth intervals and the cliques have to be passed in, since the worth comes from the R-backed heterogeneity models rather than from the run itself.

`beam.report` embeds it by default in the "Robustness at a glance" section, with the panels a run can supply without the R toolchain; pass `funky_heatmap=False` to drop it.

The [OpenProblems](../../examples/openproblems/openproblems.qmd) and [Duo 2018](../../examples/duo2018/duo2018.qmd) vignettes show the two extremes side by side. OpenProblems batch integration has a fragile top: wide leave-one-dataset-out spans and overlapping worth intervals among the leaders. Duo 2018 is stable: the top method holds rank one across every leave-one-dataset-out run, the spans are narrow, and the worth intervals separate.
