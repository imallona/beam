# Changelog

All notable changes to beam will be documented in this file. The format follows Keep a Changelog (https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

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
