# Funky heatmaps and robustness

The funky heatmap is the glyph table that dynbenchmark and OpenProblems use to read a multi-metric benchmark at a glance. Methods are the rows, sorted best first. Metrics are the columns. Each cell is a circle whose radius grows with the score, with its colour marking the metric group, and a final overall column carries the aggregate. It is a dense, readable summary. Its weakness is that read alone it looks like a settled ranking. Both the circle sizes and the row order depend on the normalization, which is usually min-max, and a different normalization moves the circles and can reorder the rows. beam resolves the normalization from the metric cards instead of fixing min-max, and then adds panels that let the table carry its own robustness.

## The glyph grid and its overlays

`beam.reporting.funky_heatmap` draws the glyph grid and the optional robustness panels beside it. `beam.reporting.funky_heatmap_from_run` builds the whole figure from a `beam.rank` `RunResult`. Each overlay answers one question about whether the row order is real, and each is fed by a beam primitive.

The leave-one-dataset-out rank span answers whether the order hangs on any single dataset. For each method it draws the span of ranks the method takes when each dataset is dropped in turn, with the pooled rank marked on the span. The values are `rank_low`, `rank_high` and `rank_stability` from `beam.mcda.leave_one_dataset_out`. A single point is robust. A wide span means the order depends on which datasets are in the pool.

The aggregation-consensus rank span answers whether the order is an artefact of the chosen aggregation. Holding the weighting fixed, it draws the span of ranks a method takes across the five aggregations: SAW, TOPSIS, VIKOR, PROMETHEE II and COMET. The values are `consensus_low` and `consensus_high`. A wide span means the order reflects the aggregation rule rather than the methods.

The SMAA rank-acceptability stacked bar answers what the ranks look like under weight uncertainty. For each method it shows the share of random weightings that place it at rank 1, rank 2, rank 3 and so on. The values are `smaa_acceptability` from `beam.mcda.smaa`, the rank_acceptability_index. This is the full distribution of ranks across sampled weights, more honest than a single confidence number.

The worth panel answers whether two adjacent methods are separable. It draws the latent strength per method from a model as points with horizontal confidence intervals, the `worth` and `worth_ci`. The model is Plackett-Luce with reference-free quasi-standard-errors, Bradley-Terry, or the mixed-effects marginal means. When two adjacent intervals overlap the methods are not separable, which the overall bar hides. This is where the heterogeneity models reach the heatmap.

The critical-difference cliques answer whether the methods are statistically distinguishable across datasets. They draw brackets grouping the rows that the Friedman-Nemenyi test cannot separate, the `cliques` from `beam.mcda.critical_difference`. A bracket over the top several rows says those methods are indistinguishable from the data at hand.

## The thesis

Each overlay asks one version of the same question: would this row order survive a reasonable change. The change is dropping a dataset, choosing a different aggregation, sampling the weights, or accounting for the model uncertainty. The plain funky heatmap answers none of these. It reads as more settled than the data support, because the single row order hides the spread that every panel makes visible.

## How to use it

Call `funky_heatmap_from_run(run)` on a `RunResult`. The leave-one-dataset-out span, the aggregation consensus and the SMAA panel come from the run automatically. The worth with intervals and the cliques are passed in by the caller, because the worth comes from the R-backed models and needs the heterogeneity toolchain. The result is the glyph grid with whichever panels the caller supplied.

Two worked cases live in the vignettes. The OpenProblems batch integration case shows a fragile top of the order, with wide leave-one-dataset-out spans and overlapping worth intervals among the leading methods. The Duo 2018 case is stable: the top method holds rank one across every leave-one-dataset-out run, the spans are narrow, and the worth intervals separate.

## Relation to the other diagnostics

The worth panel draws on the [Bradley-Terry tree](heterogeneity-bradley-terry.md) and the mixed-effects fit, which is where the latent strengths and their intervals come from. The cliques come from the [Friedman-Nemenyi test](comparing-methods-across-datasets.md), and the leave-one-dataset-out span shares its logic with that test's question of whether the order hangs on one dataset. The OpenProblems and Duo 2018 vignettes show the fragile and the stable case side by side.
