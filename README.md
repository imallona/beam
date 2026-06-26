# beam

beam  is a benchmark evaluation and metrics suite. For benchmarks as in method comparisons, mainly in bioinformatics.

[Documentation](https://imallona.github.io/beam/): how-tos, vignettes, and explanations.

## Install

Python package:

```
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,docs]"
```

`[docs]` pulls in Jupyter and matplotlib so Quarto can execute the Python code chunks in the vignettes. `[io]` pulls in pandas for the CSV adapter. `[dev]` covers the test suite.

R package:

```
library("remotes")
remotes::install_github("imallona/beam", subdir = "r/beam")
rbeam::install_beam_python()
```

### Heterogeneity diagnostics (optional, needs R)

The MCDA ranking is pure Python. The heterogeneity diagnostics (Bradley-Terry trees, mixed-effects, Plackett-Luce, variance decomposition, network meta-analysis) call `Rscript` and need `lme4`, `glmmTMB`, `psychotree`, `partykit`, `PlackettLuce`, `qvcalc`, `meta`, `netmeta` and `jsonlite`. The conda recipe puts Python and R in one environment so the wrapper finds `Rscript`:

```bash
mamba env create -f envs/heterogeneity.yml
conda activate beam-heterogeneity
pip install -e ".[dev]"
```

From R, install them once with `rbeam::install_beam_heterogeneity_deps()`. The availability checks (`beam.heterogeneity.r_available()` and friends) report whether the toolchain is in place.

## Usage

From a CSV to an HTML report:

On a shell:

```bash
beam validate scores.csv
beam rank scores.csv --weights entropy --method topsis --out result.json --report report.html
beam report result.json --out report.html
beam metric show ari
beam heterogeneity scores.csv --model bradley-terry-tree --features features.csv --out tree.json
beam run beam.yaml
```

In python:

```python
import beam
from beam.cards import Registry
from beam.config import run_config

beam.load_scores("scores.csv")
result = beam.rank("scores.csv", weights="entropy", method="topsis")
beam.report(result, "report.html")
print(Registry().get("ari"))
run_config("beam.yaml")
```

In R

```r
library(rbeam)

result <- beam_rank("scores.csv", weights = "entropy", method = "topsis")
beam_validate("scores.csv")
beam_report(result, "report.html")
beam_metric_show("ari")
beam_run("beam.yaml")
```

## Build artefacts

- [Documentation site](https://imallona.github.io/beam/): vignettes, how-tos, explanations, and the Python API reference.
- Ontology release: `docs/beam.owl.ttl` (OWL) and `docs/beam.skos.ttl` (SKOS), regenerated from the cards on each release.

## Licence

- Code: GPL-3.0-or-later (`LICENSE`).
- Metric cards under `src/beam/metrics/`: CC-BY-4.0 (`src/beam/metrics/LICENSE.md`).

## Citation

Mallona, Izaskun (2026). beam: Benchmark Evaluation And Metrics. Version 0.2.0. https://github.com/imallona/beam. ORCID 0000-0002-2853-7526.

```bibtex
@software{mallona_beam_2026,
  author  = {Mallona, Izaskun},
  title   = {beam: Benchmark Evaluation And Metrics},
  version = {0.2.0},
  year    = {2026},
  url     = {https://github.com/imallona/beam},
  license = {GPL-3.0-or-later}
}
```

## Contact

Izaskun Mallona, izaskun.mallona.work@gmail.com.

## Inspiration

- [Commonly used software tools produce conflicting and overly-optimistic AUPRC values](https://genomebiology.biomedcentral.com/articles/10.1186/s13059-024-03266-y)
- [Performance Evaluation in Machine Learning: The Good, The Bad, The Ugly and The Way Forward](http://people.cs.bris.ac.uk/~flach/papers/Performance-AAAI19.pdf)
- [Measurement theory and paleobiology](https://www.sciencedirect.com/science/article/pii/S0169534723002161)

## Started

21st Feb 2025
