# 0002 - Duo 2018 clustering benchmark, mixed-effects variance decomposition of ARI

- Status: Active
- Date: 2026-05-25
- Dataset: Duo, Robinson and Soneson (2018), 14 methods by 12 datasets by 4 metrics (bundled DuoSCClustering2018.csv)
- Authors: Izaskun Mallona
- Commit: pending
- Manifest: tests/test_heterogeneity_mixed_effects.py (test_duo_ari_decomposition)

## Observation

Fitting `score ~ method + (1 | dataset)` on the 163 observed ARI cells (5 of the 168 are missing), the between-dataset variance is 0.0579 and the residual variance is 0.0239, so the dataset intercept accounts for 0.708 of the total ARI variance (ICC). Most of the spread in ARI is datasets being uniformly easy or hard for every method, not methods reordering across datasets. The method marginal means rank SC3 first (0.853), Seurat second (0.847) and SC3svm third (0.823), with RaceID2 (0.484) and FlowSOM (0.521) clearly last; the standard error on each mean is about 0.083, so the top three are not separable from one another and the bottom two are separated from the rest. The fit is not singular and lme4 raised no convergence warning (logLik 30.3, AIC -28.6). The largest residuals, the cells where a method departs most from what its global effect predicts, are RaceID2 on SimKumar4hard (-0.50) and SimKumar8hard (-0.43), then RaceID2 on Zhengmix4eq (+0.42) and FlowSOM on Zhengmix4uneq (-0.40) and Zhengmix4eq (-0.39): the interaction signal is concentrated in the two weakest methods on the simulated and the four-group Zhengmix datasets.

## Method

Loaded the tensor with `beam.datasets.load_duo2018`, took the ARI slice, and called `beam.heterogeneity.mixed_effects_from_matrix`, which flattens the 14 by 12 matrix to long format, drops the 5 NaN cells, and fits lme4 through the one-shot R subprocess (ADR 0009). With one observation per (method, dataset) cell the method-by-dataset interaction cannot be separated from measurement noise, so the residual is their sum and is read as the upper bound on the interaction; separating it would need a multi-run benchmark. The method is fixed and the dataset is a random intercept, so the marginal means are the fitted method scores averaged over datasets, with standard errors from the fixed-effect covariance. Variance components and the ICC come from `VarCorr`.

## Implications

The variance decomposition is the formal complement to the leave-one-dataset-out check in [findings 0001](0001-duo-2018-mcda.md). Leave-one-dataset-out showed Seurat's composite rank is stable to dropping any single dataset. This result shows why that stability is plausible on ARI: two thirds of the ARI variance is a shared dataset shift rather than methods trading places. The residual share of 0.29 is the headroom for genuine method-by-dataset interaction plus noise, and the outlier cells point to where it sits: the two weakest methods on a few specific datasets, not a broad reshuffling of the strong methods. This is consistent with the critical-difference reading in findings 0001, where the upper-middle methods were not separable. The identifiability limit is this: at one run per cell beam cannot say how much of that 0.29 is interaction and how much is noise. A Gaussian likelihood on a bounded metric is also an approximation near 0 and 1. Both are addressed by the documented extensions, multi-run inputs and a glmmTMB beta family.

## Reproducibility

- Notebook or script: tests/test_heterogeneity_mixed_effects.py (test_duo_ari_decomposition)
- Run manifest: the test pins SC3 and Seurat as the two leading ARI marginal means, RaceID2 among the largest residual cells, and the main-effects model on the 163 observed cells
- Commit: pending
- Software environment: R 4.3.3, lme4; Python 3.12, numpy, the beam-heterogeneity conda environment (envs/heterogeneity.yml)

## Related

- Builds on [findings 0001](0001-duo-2018-mcda.md) (the MCDA re-analysis and the leave-one-dataset-out stability)
- Method explained in [the mixed-effects explanation](../explanations/heterogeneity-mixed-effects.md); decision in [ADR 0009](../adr/0009-heterogeneity-mixed-effects-via-r.md)
- External references: Eugster M, Hothorn T, Leisch F. (Psycho-)Analysis of Benchmark Experiments. 2008. Duo A, Robinson MD, Soneson C. F1000Research 2018, 7:1141. DOI 10.12688/f1000research.15666.3
