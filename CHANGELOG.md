# Changelog

All notable changes to beam will be documented in this file. The format follows Keep a Changelog (https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Decision module with five MCDA aggregations (SAW, TOPSIS, VIKOR, PROMETHEE II, COMET, wrapping pymcdm) and six weighting schemes (equal, entropy, standard deviation, CRITIC, MEREC, AHP).
- Five card-driven normalization strategies (min_max, log_min_max, rank, zscore, baseline_relative) with empirical-bound and heavy-tail guards.
- Sensitivity and comparison primitives: leave_one_metric_out, leave_one_dataset_out, SMAA, smallest_weight_perturbation, and the Demsar Friedman-Nemenyi critical-difference diagram.
- User-facing layer: beam.load_scores and Scores, the beam.rank procedural API and RunResult, a self-contained HTML beam.report, a reproducibility manifest, the declarative beam.yaml runner, and the beam command-line interface.
- Heterogeneity module beam.heterogeneity (R via one-shot subprocess): mixed-effects variance decomposition (lme4) with a glmmTMB beta engine for bounded metrics, Bradley-Terry trees (psychotree), and Plackett-Luce on full rankings (PlackettLuce).
- Registry grew from seven to twenty-six metric cards across clustering, efficiency, forecasting, transportation, and the scIB single-cell integration and spatial metrics.
- Bundled datasets load_duo2018, load_m4, and load_openproblems (batch_integration and spatially_variable_genes), each a small derived table with provenance in src/beam/data/README.md.
- Five worked vignettes (Duo 2018, simulated scenarios, transportation, M4, OpenProblems), all rendered in CI.
- Documentation: ADRs 0008 to 0011, findings 0001 to 0004, and explanation essays on MCDA, normalization, and the heterogeneity diagnostics.

### Changed

- pymcdm, scipy, jinja2, and matplotlib became core runtime dependencies; the metric registry and JSON Schema moved into the package under src/beam/.

## [0.1.3] - 2026-05-20

### Added

- `beam.mcda.run`: single-call facade for the full pipeline (normalize, weight, aggregate, rank). Returns a `Result` dataclass with every intermediate output. Accepts `weights="equal"`, `weights="entropy"`, or an explicit array; `method="saw"` or `method="topsis"`.
- `beam.mcda.topsis`: distance-to-ideal aggregation on the [0, 1] normalized matrix. Returns relative closeness in [0, 1]. Single-tool and all-identical inputs return 0.5.
- `beam.mcda.entropy_weights`: Shannon entropy weighting on a normalized matrix. Higher-variation metrics get higher weight; uniform columns contribute zero. Invariant under positive per-column scaling. Falls back to equal weights if every column is uniform.
- `beam.cards.polarities_for`: small helper that looks up the polarity string per metric id from the registry, intended to be passed straight to `run`. Bridges the registry and the MCDA pipeline so polarity is not hand-typed.
- `docs/explanations/cards-and-pipeline.md`: short explainer with a Mermaid diagram showing which metric card fields the MCDA pipeline currently consumes and which it does not.
- Duo vignette extended with a 2x2 weighting x method comparison.
- CI job that renders the Duo vignette with Quarto and uploads the HTML as a downloadable workflow artefact.
- `docs` extra in `pyproject.toml` (`pip install -e .[docs]`) bundling `jupyter` for Quarto Python execution.

### Changed

- `beam.mcda.__init__` now exports `Result`, `run`, `topsis`, `entropy_weights`.
- `beam.cards.__init__` now exports `polarities_for`.
- `beam.mcda.run` docstring records which metric card fields the pipeline actually consumes (only `polarity`, in the normalization step) and which it does not (`scale_type`, `range`, `allowed_transformations`).
- Version bumped from 0.1.2 to 0.1.3.

## [0.1.2] - 2025-05-24

### Added

- `src/beam/mcda/` module, Phase 2 starter. `min_max_normalize` respects per-metric polarity. `equal_weights` builds a uniform weight vector. `weighted_sum` is the simple additive weighting (SAW) aggregation. `rank` returns competition ranks, 1 is best.
- `examples/duo2018/duo2018.qmd`, walkthrough vignette. Pulls polarity from the metric cards and runs the MCDA pipeline on a synthetic three-method, two-metric stand-in. Lists what is still needed to run on the real Duo 2018 data.

### Changed

- Version bumped from 0.1.1 to 0.1.2.
- `numpy` added to runtime dependencies.

## [0.1.1] - 2025-03-22

### Added

- `src/beam/cards/` module: registry, loader, dataclass model. Loads metric cards by id, validates against the schema, exposes semantics through typed accessors.
- Five more seed metric cards: `nmi`, `peak_memory`, `accuracy`, `f1_score`, `silhouette`. The registry now covers seven metrics across clustering, classification, and efficiency.
- `src/beam/io/` stub with a CSV reader for tool by metric matrices. pandas is an optional dependency under the `io` extra.
- `examples/duo2018/` folder placeholder for the Duo 2018 clustering vignette.
- `docs/explanations/measurement-theory.md`, short essay on Stevens scales and why every card declares scale_type and polarity.
- `.gitkeep` files in `docs/tutorials/`, `docs/how-to/`, `docs/reference/` so the empty Diataxis folders are visible in the tree.
- `CITATION.cff` (cff-version 1.2.0).
- `.pre-commit-config.yaml` with ruff, trailing whitespace, end-of-file fixer, YAML and JSON syntax checks.
- `Makefile` with install, test, lint, fmt, docs, clean targets.

### Changed

- Version bumped from 0.1.0 to 0.1.1.

## [0.1.0] - 2025-02-22

### Added

- `schema/metric_card.schema.json`, JSON Schema (draft 2020-12) for the metric card format.
- Seed metric cards `metrics/ari/v1.yaml` and `metrics/runtime/v1.yaml`.
- `tests/test_schema.py` (Python validation) and `tests/validate_cards.R` (R validation).
- GitHub Actions workflow covering ruff lint, ruff format check, pytest on Python 3.12 and 3.13, R-side validation.
- `pyproject.toml` declaring the Python package.
- `CONTRIBUTING.md`, `metrics/LICENSE.md` (CC-BY-4.0).
