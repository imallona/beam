# 0012 - Funky heatmap with rank-robustness overlays

- Status: Accepted
- Date: 2026-05-26
- Deciders: Izaskun Mallona
- Supersedes: -
- Superseded by: -

## Context

The funky heatmap, the glyph table from dynbenchmark and OpenProblems drawn by the R funkyheatmap package, is the standard way to present a multi-metric benchmark. It is also the figure beam's thesis pushes back on: the row order and the circle sizes depend on the normalization, and a single heatmap reads as a settled ranking even when the order does not survive dropping a dataset, changing the aggregation, or sampling the weights. beam already computes those robustness signals (leave-one-dataset-out, SMAA, the five aggregations, the Bradley-Terry and Plackett-Luce and mixed-effects model worths, the Friedman-Nemenyi cliques) but they were shown in separate figures.

## Decision

Draw the funky heatmap in matplotlib inside beam rather than calling the R funkyheatmap package, so it renders anywhere beam is installed and can be augmented.

- Glyph grid. `beam.reporting.funky_heatmap` draws the glyph grid with methods as rows sorted top first, metrics as circles sized by the normalized score and coloured by group, and an overall composite bar. The normalization is resolved from the metric cards, not defaulted to min-max.
- Robustness panels. The same function draws optional robustness panels, each fed by a beam primitive: a leave-one-dataset-out rank span, an aggregation-consensus rank span across the five aggregations, a SMAA rank-acceptability stacked bar, a model-worth panel with confidence intervals (Plackett-Luce, Bradley-Terry, or mixed-effects), and Friedman-Nemenyi clique brackets on the rows.
- Assembly from a run. `beam.reporting.funky_heatmap_from_run` assembles these from a `beam.rank` RunResult. It derives the leave-one-dataset-out span, the SMAA panel, and the aggregation consensus from the run, and takes the worth with intervals and the cliques as arguments because the model worths need the R heterogeneity toolchain.

## Consequences

- The plot renders with matplotlib (already a core dependency) and needs no R for the glyph grid and the dataset, aggregation, and weight-based panels. Only the worth panel needs the R-backed models, and it is optional.
- The figure can grow to several panels, so the caller selects which overlays to show. The vignettes use curated subsets.
- Two worked cases are in the vignettes: OpenProblems batch integration shows a fragile top of the order, and Duo 2018 shows a stable one.
- The matplotlib redraw will not match the R funkyheatmap package pixel for pixel. That is accepted in exchange for the in-process augmentation.

## Alternatives considered

- Call the R funkyheatmap package through the subprocess boundary. Rejected: it would add an R dependency to a plotting path that is otherwise pure Python, and it could not carry beam's robustness panels without reimplementing them anyway.
- Keep the robustness diagnostics as separate figures. Rejected: the robustness signals should sit next to the order they qualify, in the figure people actually read.

## References

- [Funky heatmaps and robustness explanation](../explanations/funky-heatmaps-and-robustness.md)
- [ADR 0010 (bradley-terry-trees)](0010-bradley-terry-trees.md), [ADR 0011 (glmmtmb-and-plackett-luce)](0011-glmmtmb-and-plackett-luce.md)
- Cannoodt R, Saelens W, dynverse. funkyheatmap: generating funky heatmaps for data frames. https://github.com/dynverse/funkyheatmap. Used by the OpenProblems and dynbenchmark multi-metric figures.
- Lahdelma R, Salminen P. SMAA-2: stochastic multicriteria acceptability analysis for group decision making. Operations Research 2001, 49:444-454. Used for the SMAA rank acceptability.
- Demsar J. Statistical comparisons of classifiers over multiple data sets. Journal of Machine Learning Research 2006, 7:1-30. Used for the critical-difference cliques.
