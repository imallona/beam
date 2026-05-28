# Aim

`beam` provides `b`enchmark `e`valuation `a`nd `m`etrics.

We store open and reusable performance metrics so anyone running a method comparison (a benchmark) can pick them up. We also aim to automate decisions and reduce implicit bias.

The design borrows from measurement theory.

`beam` is under development.

## Background

A metric procedure (not the result of running it), such as *accuracy*, *kBet* or *max RSS*, takes inputs of a similar shape and returns outputs of a similar shape. It can be written in more than one implementation.

- Implementations:` [{name : blabla, version: v1, language: python, license: MIT}; {name: fastbla, version: v2.2.2, language: Rust, license: GPL}]`
- Syntax
  - Dimension: vector, matrix, scalar, graph, complex (if complex, specify schema) etc
     - Schema: json schema for shape validation
  - Values: str, int, float32, bool, etc
  - File format: matrix market, csv, json, etc
- Semantics
  - Interpretation: low is good, A better than B better than C, etc; linear or not linear
  - Range: ratio, natural plus zero, (0 - 11.5), etc
  - Scale: nominal, ordinal, interval, ratio
    - Allowed transformations: e.g `poor = 0, mid = 1`; or `sqrt(x)`, `arcsin(x)` etc
  - Timeseries: no (whether repeated measures are taken at perhaps regular intervals)
- Documentation
  - Description (human readable)
- QA/QC
  - Example inputs for CI/CD / validity testing and their expected outputs
- Taxonomy
  - Intrinsic or depending on a truth; if dependending on a truth, specify the truth
  - Truth
    - Syntax (borrow specs from above)
    - Documentation
- Known applications: `[clustering, classification]`
- Example applications: `Anthony's clustering benchmark v1 with permalink X`, `spacehack v99.9 with permalink Y`

Measurement scales constrain which comparisons make sense. Distances on nominal data, or variance on ordinal labels, do not. Cross-tabulating nominal data, or log-transforming ratios, does.

## Metric repository and formalization

We provide tested software implementations for common metrics (TPR and others), annotated with _metric nutrition labels_, similar to [dataset nutrition labels](https://datanutrition.org/). The syntax and semantics fix the input and output interfaces, so the same card is reusable across languages and interpreters.

## Why?

This project is inspired by [omnibenchmark](https://github.com/omnibenchmark/omnibenchmark), a tool for open and continuous community benchmarking.

# Resources

- [Commonly used software tools produce conflicting and overly-optimistic AUPRC values](https://genomebiology.biomedcentral.com/articles/10.1186/s13059-024-03266-y)
- [Performance Evaluation in Machine Learning: The Good, The Bad, The Ugly and The Way Forward](http://people.cs.bris.ac.uk/~flach/papers/Performance-AAAI19.pdf)
- [Measurement theory and paleobiology](https://www.sciencedirect.com/science/article/pii/S0169534723002161)

# Started

21st Feb 2025

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
beam::install_beam_python()
```

## Usage

The five-line path, from a CSV to an HTML report:

```python
import beam

scores = beam.load_scores("scores.csv")          # tool by metric, or a tool by dataset by metric tensor
result = beam.rank(scores, weights="entropy", method="topsis")
beam.report(result, "report.html")
print(result.top_tool, "ranks first")
```

`beam.rank` reads polarity, normalization, bounds and baselines from the metric cards, runs the MCDA pipeline, runs the default sensitivity analysis on the same normalization context, and builds a run manifest. The returned `RunResult` carries the ranking, the sensitivity reports, and the manifest. `beam.report` writes one self-contained HTML file with the ranking, the sensitivity, a critical-difference section when the input has more than one dataset, and a plain-language recommendation.

The same from the command line:

```
beam validate scores.csv
beam rank scores.csv --weights entropy --method topsis --out result.json --report report.html
beam report result.json --out report.html
beam metric show ari
beam run beam.yaml
```

The lower-level entry point `beam.mcda.run_from_registry(scores, metric_ids, weights=, method=)` takes a 2D array directly and returns just the MCDA `Result`. See `examples/duo2018/duo2018.qmd` for the longer walkthrough and `docs/tutorials/quickstart.md` for a runnable quickstart.

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
                                smallest_weight_perturbation, critical_difference,
                                skillings_mack, coverage_aware_critical_difference,
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
r/beam/                         R wrapper for CRAN (thin reticulate shim around beam.rank, beam.report, etc.)
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
  findings/                     Empirical findings log
  explanations/                 Conceptual essays (measurement theory, cards-and-pipeline)
  tutorials/                    Learning-oriented walkthroughs
  how-to/                       Task-oriented recipes
  beam.owl.ttl                  OWL release artefact, regenerated by python -m beam.owl.generate
  paper/                        Manuscript folder
.github/workflows/
  ci.yml                        Python tests, R card validation, vignette rendering
  r-ci.yml                      R CMD check on the R wrapper, linux/macos/windows
  docs.yml                      Quarto docs site rendered and deployed to GitHub Pages
```

## Build artefacts

- Rendered vignettes: CI renders and uploads each `examples/` vignette as a self-contained HTML workflow artefact on every push and pull request, downloadable from the Actions tab on GitHub. The artefacts are `duo2018-vignette`, `scenarios-vignette`, `transportation-vignette`, `m4-vignette`, `openproblems-vignette` and `cross_benchmark-vignette`.
- Documentation site: `.github/workflows/docs.yml` builds the Quarto site from `_quarto.yml` and deploys it to GitHub Pages on every push to main. The site indexes the tutorials, how-tos, explanations, ADRs and findings, and includes a quartodoc-generated Python API reference.
- `metric_card.schema.json`: the canonical schema. Any tool that validates JSON against it can ingest beam metric cards.
- `docs/beam.owl.ttl`: OWL artefact in Turtle, one instance per metric card under its STATO, UO or OBI parent where a mapping is declared. Regenerated from the cards and the schema by `python -m beam.owl.generate`; ships with each release.
- `CITATION.cff`: cff-version 1.2.0; GitHub renders a citation widget from it.
- Python wheel under `dist/` after `python -m build`. Not yet on PyPI.
- R source tarball after `R CMD build r/beam`. Built and tested on linux, macos and windows in `.github/workflows/r-ci.yml`. Not yet on CRAN.

## Licence

- Code: GPL-3.0-or-later (`LICENSE`).
- Metric cards under `src/beam/metrics/`: CC-BY-4.0 (`src/beam/metrics/LICENSE.md`).

## Citation

See `CITATION.cff`.
