# Comparing two methods at a time

The [critical-difference diagram](comparing-methods-across-datasets.md) says which methods differ beyond chance. It does not say by how much, or how often one method outperforms another. Its mean-rank post-hoc also depends on the whole pool: add or drop a method and two others can change from "different" to "the same" (Benavoli, Corani and Mangili 2016). [`beam.mcda.pairwise_superiority`](../reference/pairwise_superiority.qmd) reports an effect size that does not depend on the pool.

## How it works

For a pair of methods, look at the datasets they share. On each one, the method with the higher score outperforms the other on that dataset, for that metric. Over the datasets this gives three numbers: how often A outperforms B, how often B outperforms A, and how often the two are equivalent.

Two methods are equivalent on a dataset when their scores differ by no more than the region of practical equivalence, the ROPE. Set the ROPE to the metric's [noise floor](reference-levels.md) (`comparability.noise_floor`), the smallest difference the card calls interpretable, and one method counts as outperforming the other only when the difference clears that floor. With a ROPE of zero, any non-zero difference counts.

The probability of superiority of A over B is the fraction of shared datasets on which A outperforms B. It is a common-language effect size, the standard name for it (Grissom 1994): how often A scores higher than B on a dataset like these. A sign test on the decisive datasets, equivalences dropped, says whether the difference is more than chance.

## What it reports

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

## On real data

On the [Duo 2018](../../examples/duo2018/duo2018.qmd) Adjusted Rand Index (ARI) scores, with the ARI noise floor of 0.01 as the ROPE, SC3 has the highest standing. But most method pairs are practically equivalent: the sign test cannot separate more than half of them, because the differences across the twelve datasets are often within the noise floor. This agrees with the critical-difference reading, where most methods fall in overlapping cliques, and states it as an effect size: even the two leading methods are within the floor on most datasets rather than one clearly outperforming the other.

## Related checks

[`critical_difference`](comparing-methods-across-datasets.md) tests significance across all methods at once. [`noise_floor_separation`](reference-levels.md) reads the aggregate scores, one value per method, and flags pairs no metric separates above the floor. `pairwise_superiority` works across the datasets, pair by pair, and reports an effect size with the noise floor as the equivalence band. Significance, aggregate separation, and per-dataset effect size are three readings of the same question.

## Limitations

The probability of superiority describes these datasets, not a population of datasets. The sign test drops equivalences, so a pair that is equivalent on most datasets has few decisive ones and a weak test, which is the expected reading when the methods are close. The comparison is paired by dataset, so it needs the same datasets for both methods; a pair with little overlap is compared on whatever they share, and the count says how many that was.

## References

- Benavoli, A., Corani, G., Mangili, F.. Should we really use post-hoc tests based on mean-ranks?. Journal of Machine Learning Research 17 (2016).
- Grissom, R. J.. Probability of the superior outcome of one treatment over another. Journal of Applied Psychology (1994). DOI [10.1037/0021-9010.79.2.314](https://doi.org/10.1037/0021-9010.79.2.314).
