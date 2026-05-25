# Changelog

All notable changes to beam will be documented in this file. The format follows Keep a Changelog (https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- `beam.rank`, the five-line procedural API. It accepts a `Scores`, a CSV path, or a 2D array with metric ids; resolves polarity, normalization, bounds and baselines from the metric cards once; runs the MCDA pipeline; runs the default sensitivity primitives (SMAA, leave-one-metric-out, smallest weight perturbation) on the same normalization context; builds the run manifest; and returns a frozen `RunResult` bundling the `Result`, the sensitivity reports, the ranked matrix, the context, and the manifest. A long tool by dataset by metric tensor is reduced across datasets nan-aware per each card's recommended rule before ranking. `beam.rank` and `beam.RunResult` are exported at the top level.
- `beam.load_scores` and the `Scores` container (`beam.io.scores`). Reads a benchmark CSV in two layouts using only the standard library and numpy: wide (tool column plus one column per metric id) and long (tool, dataset, metric, score). Validates metric ids against the registry, raising `UnknownMetricError` on an unknown id; surfaces missing cells as NaN without imputing. The pandas `read_csv` stays as the optional `[io]` convenience.
- `beam.report` (alias of `beam.reporting.write_report`), a self-contained HTML report rendered with jinja2 and matplotlib figures embedded as base64 PNGs (no external assets, no quarto at runtime). Sections: input summary, normalization diagnostics with guard warnings, ranking table with a bar chart and a normalized-score heatmap, sensitivity outputs, a critical-difference section when the input has more than one dataset, and a plain-language recommendation paragraph from `beam.reporting.narrative`. Every figure labels both axes. The narrative avoids winner or wins phrasing and bare best or worst value judgements, and ties every claim to the metric set and weighting.
- `beam.manifest`, the run manifest: beam version, input path and sha256, metric card ids with versions and content hashes, weighting and aggregation, the SMAA sample count and seed, the per-metric normalization, and a software fingerprint including pymcdm. `created_utc` and `host` are the only per-run-volatile keys (`volatile_keys`, `reproducible_view`); two identical runs produce the same manifest otherwise. `write_manifest` writes `manifest.json`.
- `beam.config`, the declarative `beam.yaml` runner. `run_config` loads the scores, optionally selects and reorders metrics, reads the weighting, aggregation and sensitivity settings, runs `beam.rank`, and writes the report, the manifest, and the normalized scores. `dataset_features` and `heterogeneity` are Phase 4 and ignored; per-metric version pins are parsed but not yet enforced.
- The `beam` command-line interface (`beam.cli`, entry point `beam = beam.cli:main`, argparse, no new dependency). Subcommands `beam validate`, `beam rank`, `beam report`, `beam metric show`, and `beam run`. Plain unix style: lowercase output, errors to stderr as `beam: error: ...`, exit code 0 on success and 2 on a usage or validation error. `beam rank` writes a run record; `beam report` reloads it and re-runs deterministically before rendering.
- `beam.mcda.registry_context` and `RegistryContext`: the card-derived polarity, normalization, bounds and baselines for a set of metric ids, factored out of `run_from_registry` and reused by the sensitivity primitives. `smaa`, `leave_one_metric_out` and `smallest_weight_perturbation` gained optional `normalization`, `bounds` and `baselines` parameters (default keeps prior behavior) so a sensitivity analysis rests on the same normalized matrix as the ranking it qualifies.
- Aggregation methods VIKOR, PROMETHEE II and COMET, alongside the existing SAW and TOPSIS. beam delegates the algorithm math to pymcdm, now a core runtime dependency, rather than carrying its own implementations. `beam.mcda.vikor` calls pymcdm VIKOR and returns the Opricovic-Tzeng compromise oriented higher is better (it returns -Q); `beam.mcda.promethee_ii` calls pymcdm PROMETHEE II with the usual preference function (Brans and Vincke 1985) and returns the net outranking flow; `beam.mcda.comet` calls pymcdm COMET (Salabun 2015) with the characteristic objects and an automated weighted-sum expert function beam supplies; `weighted_sum` (SAW) and `topsis` route through pymcdm with an identity normalization so pymcdm runs on beam's already-normalized matrix. beam keeps the shared contract (a normalized higher-is-better matrix and a weight vector in, a per-tool preference score out), the higher-is-better convention, and the degenerate-case handling. `run`, `run_from_registry`, `smaa` and `smallest_weight_perturbation` accept all five. Rankings are identical to the earlier native implementations on the Duo data across all 16 weighting-by-method configurations.
- Objective weighting schemes standard deviation, CRITIC (Diakoulaki 1995) and MEREC (Keshavarz-Ghorabaee 2021), and the subjective AHP scheme (`ahp_weights`, Saaty 1980) with principal-eigenvector weights and a consistency-ratio check (`InconsistentPairwiseMatrixError`). The objective schemes are selectable by name in the facade (`std`, `critic`, `merec`); MEREC takes logarithms and rejects a column carrying a hard zero, so it needs a normalization bounded away from zero. AHP takes a pairwise comparison matrix and is passed as an explicit weight array. These weight functions stay beam's own rather than delegating to pymcdm: pymcdm's weight functions sum-normalize internally and reject the zeros that beam's normalization produces (min-max maps the worst tool to 0), and pymcdm has no AHP. They match pymcdm to machine precision on strictly positive input.
- `beam.datasets.load_duo2018` and the `Duo2018` dataclass: the real Duo et al. 2018 single-cell clustering benchmark vendored into the package (14 methods by 12 datasets by 4 metrics, NaN in the missing cells), as distributed in the DuoClustering2018 Bioconductor package. The Duo vignette now runs on this data instead of a synthetic stand-in, with a regression test asserting beam reproduces the pymcdm ranking on the pooled matrix.
- Two seed metric cards, `shannon_entropy_diff` and `nclust_deviation`, mapping the remaining Duo 2018 metrics. The registry now ships nine cards.
- `examples/transportation/transportation.qmd`: a cross-domain vignette that runs per-terrain MCDA on transport modes, compares all five aggregations and the weighting schemes, draws a critical-difference diagram, and runs SMAA and weight perturbation. It makes the partial-coverage point concrete: no mode runs on every terrain, so a single pooled ranking is not well defined. `TransportationBenchmark` gains `feasible_submatrix` and `common_feasible_block` helpers.
- `smallest_weight_perturbation` now covers the non-linear aggregations (TOPSIS, VIKOR, PROMETHEE II, COMET) with a numeric single-weight search, keeping the closed form for SAW; the numeric path is validated against the closed form on SAW.
- Explanations `docs/explanations/aggregation-methods.md`, `docs/explanations/comet.md` and `docs/explanations/weighting-schemes.md`; ADR `docs/adr/0008-mcda-aggregation-set.md`; and findings entry `docs/findings/0001-duo-2018-mcda.md`.
- `pymcdm` is now a core runtime dependency. beam's aggregation functions wrap it (see above); beam keeps its own normalization, validation, weighting, sensitivity, critical-difference, and cross-dataset layers, which pymcdm does not provide.
- `beam.scenarios.transportation_benchmark` and `TransportationBenchmark`: a cross-domain MCDA example with illustrative data, transport modes (foot, running, bicycle, motorcycle, train, boat, small plane) scored across terrains (flat road, mud, uphill, open water, long distance, urban hop) on speed, cost, and CO2. No mode is fastest on every terrain, and some modes cannot run on some terrains at all (a boat off-road, a small plane on an urban hop), encoded as NaN. Because no mode runs on every terrain, a single pooled ranking is not well defined, which motivates per-terrain analysis and the heterogeneity work. The scenarios vignette gains a section with a coverage heatmap and a single-terrain MCDA on the long-distance leg.
- `beam.mcda.critical_difference` and `CriticalDifferenceReport`: Demsar (2006) Friedman test plus Nemenyi post-hoc on a tool by dataset matrix. Reports the average rank per tool (1 is best), the Friedman statistic and p-value, the Nemenyi critical difference, and the cliques of tools that are not significantly different. The critical-difference q term is computed from `scipy.stats.studentized_range` and matches Demsar Table 5 (2.728 for five methods at alpha 0.05). `nemenyi_critical_difference` is exposed separately. This is the committed Phase 1 statistical-comparison output; it answers whether the methods are separable across datasets, which the MCDA composite cannot.
- `docs/explanations/comparing-methods-across-datasets.md`: explanation of the Friedman-Nemenyi method, the critical difference, cliques, when it applies, and the Bonferroni-Dunn caveat.
- Scenarios vignette: new section running Friedman-Nemenyi on the odd-dataset per-dataset ARI, with a critical-difference plot. With five datasets the methods are not separable, the honest complement to the MCDA composite.
- `tests/test_mcda_cd.py`: validates the Nemenyi q against Demsar Table 5, the significant and non-significant cases, orientation handling, tie handling, and the shape guards.
- `beam.mcda.normalize`: per-column normalization dispatcher with five strategies (`min_max`, `log_min_max`, `rank`, `zscore`, `baseline_relative`). `log_min_max` keeps the multiplicative structure of ratio metrics so one outlier no longer compresses the rest (Smith 1988); `rank` is scale-free and outlier-proof; `zscore` is a logistic-squashed standardization; `baseline_relative` maps a chance-level score to 0 instead of the column midpoint. `min_max_normalize` is now a thin wrapper over `normalize`. The declared-range check applies to every strategy.
- `beam.mcda.normalization_warnings`: guard that flags min-max columns resting on an empirical bound (not comparable across method sets) or on a heavy-tailed distribution (one outlier dominates the rescale). Warnings travel on the `Result` and do not block the run.
- New schema field `comparability.recommended_normalization` (enum: `min_max`, `log_min_max`, `rank`, `zscore`, `baseline_relative`) and `semantics.score_of_random_baseline`. Populated on the seed cards: `log_min_max` for runtime and peak_memory, `baseline_relative` with a chance baseline of 0 for ARI, `min_max` (the default) for the bounded metrics.
- `beam.scenarios.normalization_failure_scenarios`: two example scenarios where the top-ranked method under unguarded all-min_max differs from the one under the card defaults. `outlier_runtime` (a runtime outlier hides the speed ladder; min-max ranks a slower method first, `log_min_max` ranks the fastest good one first). `chance_baseline` (min-max scores a chance-level ARI as 0.5 and ranks a random method above a better one; `baseline_relative` restores the order).
- `docs/explanations/normalization-and-scales.md`: explanation of where min-max fails, why the choice depends on the measurement scale (interval versus ratio, Stevens), the affine-flag decision for ratio metrics, the five strategies, and the guard.
- Tests: strategy unit tests and guard tests in `tests/test_mcda_normalize.py`; strategy-aware validation tests in `tests/test_mcda_validate.py`; scenario assertions in `tests/test_scenarios.py` pinning the top-rank flip, the collapsed runtime ladder, the chance-baseline value difference, and the empirical-bound instability.
- `beam.mcda.leave_one_metric_out` and `SensitivityReport`: per-metric leave-one-out sensitivity. Runs the pipeline with all metrics and once per metric omission; reports per-tool rank stability and the metric whose removal causes the largest rank change.
- `beam.mcda.smaa` and `SMAAReport`: SMAA-style weight-sampling sensitivity for SAW and TOPSIS. Draws Dirichlet weight vectors over the metrics simplex, runs the pipeline per sample, and reports the rank acceptability index, the per-tool central weight vector, and the confidence factor (Lahdelma and Salminen 2001).
- `beam.cards.MetricProperties` and `properties_for`: a small read-only view over polarity, scale_type, declared range bounds, allowed transformations, and the recommended cross-dataset aggregation pulled from a metric card.
- `beam.mcda.run_from_registry`: ontology-aware entry that pulls polarity and declared bounds from the registry, validates the requested aggregation against the declared scale type and allowed transformations, and feeds the result into `run`.
- `beam.mcda.validate_for_aggregation` and `IncompatibleScaleError`: rejects SAW or TOPSIS on nominal or ordinal columns, and refuses metrics whose `allowed_transformations` exclude `affine` or `min_max`.
- `min_max_normalize` now accepts an optional `bounds=` list. When provided, the declared bounds replace the empirical min/max in the rescaling, and observations outside the declared range raise.
- `beam.mcda.aggregate_across_datasets`: reduces a tool by dataset score matrix for one metric to a per-tool vector using the rule declared on the metric card (arithmetic_mean, geometric_mean, median, rank_mean).
- `beam.mcda.smallest_weight_perturbation` and `WeightPerturbationReport`: Triantaphyllou-Sanchez weight perturbation under SAW. Reports the smallest single-weight change that swaps each ordered pair of tools, the most fragile pair overall, and a fragility flag on the top rank.
- New schema field `comparability.recommended_aggregation_across_datasets` (enum: `arithmetic_mean`, `geometric_mean`, `median`, `rank_mean`). Populated on all seven seed cards: arithmetic mean for ARI, NMI, silhouette, accuracy, F1; geometric mean for runtime and peak memory (Smith 1988).
- `affine` added to the `allowed_transformations` of runtime and peak_memory so the min-max step the pipeline applies is honestly licit on those cards.
- PLAN.md Section 10b: candidate metric card extensions (noise_floor, score_of_random_baseline, recommended_normalization, target_value, maintainer, tested_against, ontology mappings), each with the analysis it would make possible.
- `ipykernel>=6.0` and `matplotlib>=3.8` declared as explicit `[docs]` dependencies so Quarto reliably finds a Python kernel and can render the heatmap.
- Duo vignette: new SMAA section, new weight-perturbation section, new across-datasets aggregation section; switched the main MCDA call to `run_from_registry`.
- `beam.scenarios`: four canonical simulated benchmark scenarios with documented ground truth (`random` with anti-correlated trade-offs, `dominant`, `ties`, `odd_dataset` where one method is best on most datasets but a different method is best on one odd dataset). Each generator returns a `Scenario` carrying scores, optional per-dataset tensor, metric ids, and a `ScenarioExpectation` documenting what the MCDA pipeline should report.
- `tests/test_scenarios.py`: ground-truth assertions tying every pipeline primitive (run_from_registry, leave_one_metric_out, smaa, smallest_weight_perturbation, aggregate_across_datasets) to one or more scenarios. 15 tests in total, including a multi-seed sweep that the random scenario passes statistically.
- `examples/scenarios/scenarios.qmd`: simulated scenarios vignette mirroring the Duo report layout across all four scenarios.
- CI Quarto job now renders the scenarios vignette in addition to the Duo vignette and uploads the result as a separate artefact.

### Changed

- The metric registry and the JSON Schema moved from the repo root into the package, at `src/beam/metrics/` and `src/beam/schema/`, alongside the existing `src/beam/data/`. `beam.cards` resolves them through `importlib.resources`, so an installed wheel finds the cards and `run_from_registry` works outside a source checkout. The card YAML, the schema, and the report template are declared as wheel artifacts. `tests/test_packaging.py` asserts resolution from package resources, and a clean-venv wheel install was verified to run `beam rank` and `run_from_registry`.
- `jinja2>=3.1` added as a core dependency for the HTML report. `matplotlib>=3.8` promoted from the `[docs]` extra to a core dependency so the report renders anywhere beam is installed.
- `beam.__version__` now reads from `importlib.metadata` rather than a hardcoded literal, so it cannot drift from the version in pyproject.
- `PLAN.md` removed from the sdist `include` list. It is the gitignored private working contract and must not reach PyPI.
- `scipy>=1.11` added to the core dependencies. The Demsar module needs the Friedman p-value and the exact Studentized range critical value for any number of methods, which a hand-rolled implementation or a small hardcoded table could not provide cleanly (Duo 2018 alone has 14 methods).
- `beam.mcda.__init__` now also exports `CriticalDifferenceReport`, `critical_difference`, and `nemenyi_critical_difference`.
- `tied_scenario` now sets the tied pair above the other methods, so the pair ties for the top rank. The SMAA confidence factor then lands on the pair (both near 1.0) instead of on an unrelated method, which fixes a confusing bar in the scenarios vignette.
- `beam.mcda.run` and `run_from_registry` now take a per-metric normalization strategy. `run_from_registry` reads `comparability.recommended_normalization` from each card (default `min_max`), pulls `score_of_random_baseline` for the `baseline_relative` strategy, and runs the empirical-bound and heavy-tail guard.
- `validate_for_aggregation` is now strategy-aware: it checks that the card permits the transform the chosen strategy applies (`log` for `log_min_max`, `rank` for `rank`, `affine`/`min_max` for `min_max` and `baseline_relative`, `z_score`/`affine` for `zscore`), replacing the earlier blanket `affine`/`min_max` check. A ratio metric normalized by `log_min_max` is validated against `log` rather than an `affine` grant.
- `Result` gained `normalization` (the per-column strategy used) and `warnings` (the guard output).
- `beam.mcda.__init__` now also exports `STRATEGIES`, `normalize`, and `normalization_warnings`.
- British spelling (`normalis-`, `standardis-`) replaced by the z spelling (`normaliz-`, `standardiz-`) across code, tests, docs, and cards, including the `Result.normalized` field.
- `docs/explanations/cards-and-pipeline.md` reclassifies `recommended_normalization` and `score_of_random_baseline` as consumed and documents the strategy-aware validation and the guard.
- `beam.cards.__init__` now exports `MetricProperties` and `properties_for`.
- `beam.mcda.__init__` now exports `IncompatibleScaleError`, `PairPerturbation`, `Result`, `SMAAReport`, `SensitivityReport`, `WeightPerturbationReport`, `aggregate_across_datasets`, `leave_one_metric_out`, `run_from_registry`, `smaa`, `smallest_weight_perturbation`, and `validate_for_aggregation`.
- `Result` dataclass gained `bounds` and `metric_ids` fields so the caller can inspect which declared range was used and which metric ids correspond to the score columns.
- `docs/explanations/cards-and-pipeline.md` reclassifies `scale_type`, `range`, `allowed_transformations`, and `recommended_aggregation_across_datasets` from "declared but not enforced" to "consumed", with an updated Mermaid diagram.
- CI Quarto setup pinned to 1.5.57; the vignette render step now sets `MPLBACKEND=Agg`.

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
