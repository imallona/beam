# Pairwise method comparison

The [critical-difference diagram](critical-difference.md) says which methods differ beyond chance across the datasets. It does not say by how much, how often one method outperforms another, or whether the pairwise results agree with a single order. Its mean-rank post-hoc also depends on the whole pool: add or drop a method and two others can change from "different" to "the same" (Benavoli, Corani and Mangili 2016). beam has three pool-independent checks that read the same pairwise evidence: a frequentist effect size, a transitivity test, and a Bayesian posterior.

## The pairwise counts

For a pair of methods, look at the datasets they share. On each the method with the higher score outperforms the other. Over the datasets this gives three counts: how often A outperforms B, how often B outperforms A, and how often the two are equivalent.

Two methods are equivalent on a dataset when their scores differ by no more than the region of practical equivalence, the ROPE. Set the ROPE to the metric's [noise floor](reference-levels.md) (`comparability.noise_floor`), the smallest difference the card calls interpretable; a method outperforms the other only when the difference clears that floor. With a ROPE of zero, any non-zero difference counts.

## Probability of superiority

[`beam.mcda.pairwise_superiority`](../reference/pairwise_superiority.qmd) reports the effect size. The probability of superiority of A over B is the fraction of shared datasets on which A outperforms B, a common-language effect size (Grissom 1994). A sign test on the decisive datasets, equivalences dropped, says whether the difference is more than chance.

```python
from beam.mcda import pairwise_superiority
from beam.cards import properties_for

floor = properties_for(["ari"])[0].noise_floor
report = pairwise_superiority(ari_by_dataset, "higher_is_better", rope=floor,
                              method_names=method_names)
report.order[0]              # the method with the highest standing
report.probability_superior  # P(row outperforms column), a matrix
report.equivalent_pairs      # pairs the sign test cannot tell apart
```

`standing` is a Copeland-style score per method: the mean over the other methods of the chance of outperforming or being equivalent to them, in `[0, 1]`. One outperforms every other method on every dataset, 0.5 is even. `equivalent_pairs` lists the pairs whose sign test does not reach the chosen level, so no decisive difference.

On the [Duo 2018](../../examples/duo2018/duo2018.qmd) Adjusted Rand Index (ARI) scores, with the ARI noise floor of 0.01 as the ROPE, SC3 has the highest standing. Most method pairs are practically equivalent: the sign test cannot separate more than half of them, because the differences across the twelve datasets are often within the noise floor. Even the two leading methods are within the floor on most datasets rather than one clearly outperforming the other.

## Transitivity

An aggregation returns one ordering of the methods. That ordering is a fair summary only when the pairwise comparisons behind it agree with a single order. Method A can outperform B on most of the datasets they share, B outperform C, and C outperform A: a cycle, and no ordering agrees with all the pairwise majorities.

[`beam.mcda.pairwise_transitivity`](../reference/pairwise_transitivity.qmd) reads the superiority report and turns the counts into a single relation: method `i` outperforms method `j` when it does so more often than `j` outperforms `i` across their shared datasets. A pair that splits evenly, or that shares no decisive dataset, is left with no edge and recorded as tied. Because the counts already apply the ROPE, a difference inside the noise floor does not create an edge, so near-ties do not produce spurious cycles.

From the relation the function reports four things.

- The method preferred to every other method by pairwise majority, when one exists. Condorcet described this case in his 1785 essay on majority voting. Such a method might not exist, and when it does the rest of the relation can still be inconsistent.
- The circular triads: sets of three methods whose edges form a cycle. Their count, out of all method triples, measures how far the relation is from transitive.
- Kendall and Babington Smith's (1940) coefficient of consistence, `1 - d / d_max`, where `d` is the circular-triad count and `d_max` is the maximum possible for this relation size. It runs from 1 (transitive) down to 0 (least consistent). It is defined only when every pair is decided, so it is reported as undefined when any pair is tied.
- Whether the relation is transitive, and the single order it implies when it is transitive and every pair is decided.

```python
from beam.mcda import pairwise_transitivity

trans = pairwise_transitivity(report)
trans.is_transitive          # whether one order is consistent with the pairwise majorities
trans.circular_triads        # the cyclic triples, if any
trans.condorcet_choice       # method preferred to all others, or None
trans.coefficient_of_consistence  # Kendall's coefficient, or None when pairs are tied
```

