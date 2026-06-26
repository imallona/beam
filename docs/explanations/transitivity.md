# Whether one ranking is consistent with the pairwise evidence

Every aggregation in beam returns one ordering of the methods. That ordering is a
fair summary only when the pairwise comparisons behind it agree with a single
order. They do not always agree. Method A can outperform B on most of the datasets
they share, B outperform C, and C outperform A. These three results form a cycle.
When a cycle is present, no ordering of the methods agrees with all the pairwise
majorities, so the order an aggregation reports is in part a property of the rule,
not of the methods.

`beam.mcda.pairwise_transitivity` checks for this. It reads the pairwise
superiority report and asks whether the pairwise majority relation admits one
consistent order.

## How it works

For each pair of methods, `pairwise_superiority` already counted how often each one
outperforms the other across the datasets they share. `pairwise_transitivity` turns
those counts into a single relation: method i outperforms method j when it does so
on more of their shared datasets than j does. A pair that splits evenly, or that
shares no decisive dataset, is left with no edge and recorded as tied. Because the
counts already apply the region of practical equivalence, a difference inside the
noise floor does not create an edge, so near-ties do not produce spurious cycles.

From the relation the function reports four things.

- The method preferred to every other method by pairwise majority, when one
  exists. Condorcet described this case in his 1785 essay on majority voting; it is
  the option preferred to every other one in a head-to-head majority vote. Such a
  method need not exist, and when it does the rest of the relation can still be
  inconsistent.
- The circular triads: sets of three methods whose edges form a cycle. Their count,
  out of all method triples, measures how far the relation is from transitive.
- Kendall and Babington Smith's (1940) coefficient of consistence, `1 - d / d_max`,
  where `d` is the circular-triad count and `d_max` is the most a relation of this
  size can hold. It runs from 1 (transitive) down to 0 (least consistent). It is
  defined only when every pair is decided, so it is reported as undefined when any
  pair is tied.
- Whether the relation is transitive, and the single order it implies when it is
  transitive and every pair is decided.

## What it reports

```python
from beam.mcda import pairwise_superiority, pairwise_transitivity
from beam.cards import properties_for

floor = properties_for(["ari"])[0].noise_floor
sup = pairwise_superiority(ari_by_dataset, "higher_is_better", rope=floor,
                           method_names=method_names)
trans = pairwise_transitivity(sup)
trans.is_transitive          # whether one order is consistent with the pairwise majorities
trans.circular_triads        # the cyclic triples, if any
trans.condorcet_choice       # method preferred to all others, or None
trans.coefficient_of_consistence  # Kendall's coefficient, or None when pairs are tied
```

## On real data

On the [Duo 2018](../../examples/duo2018/duo2018.qmd) Adjusted Rand Index (ARI) scores, with the ARI noise floor of 0.01 as the equivalence
band, SC3 is preferred to every other method by pairwise majority, the same method
the standing score, the marginal means and the [Bradley-Terry ranking](heterogeneity-bradley-terry.md) pick out. Even
so the relation is not transitive: one circular triad sits among the other methods,
so no single order agrees with every pairwise majority. The cycle is among methods
that the critical-difference diagram and the pairwise effect sizes already place in
overlapping groups, which is where a few datasets can swing the majority either way.
Raising the equivalence band from zero to the noise floor cuts the cycles from five
to one, so most of the apparent intransitivity is differences inside the floor.

The reading is that SC3 is a stable first choice on Duo, but the order among the
methods below it is not settled by the pairwise evidence, and the noise floor is
what separates a real cycle from one made of differences too small to interpret.

## How it relates to the other checks

[`critical_difference`](comparing-methods-across-datasets.md) tests whether the methods are separable across datasets on one
metric. [`pairwise_superiority`](pairwise-superiority.md) reports, pair by pair, how often one outperforms the
other. `pairwise_transitivity` reads that same pairwise relation and asks the prior
question: does a single ranking even make sense here, or do the pairwise results
contradict each other. [`aggregation_agreement`](aggregation-agreement.md) shows that the aggregation rules
disagree; a cycle is one reason they can. Each check answers a different question,
so they are best read together.

## Limitations

The relation describes these datasets, not a population of datasets. Transitivity is
a property of the majority counts, so a relation with many tied pairs gives a partial
order rather than a full one, and the coefficient of consistence is then undefined
because it assumes every pair is decided. The check says whether a consistent order
exists; it does not, on its own, choose one when a cycle is present. The headline
remains that a reported ranking should be read alongside whether the pairwise
evidence supports any single order at all.

## References

- Condorcet, M. de. Essai sur l'application de l'analyse a la probabilite des
  decisions rendues a la pluralite des voix. Imprimerie Royale, Paris (1785).
- Kendall, M. G., Babington Smith, B.. On the method of paired comparisons.
  Biometrika 31, 324 (1940). DOI [10.1093/biomet/31.3-4.324](https://doi.org/10.1093/biomet/31.3-4.324).
