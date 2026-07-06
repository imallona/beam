# Run a blind analysis

Hide the method names while you fix the analysis pipeline, then restore them. This is the blind analysis practice from particle physics and clinical trials: choose the weighting, the aggregation and the metric set without knowing which method is which, so the choices cannot be tuned toward a preferred result. See the explanation in [docs/explanations/analysis-blinding.md](../explanations/analysis-blinding.md) for the reasoning and the references.

## From Python

```python
import beam

scores = beam.load_scores("scores.csv")

# 1. Hide the method names and shuffle the rows under a seed.
blinded, seal = beam.blind(scores, seed=7)

# 2. Store the seal separately. It is the secret that unblinds.
beam.write_seal(seal, "seal.json")

# 3. Fix the whole pipeline on the blinded labels. You cannot see which
#    method is which, so the choices below do not chase a known winner.
result = beam.rank(blinded, weights="entropy", method="topsis")

# 4. Restore the true names once the pipeline is fixed.
final = beam.unblind(result, seal)
print(final.top_tool)
```

The run [manifest](rerun-from-manifest.md) on a blinded run records the seal fingerprint:

```python
result.manifest["blinding"]   # {"blinded": True, "seal_sha256": "..."}
```

A reviewer who has the manifest and the seal can confirm the analysis ran on scores blinded under that exact seal.

## From the command line

```
beam blind scores.csv --out blinded.csv --seal seal.json --seed 7
beam rank blinded.csv --weights entropy --method topsis --out result.json
beam unblind result.json --seal seal.json --out result.unblinded.json
```

`beam blind` writes the blinded score CSV and the seal JSON. `beam rank` runs on the blinded CSV. `beam unblind` translates the method labels in the run record back to the true names.

## From R

```r
library(rbeam)

scores <- reticulate::import("beam")$load_scores("scores.csv")
blinded <- beam_blind(scores, seed = 7)
beam_write_seal(blinded$seal, "seal.json")

result <- beam_rank(blinded$scores, weights = "entropy", method = "topsis")
final <- beam_unblind(result, blinded$seal)
print(final$top_tool)
```

## What blinding does and does not do

The ranking is the same whether or not the labels were hidden, because beam ranks on the score values and unblinding only renames the rows. Blinding does not change the result. It fixes the pipeline before the result is known, and it leaves a record (the seal fingerprint in the manifest) that the configuration predates the unblinding. It cannot stop someone from reading the source file; it supports a pre-registration claim rather than enforcing one.
