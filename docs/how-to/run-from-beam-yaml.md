# Run a benchmark from a beam.yaml file

Use this recipe when you want a whole beam run captured in one file: the input scores, the metric selection, the weighting and aggregation, the sensitivity settings, and the output paths. The file plus the written manifest.json is the artifact a reviewer reruns to reproduce your ranking.

## Write the beam.yaml

Put this next to your scores.csv. Paths inside the file are resolved against the file's own directory.

```yaml
inputs:
  scores: scores.csv
metrics:
  - id: ari
  - id: nmi
  - id: runtime
weighting:
  method: entropy
aggregation:
  method: topsis
sensitivity:
  smaa: {n: 1000, seed: 42}
outputs:
  report: report.html
  manifest: manifest.json
  scores_normalized: scores_norm.csv
```

## Run it

```
beam run beam.yaml
```

On success it prints a one-line summary, for example:

```
ok: seurat ranks first of 3 tools
```

and writes the files named under outputs, relative to the beam.yaml directory.

## What each block does

inputs.scores is the only required field. It points at the score CSV (wide or long layout). If it is missing, the run stops with an error.

metrics is optional. It selects and reorders the metric columns to use. Each entry names a metric id that must be a column in the scores file. Leave the block out to use every column. A listed metric that is not in the file stops the run with a clear error.

weighting.method sets how the metric weights are derived. It accepts equal (the default when the block is absent), entropy, std, critic or merec.

aggregation.method sets how the normalized scores combine into one score per tool. It accepts saw (the default when the block is absent), topsis, vikor, promethee_ii or comet.

sensitivity turns the sensitivity analysis on or off by its presence. Include the block to run the analysis; omit it to skip it. The smaa entry sets the sample count n and the seed, which default to 1000 and 42 so two runs reproduce.

outputs is optional and each entry is optional. report writes the self-contained HTML report. manifest writes manifest.json, the run record. scores_normalized writes the normalized tool-by-metric matrix as a CSV.

## The reproducible artifact

Keep beam.yaml and the written manifest.json together with the scores file. manifest.json records the input and its hash, the metrics, the parameters and the normalization that beam resolved from the cards. A reviewer with the same scores file reruns the ranking with one command. The manifest lets them confirm they got the same inputs and parameters you did.

## Note on Phase 4 blocks

The dataset_features and heterogeneity blocks are Phase 4 and ignored for now. You can leave them out. Per-metric version pins are recorded but not yet enforced; the registry resolves the latest version of each card.
