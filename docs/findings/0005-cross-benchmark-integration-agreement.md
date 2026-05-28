# 0005 - Cross-benchmark integration agreement under a consistent ranking rule

- Status: Active
- Date: 2026-05-26 (revised 2026-05-28 with the Tyler 2023 fourth source)
- Dataset: four single-cell integration benchmarks harmonized on the shared scIB metric family (ARI, ASW, kBET, LISI) for five common methods (combat, harmony, fastMNN, scanorama, LIGER): scIB (Luecken et al. 2022), OpenProblems batch_integration, Tran et al. 2020, and Tyler et al. 2023 (bioRxiv preprint, three of five methods and three of four metrics). Bundled as src/beam/data/scib2022_metrics.csv, tran2020_metrics.csv, tyler2023_metrics.csv, integration_published_ranks.csv, and the OpenProblems table.
- Authors: Izaskun Mallona
- Commit: pending
- Manifest: tests/test_datasets_integration.py and examples/cross_benchmark/cross_benchmark.qmd

## Observation

The three benchmarks' own reported rankings of the five common methods barely agree. The mean cross-benchmark Spearman correlation is -0.10, with pairwise values of -0.6 for Tran against scIB, -0.3 for Tran against OpenProblems, and +0.6 for scIB against OpenProblems. The disagreement is concrete at the method level: combat is reported rank 5 (last) by Tran, rank 2 by scIB, and rank 1 (best) by OpenProblems; fastMNN is rank 1 in scIB but rank 4 in Tran.

Re-ranking all three benchmarks with one consistent rule raises the agreement substantially. The rule uses the four shared metrics, equal weight, and raw scores ranked within the five common methods. Under this rule the mean cross-benchmark Spearman rises to +0.50, with pairwise values of 0.4 for Tran against scIB, 0.2 for Tran against OpenProblems, and 0.9 for scIB against OpenProblems. The change in the mean is +0.60.

The beam consensus order, pooling the consistent per-benchmark ranks across the first three sources, is harmony, liger, fastMNN, scanorama, combat. Harmony is a stable top choice across all three benchmarks. A cross-benchmark variance decomposition (score ~ method + (1|benchmark) + (1|benchmark:dataset) + (1|method:benchmark), lme4) gives a method-by-benchmark variance share of 0.15 and a residual share of 0.85 on the mean-rank response over the three full-coverage benchmarks.

Adding Tyler et al. 2023 as a fourth source (2026-05-28 update) raises the method-by-benchmark variance share from 0.15 to 0.23 on the same model fit with 22 datasets and 106 observations. The direction is consistent with Tyler's central claim that unsupervised batch correction methods produce different rankings depending on the evaluation pipeline. Tyler covers three of the five methods (harmony, scanorama, liger) and three of the four metric families (ARI, ASW, kBET; cLISI is held out because it is a different quantity from the iLISI used elsewhere), so the fourth source enters the fit as a partial-coverage block; lme4 handles the imbalance through the random benchmark effect. The four-source residual share is 0.77.

A large part of the apparent disagreement between these benchmarks comes from the benchmarker's analysis choices, which metrics are used, how they are scaled, and how they are weighted, rather than from the methods themselves. Holding those choices fixed brings the rankings substantially into line.

## Method

`beam.datasets.load_integration_benchmarks` harmonizes the three benchmarks to a rank within the common methods, computed per benchmark, dataset and metric. The scIB and OpenProblems ranks come from raw higher-is-better scores; the Tran ranks come from its published per-metric ranks. The reported rankings come from `beam.datasets.load_integration_published_ranks`: the Tran Table S7 final rank, the scIB 0.6 biological and 0.4 batch weighted overall on its full metric set, and the OpenProblems mean of scaled scores. Agreement is the mean pairwise Spearman of the five-method orderings. The variance decomposition is `beam.heterogeneity.source_variance_decomposition` (lme4 via the one-shot subprocess, ADR 0009), with dataset nested in benchmark since the benchmarks mostly use different datasets.

## Implications

Standardizing the metric and aggregation layer (metric cards plus explicit aggregation) reduces spurious disagreement between benchmarks; this case shows how much. The dataset crosswalk matters here. The benchmarks mostly use different datasets, except the human pancreas, which Tran (its Dataset 4: Muraro, Segerstolpe, Baron, Wang, Xin) and scIB share. Part of the residual disagreement is genuine data difference. A same-data pancreas contrast could isolate the pure benchmarker-pipeline effect (future work).

The limits are: three benchmarks and five methods make a Spearman coarse; three benchmarks is too few for a precise benchmark-variance estimate; and the reported rankings are reconstructed. The agreement rises to 0.50, not 1.0, so genuine method-by-data heterogeneity remains.

## Reproducibility

- Notebook or script: tests/test_datasets_integration.py pins the loader and the agreement direction; examples/cross_benchmark/cross_benchmark.qmd is the worked vignette
- Run manifest: the test pins the reported-rank disagreement, the rise under the consistent rule, and the consensus order
- Commit: pending
- Software environment: R 4.3.3 with lme4, Python 3.12 with numpy and scipy, the beam-heterogeneity conda environment

## Related

- Builds on [findings 0003](0003-duo-2018-bradley-terry-tree.md) and [findings 0004](0004-openproblems-svg-bradley-terry.md) (the heterogeneity diagnostics) and the OpenProblems ingestion
- Method in [ADR 0009](../adr/0009-heterogeneity-mixed-effects-via-r.md); data provenance and the keep or discard reasoning in src/beam/data/README.md
- External references: Luecken et al. Nature Methods 2022. DOI 10.1038/s41592-021-01336-8; Tran et al. Genome Biology 2020. DOI 10.1186/s13059-019-1850-9; OpenProblems consortium. Nature Biotechnology 2025. DOI 10.1038/s41587-025-02694-w; Tyler, Guccione and Schadt. Erasure of Biologically Meaningful Signal by Unsupervised scRNAseq Batch-correction Methods. bioRxiv 10.1101/2021.11.15.468733 v2 (2023-10-26), preprint only as of 2026-05-28.