On the Duo 2018 ARI scores, with the noise floor of 0.01 as the equivalence band, SC3 is preferred to every other method by pairwise majority, the same method the standing score, the marginal means and the [Bradley-Terry ranking](method-by-dataset-heterogeneity.md#bradley-terry-trees) pick out. Even so the relation is not transitive: there is a cycle and no single order agrees with every pairwise majority. The cycle is among methods that the critical-difference diagram and the pairwise effect sizes already place in overlapping groups, where a few datasets can swing the majority either way. Raising the equivalence band from zero to the noise floor cuts the cycles from five to one.

## Bayesian sign comparison

The sign test and the critical-difference diagram report a p-value, the chance of the observed split if the two methods scored the same. [`beam.mcda.bayesian_sign_comparison`](../reference/bayesian_sign_comparison.qmd) reports the probability that one method scores higher than the other given the data, using the Bayesian sign test of Benavoli et al. (2017) on the same per-pair counts.

For a method pair, each shared dataset falls into one of three regions: A scores higher by more than the ROPE, B scores higher by more than the ROPE, or the two are within it. The test models the three shares with a Dirichlet posterior whose parameters are the observed counts plus a small prior, and reports three probabilities that sum to one: that A is practically better than B, that the two are practically equivalent, and that B is practically better than A. A pair gets a decisive label when one of the three reaches the threshold (0.95 by default), and is inconclusive otherwise. The report also carries the posterior mean share of each region and a standing score per method, the mean over the other methods of the probability of scoring at least as high as them.

The default places one prior pseudo-observation on the equivalence region, matching the baycomp default. Two other placements are available: `uniform` spreads the prior across the three regions, and `neutral` spreads it across the two directional regions. One pseudo-observation is outweighed after a few datasets.

## Related checks

[`critical_difference`](critical-difference.md) tests separability across all methods at once. [`noise_floor_separation`](reference-levels.md) reads the aggregate scores, one value per method, and flags pairs no metric separates above the floor. [`aggregation_agreement`](choice-agreement.md) shows when the aggregation rules disagree; a cycle in the pairwise relation is one reason they can.

## Limitations

These reports describe the datasets in hand, not a population of datasets. The comparison is paired by dataset, so it needs the same datasets for both methods; a pair with little overlap is compared on whatever they share, and the count says how many that was. The sign test drops equivalences, so a pair equivalent on most datasets has few decisive ones and a weak test. The Bayesian posterior stays close to the prior when the datasets are few, so most pairs are inconclusive at the threshold. All three use only the direction of each dataset's difference, not its size, and all depend on the ROPE, so set the band from the metric's noise floor.

## References

- Benavoli, A., Corani, G., Mangili, F. Should we really use post-hoc tests based on mean-ranks? Journal of Machine Learning Research 17 (2016).
- Grissom, R. J. Probability of the superior outcome of one treatment over another. Journal of Applied Psychology (1994). DOI [10.1037/0021-9010.79.2.314](https://doi.org/10.1037/0021-9010.79.2.314).
- Condorcet, M. de. Essai sur l'application de l'analyse a la probabilite des decisions rendues a la pluralite des voix. Imprimerie Royale, Paris (1785).
- Kendall, M. G., Babington Smith, B. On the method of paired comparisons. Biometrika 31, 324 (1940). DOI [10.1093/biomet/31.3-4.324](https://doi.org/10.1093/biomet/31.3-4.324).
- Benavoli, A., Corani, G., Demsar, J., Zaffalon, M. Time for a change: a tutorial for comparing multiple classifiers through Bayesian analysis. Journal of Machine Learning Research 18(77):1-36 (2017). https://jmlr.org/papers/v18/16-305.html
- Corani, G., Benavoli, A. A Bayesian approach for comparing cross-validated algorithms on multiple data sets. Machine Learning 100(2-3):285-304 (2015). https://doi.org/10.1007/s10994-015-5486-z

The reference implementation is the baycomp package (https://github.com/janezd/baycomp), against which beam is cross-checked.
