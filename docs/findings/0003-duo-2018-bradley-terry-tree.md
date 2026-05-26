# 0003 - Duo 2018 clustering benchmark, Bradley-Terry tree on ARI

- Status: Active
- Date: 2026-05-26
- Dataset: Duo, Robinson and Soneson (2018), 14 methods by 12 datasets by 4 metrics (bundled DuoSCClustering2018.csv) with the bundled dataset features (DuoSCClustering2018_features.csv)
- Authors: Izaskun Mallona
- Commit: pending
- Manifest: tests/test_heterogeneity_bradley_terry.py (test_tree_on_duo_ari_runs)

## Observation

Fitting a Bradley-Terry tree on the per-dataset ARI comparisons, with the four dataset features (number of cells, number of true clusters, real vs simulated, dataset family) as candidate splitting variables, the parameter-stability test finds no split: the tree degrades to a single Bradley-Terry model over all 12 datasets. The result holds when the test is loosened: no split appears down to a minimal node size of 2 datasets at alpha 0.1. The flat Bradley-Terry strengths rank SC3 first (worth 0.289, standard error 0.050), then RtsneKmeans (0.114), Seurat (0.110) and SC3svm (0.102), with FlowSOM (0.011) and RaceID2 (0.009) last. This ordering matches the net pairwise-win count over the same comparisons and the marginal-mean ordering from the mixed-effects fit in findings 0002 (SC3 and Seurat at the top, RaceID2 and FlowSOM at the bottom).

## Method

Loaded the tensor with `beam.datasets.load_duo2018`, took the ARI slice, and loaded the dataset features with `beam.datasets.load_duo2018_features`. `beam.heterogeneity.paired_comparisons` turned the 14 by 12 matrix into per-dataset paired method comparisons (a win for the higher ARI, a tie on exact equality, a missing comparison where a cell is NaN), and `beam.heterogeneity.bradley_terry_tree` fit `psychotree::bttree(preference ~ features)` through the one-shot R subprocess (ADR 0010). The datasets are the subjects whose features split the tree; the methods are the objects compared. The dataset features come from the DuoClustering2018 package help files: 9 real and 3 simulated datasets, true cluster counts from 3 to 9, cell counts from 222 to 6500, and five dataset families (Koh, Kumar, SimKumar, Trapnell, Zhengmix); their provenance is recorded in src/beam/data/README.md.

## Implications

Model-based recursive partitioning needs enough subjects to support a split. At 12 datasets the parameter-stability test cannot separate a feature-dependent regime from sampling noise. The same limit appears in the critical-difference diagram (findings 0001, the upper-middle methods were not separable) and in the mixed-effects fit (findings 0002, two thirds of the ARI variance is a shared dataset shift rather than methods trading places). All three diagnostics agree: on this benchmark the global ranking is stable and there is no evidence of a dataset feature that reverses it. The Bradley-Terry tree is more useful on a benchmark with many datasets carrying real feature variation. The synthetic regime-split test in the same test file shows the tree recovers a feature split and the per-leaf ranking reversal when the signal is present and the datasets are sufficient. The OpenProblems tasks are the intended richer real input.

## Reproducibility

- Notebook or script: tests/test_heterogeneity_bradley_terry.py (test_tree_on_duo_ari_runs for the Duo run, test_tree_finds_regime_split for the positive control)
- Run manifest: the test pins the flat degradation on Duo (did_split is False), the leaf assignment over 12 datasets, and SC3 as the leading global strength
- Commit: pending
- Software environment: R 4.3.3, psychotree, partykit, psychotools; Python 3.12, numpy, the beam-heterogeneity conda environment (envs/heterogeneity.yml)

## Related

- Completes the heterogeneity reading of Duo started in [findings 0001](0001-duo-2018-mcda.md) (MCDA and leave-one-dataset-out) and [findings 0002](0002-duo-2018-variance-decomposition.md) (variance decomposition)
- Method explained in [the Bradley-Terry trees explanation](../explanations/heterogeneity-bradley-terry.md); decision in [ADR 0010](../adr/0010-bradley-terry-trees.md)
- External references: Strobl C, Wickelmaier F, Zeileis A. Accounting for individual differences in Bradley-Terry models by means of recursive partitioning. Journal of Educational and Behavioral Statistics 2011. Duo A, Robinson MD, Soneson C. F1000Research 2018, 7:1141. DOI 10.12688/f1000research.15666.3
