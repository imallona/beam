# Duo 2018 clustering benchmark

This folder will hold the reproducible vignette that re-analyses the
fourteen single-cell clustering methods from Duo et al. 2018 with beam.

The vignette is not yet written. When complete it will:

1. Load the scores from the prior MCDA work into a tool by metric tensor.
2. Look up ARI, runtime, Shannon entropy difference, and cluster-count
   deviation metric cards from the beam registry.
3. Run the MCDA decision module with several weighting schemes.
4. Produce a sensitivity analysis and a one-paragraph recommendation.
