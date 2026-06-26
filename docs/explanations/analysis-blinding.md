# Analysis blinding

If a benchmarker can see which method is which while choosing the [weighting](weighting-schemes.md), the [aggregation](aggregation-methods.md) and the metric set, those choices can shift toward a preferred method. This can happen via unconscious biases and without intent. Different choices give different rankings, and it is easy to settle on the one that fits an expected result (Gelman and Loken 2013; Simmons, Nelson and Simonsohn 2011). One way to avoid it is blind analysis: run the analysis on methods whose labels are hidden, then reveal the labels (MacCoun and Perlmutter 2015; Klein and Roodman 2005).

`beam.blind` applies this to a score table. It replaces the tool names with opaque labels and shuffles the rows under a seed, so neither the names nor the order carry the methods' identity. The analyst runs the full beam pipeline on the blinded scores, fixes the configuration, then calls `beam.unblind` with the seal to restore the true names.

```python
import beam

scores = beam.load_scores("scores.csv")
blinded, seal = beam.blind(scores, seed=7)
beam.write_seal(seal, "seal.json")        # store the secret separately

# choose weights, aggregation and metric set on the blinded labels, then:
result = beam.rank(blinded, weights="entropy", method="topsis")
final = beam.unblind(result, seal)        # restore the true names
print(final.top_tool)
```

The metric and dataset axes are left visible, since the analyst needs them to set polarity, weights and the cross-dataset rule. Only the method identities are hidden.

## Auditing

beam is controlled by users and not the way around. To add an extra layer of auditing, beam treats blinding as an auditable record. The `Seal` carries a fingerprint, a sha256 over the seed and the label mapping, and beam writes it into the run manifest when the run is on blinded scores:

```json
"blinding": {"blinded": true, "seal_sha256": "6ee805357098..."}
```

The seal file, kept separately, records that the configuration was fixed before the labels were revealed. A reviewer who has the manifest and the seal can confirm the analysis ran on scores blinded under that seal. This mechanisms suits preregistration well, but does not enforce it.

## Why the blinding does not affect results

Unblinding only renames the rows and does not re-rank methods.

## Usage

```
beam blind scores.csv --out blinded.csv --seal seal.json --seed 7
beam rank blinded.csv --weights entropy --method topsis --out result.json
beam unblind result.json --seal seal.json --out result.unblinded.json
```

## See also

- [Specification curve](specification-curve.md)
- [Rank sensitivity](rank-sensitivity.md)

## References

- MacCoun, R., Perlmutter, S. Blind analysis: hide results to seek the truth. Nature 526, 187-189 (2015). DOI [10.1038/526187a](https://doi.org/10.1038/526187a).
- Klein, J. R., Roodman, A. Blind analysis in nuclear and particle physics. Annual Review of Nuclear and Particle Science 55, 141-163 (2005). DOI [10.1146/annurev.nucl.55.090704.151521](https://doi.org/10.1146/annurev.nucl.55.090704.151521).
- Simmons, J. P., Nelson, L. D., Simonsohn, U. False-positive psychology. Psychological Science 22, 1359-1366 (2011). DOI [10.1177/0956797611417632](https://doi.org/10.1177/0956797611417632).
- Gelman, A., Loken, E. The garden of forking paths (2013). Working paper, Department of Statistics, Columbia University.
