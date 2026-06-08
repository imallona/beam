# Changelog

All notable changes to beam will be documented in this file. The format follows Keep a Changelog (https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- `beam.mcda.pairwise_superiority` and `PairwiseSuperiorityReport`: compares methods two at a time across datasets, reporting the probability of superiority (the fraction of datasets on which one method outperforms another), an equivalence band set to the metric's noise floor, a Copeland-style standing score, and a sign test. The effect-size companion to the critical-difference test, whose significance reading it complements; the HTML report's critical-difference section now states how often the top-ranked method outperforms the next. docs/explanations/pairwise-superiority.md.
- `beam.mcda.rank_sensitivity` and `RankSensitivityReport`: an exact variance decomposition that splits a ranking's instability between the analyst's choices (weighting scheme, aggregation rule) and the data (the dataset), by running the full factorial of all three and attributing each tool's rank variance with an analysis of variance. On M4 the dataset carries about 96 percent of the rank variance and the choices under 1 percent each; the HTML report gains a "what moves the ranking" section for tensor inputs. docs/explanations/rank-sensitivity.md.
- `beam.mcda.card_data_consistency` and `CardDataConsistencyReport`: audits raw scores against each card's declared range, baseline, target and noise floor, flagging out-of-range values and other card-data contradictions by metric name. `beam.rank` attaches it to `RunResult.card_consistency` and the HTML report gains a section; docs/explanations/card-data-consistency.md.
- `beam.mcda.metric_diagnostics` and `MetricDiagnosticsReport`: one entry point that runs the validity, reliability, and dimensionality checks over a single grouping on the shared oriented Spearman correlations, returning the three reports together. Validity is skipped when the grouping has a single construct.
- `beam.mcda.metric_dimensionality` and `MetricDimensionalityReport`: counts the factors in each construct group by parallel analysis (Horn 1965, Glorfeld 1995) on the same oriented Spearman correlations as `metric_validity` and `metric_reliability`, the dimensionality companion to the reliability check. On OpenProblems batch integration the high-alpha biological group carries two factors while the low-alpha batch group carries one, so reliability and dimensionality dissociate; docs/explanations/dimensionality.md.
- `beam.mcda.metric_reliability` and `MetricReliabilityReport`: standardized Cronbach's alpha per construct group, the reliability companion to `metric_validity`, with a per-metric alpha-if-dropped diagnostic. On OpenProblems batch integration the biological group reads as one reliable scale (alpha 0.85) and the batch group does not (alpha 0.62); docs/explanations/reliability.md.
- `beam.mcda.metric_validity` and `MetricValidityReport`: a convergent and discriminant validity check (Campbell-Fiske 1959) that orients every metric to higher-is-better, correlates the metrics across the method-by-dataset cells with Spearman, and tests whether a construct grouping holds (within-group agreement above between-group), flagging redundant and crossloading metrics. On the OpenProblems batch integration scores the scIB bio/batch split is supported but weak and `graph_connectivity` leans biological against its label; docs/explanations/convergent-discriminant-validity.md.
- `beam.mcda.beats_random_baseline` and `beam.mcda.noise_floor_separation`: two reference-level checks that read raw scores against the cards, reporting how many tools beat the chance level in `semantics.score_of_random_baseline` and which tool pairs no metric separates above the `comparability.noise_floor`. `beam.rank` attaches a `RandomBaselineReport` and a `NoiseFloorReport` to `RunResult`, the HTML report gains a Reference levels section, and the schema bumps to 1.2 for `comparability.noise_floor` (docs/explanations/reference-levels.md).
- `beam.heterogeneity.network_meta_analysis` and `NetworkMetaReport`: a frequentist network meta-analysis (R's netmeta) that pools benchmarks scoring overlapping methods into one coherent ranking, with per-treatment P-scores, effects against a reference, and heterogeneity and inconsistency statistics. `IntegrationBenchmarks.network_arms` builds the arm-level input (study = benchmark and dataset, treatment = method, mean and sd over the metrics). Gated by `netmeta_available`; `r-meta` and `r-netmeta` join envs/heterogeneity.yml. On the four integration benchmarks it ranks harmony first and combat last, matching the consensus, with a significant inconsistency Q. This completes Phase 5.
- `beam.owl.skos` and the `docs/beam.skos.ttl` release artefact: SKOS concept schemes over the card controlled vocabulary (polarity, scale type, allowed transformations, recommended normalization), generated from the schema enums with definitions and a Stevens scale hierarchy. The upstream STATO term proposals for the gapped metrics are drafted in docs/explanations/stato-term-proposals.md.
- `beam.mcda.aggregation_agreement` and `AggregationAgreementReport`: re-rank a tool by metric matrix under the five aggregations at fixed weighting and report how closely the orderings agree (per-method ranks, pairwise Kendall tau-b, a mean-rank consensus, and the per-tool rank span). The funky-heatmap consensus panel takes its rank span from this report; docs/explanations/aggregation-agreement.md.
- The `beam.report` HTML report now embeds the funky-heatmap glyph table (a "Robustness at a glance" section) and an aggregation-agreement summary by default. Pass `funky_heatmap=False` to leave the figure out.
- `beam heterogeneity scores.csv --model {mixed-effects,bradley-terry-tree,plackett-luce}` fits a heterogeneity model on a long-format score file and writes the report as JSON, completing the CLI of Section 5.2. It needs the R toolchain and exits with a named error when the package is absent; docs/how-to/run-heterogeneity-from-the-cli.md.

### Changed

- A beam.yaml metric version pin (`- id: ari` with `version: v1`) now takes effect: the pinned card is used for the ranking, its hash is recorded in the manifest, and the version is passed to `beam.rank(versions=...)`, `registry_context` and `run_from_registry`. An unknown pinned version stops the run with a clear error instead of being ignored.

### Fixed

- `Scores.n_datasets` returned 0 for the wide single-dataset layout, contradicting its docstring; it now returns 1.

## [0.1.4] - 2026-05-29

### Added

- Ontology mappings on every metric card. Each card under `src/beam/metrics/<id>/v1.yaml` now carries an optional `mappings:` block with full IRIs to STATO (Statistics Ontology), UO (Units of Measurement Ontology), OBI (Ontology for Biomedical Investigations) and HuggingFace evaluate where a term exists. The schema bumps to 1.1: `mappings.stato`, `mappings.uo`, `mappings.obi`, `mappings.qudt`, `mappings.om2`, `mappings.huggingface_evaluate` are enumerated as typed URI strings; additionalProperties stays open so existing free-form keys and future keys validate without a schema bump. Coverage: 6 of 27 cards mapped to STATO (ari, accuracy, f1_score, isolated_label_f1, calibration_slope, correlation), 4 of 4 unit-bearing cards mapped to UO (runtime, peak_memory, speed, co2), 11 cards carry an OBI term (OBI_0002631 for the scIB family, OBI_0200104 for pcr), 5 cards cross-reference HuggingFace evaluate. 21 honest STATO gaps are documented inline and in docs/explanations/ontology-mappings.md with proposed-upstream notes for the ones beam cares about long term; beam mints no private IRIs. The OWL release artefact lives at docs/beam.owl.ttl and is regenerated from the cards by `python -m beam.owl.generate`. rdflib joins the dev optional dependencies. docs/explanations/ontology-mappings.md.
- Decision module with five MCDA aggregations (SAW, TOPSIS, VIKOR, PROMETHEE II, COMET, wrapping pymcdm) and six weighting schemes (equal, entropy, standard deviation, CRITIC, MEREC, AHP).
- Six card-driven normalization strategies (min_max, log_min_max, rank, zscore, baseline_relative, target_relative) with empirical-bound and heavy-tail guards.
- `target_relative` normalization and the `target_value` polarity for metrics whose ideal is a fixed value, not the highest or lowest score. The strategy scales each method by its closeness to the declared `semantics.target` (deviation-then-min-max), so the method nearest the target maps to 1. The pipeline enforces the pairing both ways: a `target_value` column must use `target_relative`, and `target_relative` refuses a monotone polarity. `target` is threaded from the card through `registry_context`, `run`, `run_from_registry` and the sensitivity primitives. New seed card `calibration_slope` (target 1) demonstrates the path.
- Sensitivity and comparison primitives: leave_one_metric_out, leave_one_dataset_out, SMAA, smallest_weight_perturbation, and the Demsar Friedman-Nemenyi critical-difference diagram.
- `beam.mcda.skillings_mack` and the alias `coverage_aware_critical_difference`: the Skillings-Mack (1981) generalization of the Friedman test to incomplete block designs. Runs on a tool by dataset matrix with NaN, returns a frozen `SkillingsMackReport` with the chi-squared statistic, the degrees of freedom, the p-value, the per-method centred standardised sums and the coverage. Validated against `critical_difference` on complete inputs to within 1e-10 (scipy's tie correction is the only allowed deviation), and against a hand-computed three-method four-block example with one missing cell. The Nemenyi post-hoc is not generalized; for pairwise cliques the user restricts the matrix to the complete block and calls `critical_difference`. docs/explanations/skillings-mack.md.
- User-facing layer: beam.load_scores and Scores, the beam.rank procedural API and RunResult, a self-contained HTML beam.report, a reproducibility manifest, the declarative beam.yaml runner, and the beam command-line interface.
- Heterogeneity module beam.heterogeneity (R via one-shot subprocess): mixed-effects variance decomposition (lme4) with a glmmTMB beta engine for bounded metrics, Bradley-Terry trees (psychotree), and Plackett-Luce on full rankings (PlackettLuce).
- `beam.heterogeneity.source_variance_decomposition` and `SourceVarianceReport`: a cross-benchmark variance decomposition that fits `score ~ method + (1 | benchmark) + (1 | benchmark:dataset) + (1 | method:benchmark)` in lme4 and reports the method-by-benchmark variance share, the part of the spread that is a method ranking differently depending on which benchmark evaluates it (disagreement from benchmarker choices) rather than genuine heterogeneity. Datasets are nested in benchmark, so benchmarks need not share datasets. Validated on synthetic two-benchmark data.
- `SourceVarianceReport.lrt_statistic` and `lrt_pvalue`: a significance test for each variance partition (benchmark, benchmark:dataset, method:benchmark).
- `beam.reporting.funky_heatmap` and `funky_heatmap_from_run`: the glyph-table benchmarking plot (methods by metrics, circle size for score, colour for metric group, overall bar) with an added panel that shows each method's rank span across the leave-one-dataset-out runs, so the figure carries its own rank robustness instead of reading as a settled order.
- Registry grew from seven to twenty-seven metric cards across clustering, efficiency, forecasting, transportation, the scIB single-cell integration and spatial metrics, and a clinical-prediction calibration metric.
- Bundled datasets load_duo2018, load_m4, and load_openproblems (batch_integration and spatially_variable_genes), each a small derived table with provenance in src/beam/data/README.md.
- Cross-benchmark harmonisation: load_integration_benchmarks and load_integration_published_ranks align four single-cell integration benchmarks (scIB, OpenProblems, Tran et al. 2020, Tyler et al. 2023 bioRxiv) on the shared scIB metric family (ARI, ASW, kBET, LISI) for five common methods, the input to source_variance_decomposition and the cross-benchmark meta-analysis. Derived tables scib2022_metrics.csv, tran2020_metrics.csv, tyler2023_metrics.csv and integration_published_ranks.csv vendored with provenance. The Tyler 2023 source covers three of the five methods (harmony, scanorama, liger) and three of the four metrics (ARI, ASW, kBET; the cLISI Tyler reports is a different quantity from the iLISI the other sources report, so LISI is not slotted in for Tyler). Tyler's mean_kBET_within_cell_type is raw rejection rate, lower-is-better, the opposite polarity to scIB's reported kBET; the loader handles per-source polarity. Adding Tyler raises the four-source method-by-benchmark variance share to 0.23, up from the three-source 0.15.
- `beam.datasets.load_pancreas_contrast` and `PancreasContrast`: the same-data Tran D4 versus scIB pancreas contrast on the five common methods. Both pipelines agree harmony ranks first on the shared five-study data (Muraro, Segerstolpe, Baron, Wang, Xin), but the Spearman of the per-method mean ranks is only +0.46. LIGER ranks second on Tran D4 and tied last on scIB pancreas, the dataset-confound-free version of the cross-benchmark disagreement.
- `IntegrationBenchmarks.method_metric_matrix(benchmark)` and a per-benchmark smallest-weight-perturbation analysis. Under SAW with equal weights, OpenProblems is the most fragile (0.11 ASW change flips fastMNN to harmony), Tran the middle (0.24 ASW flips harmony to LIGER), scIB the most stable (0.90 LISI, past the feasible range, would flip fastMNN to LIGER). Three benchmarks, three different fragilities under the same rule.
- Six worked vignettes (Duo 2018, simulated scenarios, transportation, M4, OpenProblems, cross-benchmark meta-analysis), all rendered in CI.
- Missing-data policy for the MCDA pipeline. The ranking entry points (beam.rank, mcda.run, run_from_registry, the CLI beam rank --on-missing, and the beam.yaml missing key) take an explicit missing= policy, default "error". "error" refuses any missing cell with a named IncompleteMatrixError; "available" is available-case ranking with SAW only (each tool scored on its observed metrics, weights renormalized over its support); "worst" treats a non-run as the worst score (missing normalized cells set to 0, the matrix completes, every method runs); "impute" is a discouraged mean-imputation opt-in. Every non-error policy warns. beam never imputes by default or silently. Normalization is now NaN-transparent. reduce_tensor gained on_zero_coverage="nan" so a tool never run on a metric flows into the policy. docs/explanations/missing-data.md.
- Documentation: explanation essays on MCDA, normalization, the heterogeneity diagnostics, the funky-heatmap robustness plot, missing data, the Skillings-Mack coverage-aware Friedman test, and the ontology mappings.
- R package `rbeam`: an R interface to beam under `r/beam/`. The MCDA wrappers (`beam_rank`, `beam_report`, `beam_validate`, `beam_run`, `beam_metric_show`) forward to the Python package through reticulate; the heterogeneity diagnostics (`beam_mixed_effects`, `beam_bradley_terry_tree`, `beam_plackett_luce`, `beam_source_variance_decomposition`) are implemented natively in R with lme4, glmmTMB, psychotree and PlackettLuce, so there is no R to Python to R indirection. Named `rbeam` because `beam` and `beamr` are taken on CRAN. Checked with `R CMD check --as-cran` on linux, macos and windows.

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
