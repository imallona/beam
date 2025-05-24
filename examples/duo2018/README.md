# Duo 2018 clustering benchmark

This folder holds the walkthrough vignette and will host the full re-analysis of the fourteen single-cell clustering methods from Duo et al. 2018.

`duo2018.qmd` is a starter vignette. It pulls metric polarity from the beam registry and runs the MCDA pipeline (normalise, weight, aggregate, rank) on a small synthetic tool by metric table.

To finish the re-analysis we still need to:

1. Replace the synthetic matrix with the 14 methods by 12 datasets by 4 metrics tensor from Duo et al. 2018.
2. Aggregate within each dataset, then across datasets.
3. Compare to the rankings reported in the original paper.
4. Add the sensitivity layer: alternative weight schemes, leave-one-metric-out, weight perturbation.
