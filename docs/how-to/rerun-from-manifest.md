# Rerun a beam analysis from a manifest

Every `beam.rank` run writes a manifest: a JSON record of the input file path and content hash, the metric card ids and versions, the weighting scheme, the aggregation method, the SMAA seed and sample count, the per-metric normalization, the software fingerprint (python, numpy, scipy, pymcdm, pyyaml, jsonschema versions), and the host fingerprint. The manifest is what travels with a publication: a reader can run beam against it and reproduce the analysis byte for byte where possible.

This recipe walks through rerunning a recorded analysis.

## 1. The run that produced the manifest

A typical run from the CLI writes the manifest next to the report:

```
beam rank scores.csv \
    --weights entropy \
    --method topsis \
    --report report.html \
    --manifest manifest.json
```

`manifest.json` is the file you keep alongside the score CSV and the report. From Python, the manifest is on the result object:

```python
import beam
result = beam.rank("scores.csv", weights="entropy", method="topsis")
result.manifest      # the dict
```

## 2. Inspect what was recorded

```
python -c "import json; print(json.dumps(json.load(open('manifest.json')), indent=2))" | head -40
```

You will see the input hash, the metric cards with their version and content hash, the parameters, and the software versions.

## 3. Rerun

The CLI's `beam report` reloads a run record and re-runs the analysis with the recorded parameters and seed, then renders a fresh report:

```
beam report result.json --out report_rerun.html
```

(Note: `result.json` is the small run record written by `--out` on the original `beam rank`; the manifest is the full reproducibility record, the run record is the smaller pointer.)

From Python you can also reuse the parameters in the manifest directly:

```python
import json
import beam

m = json.load(open("manifest.json"))
result = beam.rank(
    m["input"]["path"],
    weights=m["parameters"]["weighting"]["method"],
    method=m["parameters"]["aggregation"]["method"],
    seed=m["parameters"]["sensitivity"]["smaa"]["seed"],
)
```

The score CSV must be at the path the manifest records (or you pass an identical CSV; the content hash is what guarantees identity).

## 4. Confirm the rerun matches

Two manifests for two runs of the same data with the same parameters and seed should differ only in two fields: `created_utc` and `host`. The `reproducible_view` helper strips those:

```python
from beam.manifest import reproducible_view
assert reproducible_view(m1) == reproducible_view(m2)
```

That is the byte-level reproducibility check, and the test suite asserts it under `tests/test_api_rank.py`.

## 5. When reproducibility breaks

If the software versions changed (numpy, scipy, pymcdm) the rerun may give a different ranking. The manifest records the original versions; if you need to match them, install the package set the manifest records and rerun in that environment.

If a metric card changed between runs (a new version), the rerun uses the new card by default. To pin the older card, install the older beam release that shipped it.
