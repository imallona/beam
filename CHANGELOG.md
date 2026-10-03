# Changelog

The format follows Keep a Changelog (https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- `beam.mcda.attribution_synthesis`: analyst-choice, dataset and benchmarker shares of rank variance.
- `beam.mcda.dataset_discrimination` and `difficulty_concordance`, with R wrappers and plots.
- `beam.mcda.dataset_concordance`: Kendall tau-b agreement between per-dataset rankings.
- `beam.mcda.normalization_agreement`: rankings under several normalizations.
- `beam.mcda.bayesian_sign_comparison`: Bayesian sign test on pairwise counts.
- `beam.mcda.pairwise_transitivity`: Condorcet choice, circular triads, coefficient of consistence.
- `beam.mcda.specification_curve`: rankings under every weighting, aggregation and dataset.
- `beam.blind`, `beam.unblind`, `Seal`, and the CLI `beam blind`, `beam unblind`.
- `beam.datasets.load_scib_integration_families`: scIB deep-learning methods on the classical datasets.
- `beam.plot`: matplotlib figures of a run; `rank_sensitivity_by_tool`.
- `beam.io.write_scores`.
- R: `beam_specification_curve`, `beam_blind`, `beam_unblind`, `beam_write_seal`, `beam_read_seal`.
- R: `beam_funky_table` and `beam_rank_bump` for raw matrices.
- `scripts/generate_example_reports.py` writes one report per bundled dataset.

### Changed

- rbeam draws its plots with ggplot2 and patchwork.
- The rank sensitivity plot colours bars by analyst choice, dataset, interaction.
- The funky heatmap aligns its span and SMAA panels on rows.
- Plots size to their content.
- The forest plot labels P-scores as such.
- Rank sensitivity plot titles are "rank variance by factor".
- The funky heatmap has no group legend for one group.
- The report draws the Friedman-Nemenyi diagram with joining bars.
- COMET refuses more than eight metrics.
- `install_beam_python()` installs from GitHub.
- Explanation pages, vignettes and example READMEs are shorter.

### Fixed

- The how-to example metric card validates against the schema.
- `docs/beam.owl.ttl` and the mapping table list all 29 cards.

## [0.2.0] - 2026-06-09

### Added

- `beam.datasets.load_gptcelltype` (Hou and Ji 2024), two annotation cards, a vignette.
- `beam.datasets.load_deepcellseek` (Xiao et al. 2025) and an LLM cross-benchmark comparison.
- `beam.mcda.pairwise_superiority`: probability of superiority, equivalence band, standing, sign test.
- `beam.mcda.rank_sensitivity`: rank variance by weighting, aggregation and dataset.
- `beam.mcda.card_data_consistency`: raw scores against card range, baseline, target, noise floor.
- `beam.mcda.metric_validity`, `metric_reliability`, `metric_dimensionality`, and `metric_diagnostics` for all three.
- `beam.mcda.beats_random_baseline` and `noise_floor_separation`.
- `beam.heterogeneity.network_meta_analysis` (R's netmeta).
- `beam.owl.skos` and `docs/beam.skos.ttl`.
- `beam.mcda.aggregation_agreement`: rankings under the five aggregations.
- The HTML report embeds the funky heatmap and the aggregation agreement.
- CLI `beam heterogeneity` for mixed-effects, Bradley-Terry tree and Plackett-Luce.

### Changed

- A metric version pinned in beam.yaml selects that card version.

### Fixed

- The SMAA colorbar of the funky heatmap has rank 1 bright.
- `Scores.n_datasets` is 1 for the wide layout.

## [0.1.4] - 2026-05-29

### Added

- `mappings` on metric cards: STATO, UO, OBI, HuggingFace evaluate; `docs/beam.owl.ttl`.
- Five aggregations (SAW, TOPSIS, VIKOR, PROMETHEE II, COMET) through pymcdm.
- Six weighting schemes: equal, entropy, standard deviation, CRITIC, MEREC, AHP.
- Six normalizations: min_max, log_min_max, rank, zscore, baseline_relative, target_relative.
- The `target_value` polarity.
- Leave-one-metric-out, leave-one-dataset-out, SMAA, smallest weight perturbation, critical difference.
- `beam.mcda.skillings_mack` for incomplete matrices.
- `beam.load_scores`, `beam.rank`, `beam.report`, the manifest, beam.yaml, the CLI.
- `beam.heterogeneity`: mixed-effects (lme4, glmmTMB), Bradley-Terry trees, Plackett-Luce.
- `beam.heterogeneity.source_variance_decomposition` with likelihood-ratio tests.
- `beam.reporting.funky_heatmap` with a leave-one-dataset-out rank span.
- Twenty-seven metric cards.
- Datasets: `load_duo2018`, `load_m4`, `load_openproblems`.
- `load_integration_benchmarks`, `load_integration_published_ranks`, `load_pancreas_contrast`.
- A `missing=` policy: error (default), available, worst, impute.
- Six vignettes and the explanation pages.
- The R package `rbeam`.

### Changed

- pymcdm, scipy, jinja2 and matplotlib are runtime dependencies.
- The registry and the schema are inside the package.
- Aggregations, objective weights and critical difference refuse missing cells.

## [0.1.3] - 2026-05-20

### Added

- `beam.mcda.run`, `topsis`, `entropy_weights`.
- `beam.cards.polarities_for`.
- The cards-and-pipeline explanation.
- A CI job renders the Duo vignette.
- The `docs` extra.

## [0.1.2] - 2025-05-24

### Added

- `beam.mcda`: `min_max_normalize`, `equal_weights`, `weighted_sum`, `rank`.
- The Duo 2018 vignette.

### Changed

- numpy is a runtime dependency.

## [0.1.1] - 2025-03-22

### Added

- `beam.cards`: registry, loader, model.
- Cards: `nmi`, `peak_memory`, `accuracy`, `f1_score`, `silhouette`.
- `beam.io` CSV reader; pandas under the `io` extra.
- The measurement-theory explanation.
- `CITATION.cff`, `.pre-commit-config.yaml`, `Makefile`.

## [0.1.0] - 2025-02-22

### Added

- The metric card JSON Schema (draft 2020-12).
- Cards: `ari`, `runtime`.
- Schema tests in Python and R.
- GitHub Actions for lint, tests and R validation.
- `pyproject.toml`, `CONTRIBUTING.md`, the CC-BY-4.0 card license.
