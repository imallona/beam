# Run

The same ranking in each interface, from a wide scores CSV: the tool in the first column, one column per metric id, each id resolving to a [metric card](../explanations/cards-and-pipeline.qmd). `beam.rank` reads the scores, normalizes and combines them per the cards, and runs the default sensitivity checks; `beam.report` writes a self-contained HTML report with the figures embedded. `beam.plot` returns those figures individually as `matplotlib` objects to save or reuse in a notebook.

## Python

```python
import beam
result = beam.rank("scores.csv", weights="entropy", method="topsis")
beam.report(result, "report.html")
print(result.top_tool)
```

## R

The R wrappers forward to the same Python pipeline through reticulate.

```r
library(rbeam)
result <- beam_rank("scores.csv", weights = "entropy", method = "topsis")
beam_report(result, "report.html")
print(result$top_tool)
```

## CLI

The CLI runs the same and writes a manifest for reproducibility.

```sh
beam rank scores.csv --weights entropy --method topsis --report report.html --manifest manifest.json
```

## Run from a beam.yaml

A beam.yaml captures a whole run in one file: the input scores, the metric selection, the [weighting](../explanations/weighting-schemes.md) and [aggregation](../explanations/aggregation-methods.md), the sensitivity settings, and the output paths. It sits next to scores.csv; paths inside are resolved against the file's own directory.

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

Run it:

```
beam run beam.yaml
```

On success it prints a one-line summary, for example `ok: seurat ranks first of 3 tools`, and writes the files named under outputs, relative to the beam.yaml directory.

### The beam.yaml blocks

inputs.scores is the only required field. It points at the score CSV (wide or long layout). If it is missing, the run stops with an error.

metrics is optional. It picks and reorders the metric columns to use. Each entry names a metric id that must be a column in the scores file. Leave the block out to use every column. A listed metric that is not in the file stops the run with a clear error.

weighting.method sets how the metric weights are derived. It accepts equal (the default when the block is absent), entropy, std, critic or merec.

aggregation.method sets how the [normalized](../explanations/normalization-and-scales.md) scores combine into one score per tool. It accepts saw (the default when the block is absent), topsis, vikor, promethee_ii or comet.

sensitivity turns the sensitivity analysis on or off by its presence. Include the block to run the analysis; omit it to skip it. The [smaa](../reference/smaa.qmd) entry sets the sample count n and the seed, which default to 1000 and 42 so two runs reproduce.

outputs is optional and each entry is optional. report writes the self-contained HTML report. manifest writes manifest.json, the run record. scores_normalized writes the normalized tool-by-metric matrix as a CSV.

### Card versions

Each metric entry may pin a [card](../explanations/cards-and-pipeline.qmd) version, so a rerun uses the exact card the ranking was built on:

```yaml
metrics:
  - id: ari
    version: v1
  - id: runtime
```

The pinned card is the one used to rank and the one fingerprinted in the manifest. A metric without a version takes the latest. A pinned version the registry does not carry stops the run with a clear error naming the metric and the versions that are available.

## Reproduce a run

`beam rank --manifest manifest.json` records the run: input path and content hash, card ids and versions, weighting, aggregation, [SMAA](../reference/smaa.qmd) seed and sample count, normalization, and the python/numpy/scipy/pymcdm fingerprint. It is kept with the scores. `beam report` reruns from the run record with the recorded parameters and seed:

```sh
beam report result.json --out report_rerun.html
```

To confirm, two runs of the same data and parameters give manifests that differ only in `created_utc` and `host`, and `beam.manifest.reproducible_view` strips those for an equality check. If the software versions or a card changed between runs the ranking can differ; the manifest records the versions to reinstall.
