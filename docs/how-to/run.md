# Run

Each interface gives the same ranking from a wide scores CSV: the tool in the first column, one column per metric id, each id resolving to a [metric card](../explanations/cards-and-pipeline.qmd). `beam.rank` reads the scores, normalizes and combines them per the cards, and runs the default sensitivity checks; `beam.report` writes a self-contained HTML report with the figures embedded. `beam.plot` returns those figures individually as `matplotlib` objects to save or reuse in a notebook.

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

The CLI runs the same pipeline and writes a manifest for reproducibility.

```sh
beam rank scores.csv --weights entropy --method topsis --report report.html --manifest manifest.json
```

## Run from a beam.yaml

A beam.yaml describes a whole run in one file: the input scores, the metric selection, the [weighting](../explanations/weighting-schemes.md) and [aggregation](../explanations/aggregation-methods.md), the sensitivity settings, and the output paths. It is placed next to scores.csv; paths inside are resolved against the file's own directory.

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

metrics is optional. It picks and reorders the metric columns to use. Each entry names a metric id that must be a column in the scores file. Leave the block out to use every column. A listed metric that is not in the file stops the run with an error.

weighting.method sets how the metric weights are derived. It accepts equal (the default when the block is absent), entropy, std, critic or merec.

aggregation.method sets how the [normalized](../explanations/normalization-and-scales.md) scores combine into one score per tool. It accepts saw (the default when the block is absent), topsis, vikor, promethee_ii or comet.

The sensitivity block, when present, turns the sensitivity analysis on. The [smaa](../reference/smaa.qmd) entry sets the sample count n and the seed, which default to 1000 and 42 so two runs reproduce.

outputs is optional and each entry is optional. report writes the self-contained HTML report. manifest writes manifest.json, the run record. scores_normalized writes the normalized tool-by-metric matrix as a CSV.

### Card versions

Each metric entry may pin a [card](../explanations/cards-and-pipeline.qmd) version, so a rerun uses the card of the original ranking:

```yaml
metrics:
  - id: ari
    version: v1
  - id: runtime
```

The pinned card is the one used to rank and the one fingerprinted in the manifest. A metric without a version takes the latest. A pinned version that is not in the registry stops the run with an error naming the metric and the available versions.

## Reproduce a run

`beam rank --manifest manifest.json` records the run: input path and content hash, card ids and versions, weighting, aggregation, [SMAA](../reference/smaa.qmd) seed and sample count, normalization, and the versions of python, beam, numpy, scipy, pymcdm, pyyaml and jsonschema. It is kept with the scores. `beam rank --out result.json` writes the run record, and `beam report` reruns from it with the recorded parameters and seed:

```sh
beam rank scores.csv --out result.json --manifest manifest.json
beam report result.json --out report_rerun.html
```

Two runs on the same data and parameters give manifests differing only in `created_utc` and `host`; `beam.manifest.reproducible_view` strips those for an equality check. If the software versions or a card changed between runs the ranking can differ; the manifest records the versions to reinstall.
