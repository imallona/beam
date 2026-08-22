# Pairwise method comparison

The [critical-difference diagram](critical-difference.md) tests which methods differ across datasets. Its mean-rank post-hoc depends on the whole pool: adding or dropping a method can change the result for two others (Benavoli, Corani and Mangili 2016). beam has three checks on pairs of methods that do not depend on the pool: an effect size, a transitivity test, and a Bayesian posterior.

## Pairwise counts

For two methods and the datasets they share, beam counts how often A outperforms B, how often B outperforms A, and how often they are equivalent.

Two methods are equivalent on a dataset when their scores differ by at most the region of practical equivalence (ROPE). The metric's [noise floor](reference-levels.md) (`comparability.noise_floor`) is the usual ROPE. With a ROPE of zero, any difference counts.

## Probability of superiority

[`beam.mcda.pairwise_superiority`](../reference/pairwise_superiority.qmd) reports the fraction of shared datasets on which A outperforms B, a common-language effect size (Grissom 1994), and a sign test on the datasets where the two are not equivalent.

```python
from beam.mcda import pairwise_superiority
from beam.cards import properties_for

floor = properties_for(["ari"])[0].noise_floor
report = pairwise_superiority(ari_by_dataset, "higher_is_better", rope=floor,
                              method_names=method_names)
report.order[0]              # the method with the highest standing
report.probability_superior  # P(row outperforms column), a matrix
report.equivalent_pairs      # pairs the sign test does not separate
```

`standing` is a Copeland-style score per method in `[0, 1]`: the mean over the other methods of the chance of outperforming or being equivalent to them.

## Transitivity

A can outperform B on most shared datasets, B outperform C, and C outperform A. No ordering agrees with such a cycle.

[`beam.mcda.pairwise_transitivity`](../reference/pairwise_transitivity.qmd) takes the superiority report. Method `i` is preferred to method `j` when it outperforms `j` more often than the reverse. A pair with equal counts is tied. The counts already apply the ROPE.

The report has:

- The method preferred to every other by pairwise majority, when one exists (Condorcet 1785).
- The circular triads: sets of three methods whose preferences form a cycle.
- The coefficient of consistence of Kendall and Babington Smith (1940), `1 - d / d_max`, with `d` the number of circular triads and `d_max` its maximum for this number of methods. It is 1 for a transitive relation and undefined when any pair is tied.
- Whether the relation is transitive, and the order it implies when every pair is decided.

```python
from beam.mcda import pairwise_transitivity

trans = pairwise_transitivity(report)
trans.is_transitive
trans.circular_triads
trans.condorcet_choice            # method preferred to all others, or None
trans.coefficient_of_consistence  # None when pairs are tied
```

## Bayesian sign comparison

[`beam.mcda.bayesian_sign_comparison`](../reference/bayesian_sign_comparison.qmd) applies the Bayesian sign test of Benavoli et al. (2017) to the same counts.

Each shared dataset is in one of three regions: A higher by more than the ROPE, B higher by more than the ROPE, or within it. A Dirichlet posterior on the three shares, with the counts plus a prior as parameters, gives the probabilities that A is practically better, that the two are practically equivalent, and that B is practically better. A pair is decided when one of them reaches the threshold (0.95 by default). The report also has the posterior mean share per region and a standing score per method.

The default prior is one pseudo-observation on the equivalence region, as in baycomp. `uniform` spreads it over the three regions and `neutral` over the two directional ones.

## Limits

The comparison is paired by dataset and uses only the direction of each difference, not its size. The sign test drops equivalent datasets, so a pair equivalent on most datasets has a weak test. With few datasets the posterior is close to the prior. All three depend on the ROPE.

## References

- Benavoli, A., Corani, G., Mangili, F. Should we really use post-hoc tests based on mean-ranks? Journal of Machine Learning Research 17 (2016).
- Grissom, R. J. Probability of the superior outcome of one treatment over another. Journal of Applied Psychology (1994). DOI [10.1037/0021-9010.79.2.314](https://doi.org/10.1037/0021-9010.79.2.314).
- Condorcet, M. de. Essai sur l'application de l'analyse a la probabilite des decisions rendues a la pluralite des voix. Imprimerie Royale, Paris (1785).
- Kendall, M. G., Babington Smith, B. On the method of paired comparisons. Biometrika 31, 324 (1940). DOI [10.1093/biomet/31.3-4.324](https://doi.org/10.1093/biomet/31.3-4.324).
- Benavoli, A., Corani, G., Demsar, J., Zaffalon, M. Time for a change: a tutorial for comparing multiple classifiers through Bayesian analysis. Journal of Machine Learning Research 18(77):1-36 (2017). https://jmlr.org/papers/v18/16-305.html
- Corani, G., Benavoli, A. A Bayesian approach for comparing cross-validated algorithms on multiple data sets. Machine Learning 100(2-3):285-304 (2015). https://doi.org/10.1007/s10994-015-5486-z

The reference implementation is the baycomp package (https://github.com/janezd/baycomp), against which beam is cross-checked.
