# Aim

`beam` provides `b`enchmark `e`valuation `a`nd `m`etrics.

We store and manage open and reusable performance metrics so anyone running a method comparison (a benchmark) can automate decisions and reduce implicit bias.

Our [documentation](https://imallona.github.io/beam/) includes howtos, vignettes, and explanations.

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

R dependencies for the heterogeneity diagnostics:

The MCDA ranking is pure Python and needs no R. The heterogeneity diagnostics (`beam.heterogeneity.bradley_terry_tree`, `mixed_effects`, `plackett_luce`, `source_variance_decomposition`, `network_meta_analysis`, and the matching `beam heterogeneity` CLI) call `Rscript` and need `lme4`, `glmmTMB`, `psychotree`, `partykit`, `PlackettLuce`, `qvcalc`, `meta`, `netmeta` and `jsonlite` on the R library path.

From Python or the CLI, the supported route is the conda recipe [envs/heterogeneity.yml](https://github.com/imallona/beam/blob/main/envs/heterogeneity.yml), which puts Python and R in one environment so the wrapper finds `Rscript`. It pulls the R packages as conda-forge binaries, so it avoids compiling `PlackettLuce` and its solver dependencies (`CVXR`, `clarabel`) from source:

```bash
mamba env create -f envs/heterogeneity.yml
conda activate beam-heterogeneity
pip install -e ".[dev]"
```

`beam.heterogeneity.r_available()`, `.bttree_available()`, `.glmmtmb_available()` and `.plackett_luce_available()` report whether each toolchain is in place.

From R, install the packages once with the bundled helper (they are Suggests, so they are not installed with `rbeam` itself):

```r
rbeam::install_beam_heterogeneity_deps()
```

## Usage

We have a detailed [documentation](https://imallona.github.io/beam/). TL/DR from a CSV to an HTML report:

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

## Repository layout

```
src/beam/
  schema/                       metric_card.schema.json, JSON Schema (draft 2020-12), shipped as package data
  metrics/                      One YAML file per metric and version; LICENSE.md is CC-BY-4.0 (cards only)
  cards/                        Card loader, MetricCard, MetricProperties, Registry,
                                polarities_for, properties_for
  mcda/                         normalize, weights (equal, entropy, std, critic, merec, ahp),
                                topsis, weighted_sum, vikor, promethee_ii, comet, rank, run,
                                run_from_registry, registry_context, validate_for_aggregation,
                                leave_one_metric_out, leave_one_dataset_out, smaa,
                                smallest_weight_perturbation, aggregation_agreement,
                                beats_random_baseline, noise_floor_separation,
                                critical_difference, skillings_mack,
                                coverage_aware_critical_difference,
                                aggregate_across_datasets, reduce_tensor, Result
  api.py                        load-rank-report procedural API: rank, RunResult
  reporting/                    Self-contained HTML report (write_report, exposed as beam.report)
  manifest.py                   Run manifest: hashes, card versions, software fingerprint
  config.py                     Declarative beam.yaml runner (run_config)
  cli.py                        beam command-line interface (entry point beam = beam.cli:main)
  io/                           load_scores (stdlib CSV) and the optional pandas read_csv
  scenarios.py                  Canonical simulated scenarios and the transportation benchmark
  datasets.py                   load_duo2018, load_m4, load_openproblems and their features loaders
  heterogeneity/                mixed_effects (lme4, glmmTMB beta engine), bradley_terry_tree
                                (psychotree), plackett_luce (PlackettLuce), paired_comparisons,
                                rankings_from_matrix, the availability probes, and the .R scripts
  data/                         DuoSCClustering2018.csv (Duo et al. 2018), its features CSV, and provenance
  owl/                          generate.py: regenerates docs/beam.owl.ttl from the cards and the schema
r/beam/                         rbeam R package: reticulate shim for the MCDA wrappers (beam_rank, beam_report, ...), native R for the heterogeneity diagnostics
scripts/                        one-shot helpers: ols_query.py and ols_verify.py used during the ontology lift
tests/
  test_schema.py                Python-side metric card validation
  validate_cards.R              R-side metric card validation (jsonvalidate)
  test_cards_*.py               Cards loader, registry, polarities_for, properties_for
  test_mcda_*.py                Normalize, weights, aggregate, topsis, facade, pipeline,
                                validate, run_from_registry, sensitivity, smaa, perturbation,
                                cross_dataset
  test_scenarios.py             Ground-truth checks on the four canonical scenarios
examples/
  duo2018/duo2018.qmd           Walkthrough vignette on the real Duo 2018 data
  scenarios/scenarios.qmd       Consistency-check vignette across canonical scenarios
  transportation/transportation.qmd  Cross-domain example across all methods
  m4/m4.qmd                     M4 forecasting competition, a large real non-bio benchmark
  openproblems/openproblems.qmd  MCDA and Bradley-Terry tree on two OpenProblems tasks
  cross_benchmark/cross_benchmark.qmd  Meta-analysis of four integration benchmarks
docs/
  adr/                          Architectural decision records
  explanations/                 Conceptual essays (measurement theory, cards-and-pipeline)
  tutorials/                    Learning-oriented walkthroughs
  how-to/                       Task-oriented recipes
  beam.owl.ttl                  OWL release artefact, regenerated by python -m beam.owl.generate
.github/workflows/
  ci.yml                        Python tests, R card validation, vignette rendering
  r-ci.yml                      R CMD check on the R wrapper, linux/macos/windows
  docs.yml                      Quarto docs site rendered and deployed to GitHub Pages
```

## Build artefacts

- Rendered vignettes: CI renders and uploads each `examples/` vignette as a self-contained HTML workflow artefact on every push and pull request, downloadable from the Actions tab on GitHub. The artefacts are `duo2018-vignette`, `scenarios-vignette`, `transportation-vignette`, `m4-vignette`, `openproblems-vignette` and `cross_benchmark-vignette`.
- Documentation site: `.github/workflows/docs.yml` builds the Quarto site from `_quarto.yml` and deploys it to GitHub Pages on every push to main. The site indexes the tutorials, how-tos and explanations, and includes a quartodoc-generated Python API reference.
- `metric_card.schema.json`: the canonical schema. Any tool that validates JSON against it can ingest beam metric cards.
- `docs/beam.owl.ttl`: OWL artefact in Turtle, one instance per metric card under its STATO, UO or OBI parent where a mapping is declared. Regenerated from the cards and the schema by `python -m beam.owl.generate`; ships with each release.
- `docs/beam.skos.ttl`: SKOS concept schemes over the card controlled vocabulary (polarity, scale type, allowed transformations, recommended normalization), one concept per allowed value with definitions and a scale hierarchy. Regenerated by `python -m beam.owl.skos`; ships with each release.
- `CITATION.cff`: cff-version 1.2.0; GitHub renders a citation widget from it.
- Python wheel under `dist/` after `python -m build`. Not yet on PyPI.
- R source tarball after `R CMD build r/beam`. Built and tested on linux, macos and windows in `.github/workflows/r-ci.yml`. Not yet on CRAN.

## Licence

- Code: GPL-3.0-or-later (`LICENSE`).
- Metric cards under `src/beam/metrics/`: CC-BY-4.0 (`src/beam/metrics/LICENSE.md`).

## Citation

See `CITATION.cff`.

## Inspiration

- [Commonly used software tools produce conflicting and overly-optimistic AUPRC values](https://genomebiology.biomedcentral.com/articles/10.1186/s13059-024-03266-y)
- [Performance Evaluation in Machine Learning: The Good, The Bad, The Ugly and The Way Forward](http://people.cs.bris.ac.uk/~flach/papers/Performance-AAAI19.pdf)
- [Measurement theory and paleobiology](https://www.sciencedirect.com/science/article/pii/S0169534723002161)

## Started

21st Feb 2025
