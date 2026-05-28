# Contributing to beam

Thanks for considering a contribution. This file covers the PR contract, how to add a metric card, the licensing terms, and the community expectations.

## Quick start

```
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check .
```

If you change a metric card or the schema, validate from R too (or rely on CI to do it for you):

```
Rscript tests/validate_cards.R
```

R-side validation needs the CRAN packages `jsonvalidate`, `yaml`, and `jsonlite`. The schema is plain JSON Schema (draft 2020-12) and is meant to be readable from any language; if your language is not covered, please open an issue.

## PR contract

Every non-trivial PR ships:

- code change with type hints (Python) or roxygen2 docstrings (R)
- a unit test
- updated docstring on every public function the PR touches
- an ADR in `docs/adr/` if the change reflects a design decision
- a CHANGELOG entry (Keep a Changelog format)

Commits do not bundle unrelated edits. One commit = one coherent change.

## Adding a metric card

Cards live under `src/beam/metrics/<id>/v<version>.yaml`. The directory name must match the `id` field; the filename stem must match the `version` field. This is enforced in CI. The cards ship inside the package so an installed wheel can find them.

The schema is at `src/beam/schema/metric_card.schema.json`. Every required field must be present. A minimum-effort card needs `id`, `version`, `name`, `description`, `metric_kind`, `measurand`, `task`, `requires_ground_truth`, `output`, `semantics`, `comparability`, `implementations`, `examples`, and `provenance`.

See `src/beam/metrics/ari/v1.yaml` and `src/beam/metrics/runtime/v1.yaml` for two worked examples covering the derived and the measured `metric_kind` respectively.

## Licensing

- Code (everything outside `src/beam/metrics/`): GPL-3.0-or-later. See `LICENSE`.
- Metric cards (`src/beam/metrics/`): CC-BY-4.0. See `src/beam/metrics/LICENSE.md`. By contributing a card you agree to this licensing.

## ADR template

See `docs/adr/0000-template.md`. Number sequentially. Start in status "Proposed"; move to "Accepted" after review. Never edit an accepted ADR silently; if it changes, supersede it with a new one.

## Conventions

- Documentation uses Quarto. Vignettes live in `examples/` and are rendered as part of CI.
- Diataxis split for `docs/`: tutorials, how-to, reference, explanations. Do not mix modes within one document.
- Plain English in prose; no jargon without an explicit definition.

## Community

Contributors and users are welcome regardless of sex, gender identity, age, ethnicity, nationality, religion, disability, sexual orientation, career stage, native language, or any other attribute. We believe in respectful and healthy collaboration in scientific research.
