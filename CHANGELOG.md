# Changelog

All notable changes to beam will be documented in this file. The format follows Keep a Changelog (https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Decision module with five MCDA aggregations (SAW, TOPSIS, VIKOR, PROMETHEE II, COMET, wrapping pymcdm) and six weighting schemes (equal, entropy, standard deviation, CRITIC, MEREC, AHP).
- Six card-driven normalization strategies (min_max, log_min_max, rank, zscore, baseline_relative, target_relative) with empirical-bound and heavy-tail guards.
- `target_relative` normalization and the `target_value` polarity for metrics whose ideal is a fixed value, not the highest or lowest score. The strategy scales each method by its closeness to the declared `semantics.target` (deviation-then-min-max), so the method nearest the target maps to 1. The pipeline enforces the pairing both ways: a `target_value` column must use `target_relative`, and `target_relative` refuses a monotone polarity. `target` is threaded from the card through `registry_context`, `run`, `run_from_registry` and the sensitivity primitives. New seed card `calibration_slope` (target 1) demonstrates the path.
- Sensitivity and comparison primitives: leave_one_metric_out, leave_one_dataset_out, SMAA, smallest_weight_perturbation, and the Demsar Friedman-Nemenyi critical-difference diagram.
- User-facing layer: beam.load_scores and Scores, the beam.rank procedural API and RunResult, a self-contained HTML beam.report, a reproducibility manifest, the declarative beam.yaml runner, and the beam command-line interface.
- Heterogeneity module beam.heterogeneity (R via one-shot subprocess): mixed-effects variance decomposition (lme4) with a glmmTMB beta engine for bounded metrics, Bradley-Terry trees (psychotree), and Plackett-Luce on full rankings (PlackettLuce).
- `beam.heterogeneity.source_variance_decomposition` and `SourceVarianceReport`: a cross-benchmark variance decomposition that fits `score ~ method + (1 | benchmark) + (1 | benchmark:dataset) + (1 | method:benchmark)` in lme4 and reports the method-by-benchmark variance share, the part of the spread that is a method ranking differently depending on which benchmark evaluates it (disagreement from benchmarker choices) rather than genuine heterogeneity. Datasets are nested in benchmark, so benchmarks need not share datasets. Validated on synthetic two-benchmark data.
- `SourceVarianceReport.lrt_statistic` and `lrt_pvalue`: a significance test for each variance partition (benchmark, benchmark:dataset, method:benchmark). 
- `beam.reporting.funky_heatmap` and `funky_heatmap_from_run`: the glyph-table benchmarking plot (methods by metrics, circle size for score, colour for metric group, overall bar) with an added panel that shows each method's rank span across the leave-one-dataset-out runs, so the figure carries its own rank robustness instead of reading as a settled order.
- Registry grew from seven to twenty-seven metric cards across clustering, efficiency, forecasting, transportation, the scIB single-cell integration and spatial metrics, and a clinical-prediction calibration metric.
- Bundled datasets load_duo2018, load_m4, and load_openproblems (batch_integration and spatially_variable_genes), each a small derived table with provenance in src/beam/data/README.md.
- Cross-benchmark harmonisation: load_integration_benchmarks and load_integration_published_ranks align three single-cell integration benchmarks (scIB, OpenProblems, Tran et al. 2020) on the shared scIB metric family (ARI, ASW, kBET, LISI) for five common methods, the input to source_variance_decomposition and the cross-benchmark meta-analysis (finding 0005). Derived tables scib2022_metrics.csv, tran2020_metrics.csv and integration_published_ranks.csv vendored with provenance.
- Six worked vignettes (Duo 2018, simulated scenarios, transportation, M4, OpenProblems, cross-benchmark meta-analysis), all rendered in CI.
- Missing-data policy for the MCDA pipeline. The ranking entry points (beam.rank, mcda.run, run_from_registry, the CLI beam rank --on-missing, and the beam.yaml missing key) take an explicit missing= policy, default "error". "error" refuses any missing cell with a named IncompleteMatrixError; "available" is available-case ranking with SAW only (each tool scored on its observed metrics, weights renormalized over its support); "worst" treats a non-run as the worst score (missing normalized cells set to 0, the matrix completes, every method runs); "impute" is a discouraged mean-imputation opt-in. Every non-error policy warns. beam never imputes by default or silently. Normalization is now NaN-transparent. reduce_tensor gained on_zero_coverage="nan" so a tool never run on a metric flows into the policy. ADR 0013, docs/explanations/missing-data.md.
- Documentation: ADRs 0008 to 0013, findings 0001 to 0005, and explanation essays on MCDA, normalization, the heterogeneity diagnostics, the funky-heatmap robustness plot, and missing data.

### Changed

- pymcdm, scipy, jinja2, and matplotlib became core runtime dependencies; the metric registry and JSON Schema moved into the package under src/beam/.
- TOPSIS, VIKOR, COMET, PROMETHEE II, the objective weight schemes (entropy, standard deviation, CRITIC, MEREC) and the Friedman-Nemenyi critical-difference test now refuse a tool by metric matrix with missing cells instead of silently propagating or masking NaN. The previous TOPSIS/VIKOR/COMET behavior masked a missing-derived NaN to 0.5, which fabricated a mid-range score; that mask is gone (0.5 stays only as a tie convention for genuinely complete but degenerate inputs).

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

- `src/beam/mcda/` module, the MCDA starter. `min_max_normalize` respects per-metric polarity. `equal_weights` builds a uniform weight vector. `weighted_sum` is the simple additive weighting (SAW) aggregation. `rank` returns competition ranks, 1 is best.
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
