# OpenProblems as a data source

beam needs benchmark results that are already a method by dataset by metric tensor with declared metric directions. Most published benchmarks are not in that shape, and putting them together is the data-engineering bottleneck the cross-benchmark meta-analysis runs into. OpenProblems in Single-Cell Analysis (openproblems.bio, Nature Biotechnology 2025, DOI 10.1038/s41587-025-02694-w) already produces that shape, so beam ingests it directly.

## What OpenProblems publishes

OpenProblems runs a continuous automated single-cell benchmark. Within a task, every method is scored on every dataset by every metric, and the full results are published as CC-BY JSON per task in the openproblems-bio/website GitHub repository. So one task is a clean method by dataset by metric tensor with the metric directions stated. That is the harmonization beam would otherwise have to do by hand.

beam vendors small derived tables in long format, with columns `method_id`, `dataset_id`, `metric_id` and `score`, not the raw single-cell data, from a pinned commit. `beam.datasets.load_openproblems(task)` loads them. The provenance and the CC-BY-4.0 license are recorded in `src/beam/data/README.md`.

## Two tasks, chosen for complementary reasons

No single OpenProblems task gives both many metrics and many datasets, so beam bundles two and each exercises a different part of the stack.

`batch_integration` has 19 methods, 6 datasets and 13 scIB metrics (Luecken et al. 2022). It is metric-rich, so it exercises the MCDA layer over many criteria. beam re-derives the per-metric normalization from the metric cards and runs explicit MCDA with sensitivity. This can place a different method first than the platform's own mean-of-scaled-scores leaderboard rule. In the bundled data, beam with equal weights and TOPSIS leads with combat while the mean-of-scores rule leads with scanvi. The aggregation rule, not the data alone, decides the top method. Coverage is uneven: the `hvg_overlap` column and some method-by-dataset cells are sparse, which beam surfaces as NaN rather than hiding.

`spatially_variable_genes` has 14 methods, 50 datasets and one correlation metric. It is dataset-rich, which is what the Bradley-Terry tree needs to find feature-based splits. The dataset features (spatial assay technology, organism, cancer condition) parse out of the dataset id. The tree splits on technology: spark_x leads the pooled ranking, but spanve leads on the visium and xenium datasets and nnsvg leads on the seqfish, slideseqv2 and slidetags datasets. The top spatially-variable-gene method depends on the assay. See findings 0004.

## The honest tradeoff

Because no one task carries both breadth in metrics and breadth in datasets, `batch_integration` exercises the MCDA breadth and `spatially_variable_genes` exercises the heterogeneity depth. The published results JSON does not include dataset-level numeric features such as cell counts or batch design, so beam uses only the categorical descriptors parseable from the dataset id, and for the spatial data the technology and organism are partly confounded. This bounds what the tree can attribute a split to.

## Two further uses

OpenProblems re-derives its leaderboard by a fixed mean-of-normalized-scores rule. beam contrasts that with explicit MCDA aggregation plus sensitivity, as the `batch_integration` example shows. Because OpenProblems is a sister continuous-benchmarking platform to omnibenchmark, a clean ingestion doubles as a reference for the future omnibenchmark adapter.

The OpenProblems vignette (`examples/openproblems/openproblems.qmd`) works both tasks through end to end, and [findings 0004](../findings/0004-openproblems-svg-bradley-terry.md) records the assay-dependent spatial result.
