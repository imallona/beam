# Duo 2018 clustering benchmark

This folder holds the walkthrough vignette and will host the full re-analysis of the fourteen single-cell clustering methods from Duo et al. 2018.

`duo2018.qmd` is a starter vignette. It pulls per-metric properties (polarity, scale_type, declared range, allowed transformations, recommended cross-dataset aggregation) from the beam registry via `properties_for`, runs the MCDA pipeline through `run_from_registry`, and reports leave-one-metric-out stability, SMAA weight sampling, and Triantaphyllou-Sanchez weight perturbation on a small synthetic tool by metric table.

To finish the re-analysis we still need to:

1. Replace the synthetic matrix with the 14 methods by 12 datasets by 4 metrics tensor from Duo et al. 2018.
2. Aggregate within each dataset, then across datasets using `aggregate_across_datasets` with the per-metric rule from the card.
3. Add cards for Shannon entropy difference and cluster-count deviation.
4. Compare to the rankings reported in the original paper.
