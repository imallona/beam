# 0006 - Same-data pancreas contrast: pipeline matters even when the data is shared

- Status: Active
- Date: 2026-05-28
- Dataset: the human pancreas data shared between Tran et al. 2020 (its Dataset 4) and scIB (its pancreas task). Both are built from the same five studies (Muraro GSE85241, Segerstolpe E-MTAB-5061, Baron GSE84133, Wang GSE83139, Xin GSE81608). Bundled as src/beam/data/scib2022_metrics.csv and tran2020_metrics.csv. The cross-benchmark set also covers OpenProblems batch_integration, but its datasets are cellxgene-census atlases, not the pancreas, so it does not enter this contrast.
- Authors: Izaskun Mallona
- Commit: pending
- Manifest: tests/test_datasets_integration.py (`test_load_pancreas_contrast`) and examples/cross_benchmark/cross_benchmark.qmd

## Observation

On the same five pancreas studies, the two pipelines agree that harmony ranks first among the five common methods (combat, harmony, fastMNN, scanorama, LIGER), but the rest of the order disagrees more than a pooled cross-benchmark mean Spearman of +0.50 would predict. The Spearman of the per-method mean ranks (over ARI, ASW, kBET, LISI) is +0.46. The methods that move: LIGER ranks second on Tran D4 (it placed first on Tran's kBET and LISI columns) and tied last on scIB pancreas (mean rank 4.0 of 5). fastMNN ranks second on scIB pancreas but fourth on Tran D4. Per-method mean ranks (1 ranks first, 5 ranks last):

| method     | Tran D4 | scIB pancreas |
|------------|---------|---------------|
| harmony    | 1.5     | 1.5           |
| LIGER      | 2.0     | 4.0           |
| scanorama  | 3.0     | 3.5           |
| fastMNN    | 4.0     | 2.0           |
| combat     | 4.5     | 4.0           |

The two pipelines also have markedly different fragility on their own benchmark mean-rank matrix. The smallest single-weight change (Triantaphyllou-Sanchez closed form) that flips the top method under SAW with equal weights is 0.11 absolute on the ASW weight for OpenProblems (fastMNN flips to harmony), 0.24 on ASW for Tran (harmony flips to LIGER), and 0.90 on LISI for scIB (fastMNN flips to LIGER, past the feasible weight range).

## Method

`beam.datasets.load_pancreas_contrast` selects Tran's Dataset 4 rows from `tran2020_metrics.csv` and the pancreas rows from `scib2022_metrics.csv`. The scIB cells average the two feature-space rows (HVG and full, both unscaled) so the rank does not depend on row order. Within each metric, both pipelines are re-ranked among the five common methods, with the Tran re-ranking inverted (lower is better in the source) and the scIB re-ranking oriented to higher is better. The Spearman uses `scipy.stats.spearmanr` on the per-method mean ranks. The fragility uses `beam.mcda.smallest_weight_perturbation` with SAW and equal weights on each benchmark's method-by-metric mean-rank matrix (`IntegrationBenchmarks.method_metric_matrix`).

The fix to the loader is a real correctness change. The scIB source carries two unscaled rows per (dataset, method, metric) for most cells, one per feature space; the earlier loader silently kept only the second row, making the result depend on row order. The new loader averages them. The thresholds in the cross-benchmark agreement test stayed loose enough that the headline +0.60 rise in mean Spearman is unchanged.

## Implications

The dataset confound that limited findings 0005 is removed on the one shared block. The pipeline difference is real and visible on the pancreas alone: a Spearman of 0.46 between Tran D4 and scIB pancreas, on the same data, the same metrics and the same methods. This is a stronger claim than the pooled benchmark-variance estimate, because no data variability remains in the contrast. The leader is the same (harmony), which is consistent with the pooled finding that harmony is a stable top choice across all three benchmarks. The fragility result complements the contrast: each benchmark's top method sits at a different distance from a flip under the same equal-weights rule, so the recommendation strength is itself benchmarker-dependent.

The limits: one shared dataset family is too thin for a separate variance estimate, and the Tran metric values are published ranks (Table S7) rather than raw scores, so the comparison is between two rank-based pipelines, not between two raw-score pipelines.

## Reproducibility

- Notebook or script: `examples/cross_benchmark/cross_benchmark.qmd` (Same data, two pipelines and Per-benchmark fragility sections); test `tests/test_datasets_integration.py::test_load_pancreas_contrast` and `test_per_benchmark_smallest_weight_perturbation`
- Run manifest: the bundled tables `scib2022_metrics.csv` and `tran2020_metrics.csv` plus the deterministic `load_pancreas_contrast` and `smallest_weight_perturbation` calls
- Commit: pending
- Software environment: Python 3.12 with numpy and scipy, beam at HEAD

## Related

- Builds on [findings 0005](0005-cross-benchmark-integration-agreement.md) (the pooled cross-benchmark agreement). The pancreas contrast is the unconfounded version of the same question on the one shared block.
- Method in [ADR 0013](../adr/0013-missing-data-policy.md) (the never-impute rule explains why the loader averages rather than silently keeps one row).
- External references: Luecken et al. Nature Methods 2022. DOI 10.1038/s41592-021-01336-8; Tran et al. Genome Biology 2020. DOI 10.1186/s13059-019-1850-9; Triantaphyllou and Sanchez 1997, A sensitivity analysis approach for some deterministic multi-criteria decision-making methods. Decision Sciences 28(1):151-194.
