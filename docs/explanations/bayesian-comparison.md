# Bayesian comparison of two methods

The critical-difference diagram and the pairwise superiority report p-value, as they test the chance of the observed split if the two methods scored the same. For analysts choosing a method that score is not that informative; ideally, the probability that one method scores higher than the other given the data is more informative. `beam.mcda.bayesian_sign_comparison` reports the latter, using the Bayesian sign test of Benavoli et al. (2017) on the same per-pair counts `pairwise_superiority` produces.

## Procedure

For a method pair, each shared dataset falls into one of three regions: A scores higher by more than the region of practical equivalence (the ROPE), B scores higher by more than the ROPE, or the two sit within the ROPE. The ROPE is taken from the superiority report, often the metric's noise floor, so a difference too small to interpret counts as a tie.

The share of datasets in each region is unknown. The test models the three shares with a Dirichlet posterior whose parameters are the observed counts plus a small prior. The function reports three probabilities that sum to one: that A is practically better than B, that the two are practically equivalent, and that B is practically better than A.

A pair gets a decisive label when one of the three reaches the threshold (0.95 by default), and is inconclusive otherwise. The function also reports the posterior mean share of each region, the Dirichlet mean. It reports a standing score per method: the mean over the other methods of the probability of scoring at least as high as them.

The default places one prior pseudo-observation on the equivalence region, matching the baycomp default. Two other placements are available: `uniform` spreads the prior across the three regions, and `neutral` spreads it across the two directional regions. One pseudo-observation is outweighed after a few datasets.

## Relation to the other comparison tools

beam's four comparison tools read the same tool by dataset evidence and answer different questions:

1. The critical-difference diagram tests separability on one metric. 
2. The pairwise superiority report gives a frequentist effect size and a sign-test p-value. 
3. The transitivity check asks whether the pairwise majorities admit one consistent order. 
4. The Bayesian sign test reports the probability that A is practically better than B.

## Limits

The posterior describes the datasets in hand, not a population of datasets. With few datasets most pairs are inconclusive at the threshold. The result depends on the ROPE, so set the band from the metric's noise floor. The sign test uses only the direction of each dataset's difference, not its size.

## References

Benavoli A, Corani G, Demsar J, Zaffalon M. Time for a change: a tutorial for comparing multiple classifiers through Bayesian analysis. Journal of Machine Learning Research 2017, 18(77):1-36. <https://jmlr.org/papers/v18/16-305.html>

Corani G, Benavoli A. A Bayesian approach for comparing cross-validated algorithms on multiple data sets. Machine Learning 2015, 100(2-3):285-304. <https://doi.org/10.1007/s10994-015-5486-z>

The reference implementation is the baycomp package (<https://github.com/janezd/baycomp>), against which beam is cross-checked.
